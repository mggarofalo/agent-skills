"""Claude Code PreToolUse hook: rejects Bash commands that hide intent.

Blocks Bash tool calls that:
  1. Wrap commands in `bash -c` / `sh -c` subshells, which hide the
     real command from Claude Code's permission matching system.
  2. Use `npx --prefix <path>` — the --prefix flag is unnecessary
     (npx resolves binaries up the directory tree) and breaks
     permission matching against `Bash(npx <tool>:*)` allow rules.
"""

import json
import re
import sys

# Matches: bash -c '...' or sh -c "..." (with optional flags before -c)
SHELL_DASH_C = re.compile(
    r"""^\s*(?:bash|sh)\s+(?:-\S+\s+)*-c\s""",
    re.VERBOSE,
)

# Matches: npx --prefix <path> <tool> ...
NPX_PREFIX = re.compile(r"^\s*npx\s+--prefix\s+\S+")


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

    # Block npx --prefix — it's unnecessary (npx walks up the tree to
    # find node_modules/.bin) and the prefix breaks permission matching
    # against allow rules like `Bash(npx tsc:*)`.
    if NPX_PREFIX.search(command):
        deny(
            "BLOCKED: `npx --prefix <path>` breaks permission matching. "
            "Drop the `--prefix` flag — npx resolves binaries by walking "
            "up the directory tree from cwd automatically. "
            "Use `npx <tool> [args]` directly instead."
        )

    # Block bash -c / sh -c wrappers — they hide the real command from
    # permission matching (e.g. `bash -c 'git show ...'` won't match
    # an allow rule for `Bash(git:show)`).
    if SHELL_DASH_C.search(command):
        deny(
            "BLOCKED: `bash -c` / `sh -c` wrappers break permission matching. "
            "The real commands inside the subshell are invisible to allow-rules. "
            "Instead, issue each command as its own Bash tool call."
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
