"""Claude Code PreToolUse hook: blocks file tools from escaping the worktree.

When an agent runs inside a linked git worktree, file tools (Read, Edit,
Write, Glob, Grep) must operate within the worktree — not the primary
checkout. Without this guard, agents construct absolute paths from git output
or cached context that point at the primary checkout, silently reading stale
files or writing to the wrong tree.

Detection (from the payload's cwd, via git):
  1. `git rev-parse --show-toplevel` gives the active worktree root.
  2. `git worktree list --porcelain` lists every worktree; the first entry is
     the primary checkout. If the active root is the primary (or git fails, or
     there is only one worktree), allow everything.
  3. For each file tool call, resolve the target path and block it if it falls
     under the primary checkout but outside the active worktree.

Any linked worktree counts, not only `.claude/worktrees/<name>/`. Paths
outside the primary checkout entirely (e.g. ~/.claude/, /tmp/, sibling
worktrees elsewhere on disk) are allowed — only the "wrong copy of the same
repo" is blocked.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Tools and the input keys that carry file/directory paths
TOOL_PATH_KEYS = {
    "Read": ["file_path"],
    "Edit": ["file_path"],
    "Write": ["file_path"],
    "Glob": ["path"],
    "Grep": ["path"],
}


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def fail_closed(reason: str) -> None:
    """Deny because the guard could not reach a decision at all.

    Exit 2 with a reason on stderr is the only failure signal both Claude Code
    and Codex treat as a block; every other nonzero status permits the call.
    """
    sys.stderr.write(f"BLOCKED (guard error, failing closed): {reason}\n")
    sys.exit(2)


def git(cwd: Path, *args: str) -> str:
    """Run git in cwd; return stripped stdout, or "" on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def worktree_roots(cwd: Path):
    """Return (primary_root, active_root) when cwd is in a linked worktree.

    Returns None when cwd is not in a repo, git fails, or cwd is in the
    primary checkout — all cases with nothing to enforce.
    """
    active_text = git(cwd, "rev-parse", "--show-toplevel")
    if not active_text:
        return None
    active_root = Path(active_text).resolve()

    listing = git(cwd, "worktree", "list", "--porcelain")
    roots = [
        Path(line[len("worktree ") :]).resolve()
        for line in listing.splitlines()
        if line.startswith("worktree ")
    ]
    if len(roots) < 2 or active_root not in roots or active_root == roots[0]:
        return None
    return roots[0], active_root


def inside(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError as exc:
        fail_closed(f"unparseable hook payload: {exc}")

    if not isinstance(payload, dict):
        fail_closed(f"hook payload was {type(payload).__name__}, expected object")

    tool_name = payload.get("tool_name", "")
    if tool_name not in TOOL_PATH_KEYS:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        fail_closed(f"tool_input was {type(tool_input).__name__}, expected object")

    targets = []
    for key in TOOL_PATH_KEYS[tool_name]:
        target = tool_input.get(key)
        if not target:
            continue
        if not isinstance(target, str):
            fail_closed(
                f"{tool_name}.{key} was {type(target).__name__}, expected string"
            )
        targets.append(target)
    if not targets:
        # No explicit path (e.g. Glob/Grep defaulting to cwd) — nothing to check
        sys.exit(0)

    cwd_text = payload.get("cwd")
    if not isinstance(cwd_text, str) or not cwd_text:
        cwd_text = os.getcwd()
    cwd = Path(cwd_text).expanduser().resolve(strict=False)

    roots = worktree_roots(cwd)
    if roots is None:
        # Not in a linked worktree — nothing to enforce
        sys.exit(0)
    primary_root, active_root = roots

    for target in targets:
        resolved = (cwd / Path(target).expanduser()).resolve(strict=False)

        # Allow paths inside the active worktree (even when it is nested
        # under the primary checkout, as with .claude/worktrees/<name>)
        if inside(resolved, active_root):
            continue

        # Allow paths completely outside the primary checkout
        if not inside(resolved, primary_root):
            continue

        # The path is inside the primary checkout but outside the worktree —
        # block it, and compute the equivalent worktree path so the agent
        # can fix it
        suggested = active_root / resolved.relative_to(primary_root)

        deny(
            f"BLOCKED: You are in a worktree at {active_root} but this "
            f"{tool_name} call targets the primary checkout at {primary_root}. "
            f"Use the worktree path instead: {suggested}"
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — any failure must deny
        fail_closed(f"{type(exc).__name__}: {exc}")
