"""Claude Code PreToolUse hook: blocks destructive git operations.

Blocks high-consequence commands that are hard to reverse:
  - git reset --hard (destroys uncommitted changes)
  - git push --force to main/master (rewrites shared history)
  - git clean -f (permanently deletes untracked files)
  - git checkout -- . / git restore . (discards all unstaged changes)

Allowed (legitimate workflow):
  - --force-with-lease on any branch
  - git branch -D (low-risk post-merge cleanup)
  - git reset --soft / --mixed (non-destructive)
  - git push --force to feature branches
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


# --- Pattern checks ---

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


def main() -> None:
    payload = json.loads(sys.stdin.read())

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command.strip():
        sys.exit(0)

    # Strip quoted content so patterns inside strings/heredocs don't trigger
    stripped = strip_quoted_content(command)

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

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
