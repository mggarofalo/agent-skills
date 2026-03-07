"""Claude Code PreToolUse hook: blocks file tools from escaping the worktree.

When an agent runs inside a git worktree (.claude/worktrees/<name>/), file
tools (Read, Edit, Write, Glob, Grep) must operate within the worktree — not
the original repo root. Without this guard, agents construct absolute paths
from git output or cached context that point at the root source, silently
reading stale files or writing to the wrong tree.

Detection:
  1. Check if cwd contains '/.claude/worktrees/' — if not, allow everything.
  2. Extract the original repo root (the path before .claude/worktrees/).
  3. For each file tool call, resolve the target path and block it if it falls
     under the original repo root but outside the worktree.

Paths outside the repo entirely (e.g. ~/.claude/, /tmp/) are allowed — only
the "wrong copy of the same repo" is blocked.
"""

import json
import os
import sys

WORKTREE_SENTINEL = "/.claude/worktrees/"

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


def normalize(p: str) -> str:
    """Normalize a path to forward slashes for consistent comparison."""
    return p.replace("\\", "/").rstrip("/")


def main() -> None:
    payload = json.loads(sys.stdin.read())

    tool_name = payload.get("tool_name", "")
    if tool_name not in TOOL_PATH_KEYS:
        sys.exit(0)

    # Determine if we're inside a worktree
    cwd = normalize(os.getcwd())
    idx = cwd.find(WORKTREE_SENTINEL)
    if idx == -1:
        # Not in a worktree — nothing to enforce
        sys.exit(0)

    repo_root = cwd[:idx]  # original repo root (without trailing slash)
    worktree_root = cwd  # the worktree itself (cwd is the worktree root or a subdir)

    # The worktree dir is repo_root + /.claude/worktrees/<name>
    # Extract it precisely: everything up to and including the worktree name
    after_sentinel = cwd[idx + len(WORKTREE_SENTINEL) :]
    worktree_name = after_sentinel.split("/")[0]
    worktree_root = f"{repo_root}{WORKTREE_SENTINEL}{worktree_name}"

    tool_input = payload.get("tool_input") or {}

    for key in TOOL_PATH_KEYS[tool_name]:
        target = tool_input.get(key)
        if not target:
            continue

        resolved = normalize(os.path.abspath(target))

        # Allow paths inside the worktree
        if resolved == worktree_root or resolved.startswith(worktree_root + "/"):
            continue

        # Allow paths completely outside the repo (e.g. ~/.claude/, /tmp/)
        if not (resolved == repo_root or resolved.startswith(repo_root + "/")):
            continue

        # The path is inside the original repo but outside the worktree — block it
        # Compute the relative path so the agent can fix it
        rel = resolved[len(repo_root) + 1 :]  # strip repo_root + "/"
        suggested = f"{worktree_root}/{rel}"

        deny(
            f"BLOCKED: You are in a worktree at {worktree_root} but this "
            f"{tool_name} call targets the original repo root at {repo_root}. "
            f"Use the worktree path instead: {suggested}"
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
