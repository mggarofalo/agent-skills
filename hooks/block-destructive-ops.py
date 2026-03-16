"""Claude Code PreToolUse hook: blocks destructive operations.

Catches high-consequence commands that are hard or impossible to reverse.
Designed to be the safety net when running with --dangerously-skip-permissions.

Git operations blocked:
  - git reset --hard (destroys uncommitted changes)
  - git push --force to main/master (rewrites shared history)
  - git clean -f (permanently deletes untracked files)
  - git checkout -- . / git restore . (discards all unstaged changes)

Filesystem operations blocked:
  - rm -rf with broad targets: . .. ~ / /* * (catastrophic data loss)

Network operations blocked:
  - curl/wget piped to shell (arbitrary code execution)

Allowed (legitimate workflow):
  - --force-with-lease on any branch
  - git branch -D (low-risk post-merge cleanup)
  - git reset --soft / --mixed (non-destructive)
  - git push --force to feature branches
  - rm -rf with specific paths (node_modules, dist, build, etc.)
  - curl/wget without pipe to shell
"""

import json
import re
import sys


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


def strip_quoted_content(command: str) -> str:
    """Remove content inside quotes and heredocs to avoid false positives."""
    # Remove heredoc content (<<'EOF'...EOF, <<"EOF"...EOF, <<EOF...EOF)
    result = re.sub(
        r"<<-?\s*['\"]?(\w+)['\"]?\s*\n.*?\n\s*\1",
        "",
        command,
        flags=re.DOTALL,
    )
    # Remove double-quoted strings (handling escaped quotes)
    result = re.sub(r'"(?:[^"\\]|\\.)*"', '""', result)
    # Remove single-quoted strings
    result = re.sub(r"'[^']*'", "''", result)
    return result


# --- Git patterns ---

RESET_HARD = re.compile(r"git\s+reset\s+--hard")

CLEAN_FORCE = re.compile(r"git\s+clean\s+(?:.*\s)?-[a-z]*f")

DISCARD_ALL = re.compile(r"git\s+(?:checkout\s+--\s+\.|restore\s+\.)")


def is_force_push_to_main(command: str) -> bool:
    """Check if command is a force push to main/master."""
    if not re.search(r"git\s+push\b", command):
        return False
    # --force-with-lease is safe — allow it
    if re.search(r"--force-with-lease", command):
        return False
    # Must have --force or -f
    if not re.search(r"(?:--force\b|-f\b)", command):
        return False
    # Must target main or master
    if not re.search(r"\b(?:main|master)\b", command):
        return False
    return True


# --- Filesystem patterns ---


def is_dangerous_rm(command: str) -> bool:
    """Check if rm -rf targets a dangerously broad path."""
    if not re.search(r"\brm\b", command):
        return False
    # Must have recursive flag (-r, -R, or --recursive, possibly combined like -rf)
    if not re.search(r"-[a-zA-Z]*[rR]|--recursive", command):
        return False
    # Must have force flag (-f or --force, possibly combined like -rf)
    if not re.search(r"-[a-zA-Z]*f|--force", command):
        return False
    # Check for dangerous broad targets
    # . or ./
    if re.search(r"(?:^|\s)\./?(?:\s|$)", command):
        return True
    # .. or ../
    if re.search(r"(?:^|\s)\.\./?(?:\s|$)", command):
        return True
    # ~ or ~/
    if re.search(r"(?:^|\s)~/?(?:\s|$)", command):
        return True
    # / alone or /*
    if re.search(r"(?:^|\s)/(?:\s|$|\*)", command):
        return True
    # bare * (everything in cwd)
    if re.search(r"(?:^|\s)\*(?:\s|$)", command):
        return True
    return False


# --- Network patterns ---

# curl ... | bash, wget ... | sh, etc.
PIPE_TO_SHELL = re.compile(
    r"(?:curl|wget)\s+.*\|\s*(?:ba)?sh\b"
)


def main() -> None:
    payload = json.loads(sys.stdin.read())

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command.strip():
        sys.exit(0)

    # Strip quoted content so patterns inside strings/heredocs don't trigger
    stripped = strip_quoted_content(command)

    # --- Git checks ---

    if RESET_HARD.search(stripped):
        deny(
            "BLOCKED: `git reset --hard` destroys uncommitted changes irreversibly. "
            "Use `git stash` or `git reset --soft` instead, or confirm intent explicitly."
        )

    if is_force_push_to_main(stripped):
        deny(
            "BLOCKED: `git push --force` to main/master rewrites shared history on "
            "the default branch. Use `--force-with-lease` on a feature branch and "
            "merge via PR."
        )

    if CLEAN_FORCE.search(stripped):
        deny(
            "BLOCKED: `git clean -f` permanently deletes untracked files. "
            "List them with `git clean -dn` first."
        )

    if DISCARD_ALL.search(stripped):
        deny(
            "BLOCKED: `git checkout -- .` / `git restore .` discards all unstaged "
            "changes in the working tree."
        )

    # --- Filesystem checks ---

    if is_dangerous_rm(stripped):
        deny(
            "BLOCKED: `rm -rf` targets a dangerously broad path (., .., ~, /, *). "
            "This would cause catastrophic data loss. Use a more specific path, "
            "or delete files individually."
        )

    # --- Network checks ---

    if PIPE_TO_SHELL.search(stripped):
        deny(
            "BLOCKED: piping curl/wget output to a shell executes arbitrary code. "
            "Download the script first, review it, then run it explicitly."
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
