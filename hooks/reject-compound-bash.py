"""Claude Code PreToolUse hook: rejects compound Bash commands.

Blocks Bash tool calls that:
  1. Chain multiple commands with &&, ||, or ; at the top level.
  2. Wrap commands in `bash -c` / `sh -c` subshells, which hide the
     real command from Claude Code's permission matching system.
  3. Use `npx --prefix <path>` — the --prefix flag is unnecessary
     (npx resolves binaries up the directory tree) and breaks
     permission matching against `Bash(npx <tool>:*)` allow rules.

Ignores operators that appear inside quoted strings (single, double,
or HEREDOC bodies) so that legitimate uses are not blocked.
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


def remove_quoted_regions(text: str) -> str:
    # 1. HEREDOC bodies: <<'DELIM' ... DELIM / <<"DELIM" ... DELIM / <<DELIM ... DELIM
    text = re.sub(
        r"<<-?\s*'?\"?(\w+)\"?'?\s*\r?\n.*?\r?\n\s*\1\b",
        "",
        text,
        flags=re.DOTALL,
    )
    # 2. Single-quoted strings (no escaping inside single quotes in bash)
    text = re.sub(r"'[^']*'", "", text)
    # 3. Double-quoted strings (respect backslash escapes)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', "", text)
    return text


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
            "Instead, issue each command as its own Bash tool call. "
            "If you need to change directories first, use a separate `cd <path>` "
            "call (the working directory persists between Bash calls), then run "
            "the actual command in the next call."
        )

    stripped = remove_quoted_regions(command)

    # Match && or || or ; that are NOT part of ;; (case terminators)
    if re.search(r"(?<![;&|])&&(?!&)|(?<![|&])\|\|(?!\|)|(?<!;);(?!;)", stripped):
        deny(
            "Compound command detected (&&, ||, or ; operator outside quotes). "
            "Issue each command as a separate Bash tool call instead of chaining them. "
            "If the commands are independent, call them in parallel. "
            "If they must run sequentially, call them one at a time and check the "
            "result before proceeding."
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
