"""Claude Code PreToolUse hook: blocks git flags that precede the subcommand.

Claude Code's permission rules match on the command string, e.g.
    allow "Bash(git:show)" matches "git show ..."
But "git -C /some/path show ..." does NOT match "git:show" because
the first token after "git" is "-C", not the subcommand.

Similarly, "git -c core.pager= status" does NOT match "git:status"
because "-c" appears before the subcommand.

This hook detects these patterns and denies the call with a message
telling Claude to rewrite the command so that the subcommand appears
in the canonical position (immediately after "git").
"""

import json
import re
import sys


# Matches: git -C <path> <subcmd> [rest...]
# path can be quoted ("..." or '...') or unquoted (no spaces)
GIT_DASH_BIG_C = re.compile(
    r"""^\s*git\s+-C\s+
        (?P<path>"[^"]+"|'[^']+'|\S+)   # path (quoted or bare)
        \s+
        (?P<subcmd>\S+)                  # subcommand
        (?P<rest>.*)$                    # remaining args
    """,
    re.VERBOSE,
)

# Matches: git -c <key=value> <subcmd> [rest...]
# Handles one or more -c flags (e.g. git -c x=1 -c y=2 status)
GIT_DASH_SMALL_C = re.compile(
    r"""^\s*git\s+
        (?P<configs>(?:-c\s+\S+\s+)+)   # one or more -c key=value pairs
        (?P<subcmd>\S+)                  # subcommand
        (?P<rest>.*)$                    # remaining args
    """,
    re.VERBOSE,
)


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


def main() -> None:
    payload = json.loads(sys.stdin.read())

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command.strip():
        sys.exit(0)

    # Check git -C <path> (directory override)
    m = GIT_DASH_BIG_C.match(command)
    if m:
        git_path = m.group("path")
        subcmd = m.group("subcmd")
        rest = (m.group("rest") or "").strip()

        suggestion = f"git {subcmd}"
        if rest:
            suggestion += f" {rest}"

        deny(
            f"BLOCKED: `git -C` breaks permission matching. "
            f"First `cd` to the target directory, then run `{suggestion}` as a separate command. "
            f"Example: call `cd {git_path}` first, then call `{suggestion}`. "
            f"Do NOT use `--git-dir`/`--work-tree` flags or compound commands (`&&`/`;`). "
            f"The final git command must look like `git {subcmd} [args]` — nothing between `git` and the subcommand."
        )

    # Check git -c <key=value> (config override)
    m = GIT_DASH_SMALL_C.match(command)
    if m:
        subcmd = m.group("subcmd")
        rest = (m.group("rest") or "").strip()

        suggestion = f"git {subcmd}"
        if rest:
            suggestion += f" {rest}"

        deny(
            f"BLOCKED: `git -c <key>=<value>` breaks permission matching. "
            f"Drop the `-c` flag(s) and run `{suggestion}` directly. "
            f"The pager is not needed in this non-interactive environment. "
            f"The command must look like `git {subcmd} [args]` — nothing between `git` and the subcommand."
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
