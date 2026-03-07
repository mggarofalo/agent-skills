"""Claude Code PreToolUse hook: blocks shell commands that have dedicated tools.

Detects when Claude uses file-operation shell commands (find, grep, cat, etc.)
as the primary command and blocks them with guidance to use the dedicated
Claude Code tools instead (Glob, Grep, Read, Edit, Write).

This improves the user experience because:
  1. Dedicated tools give better permission prompts (e.g. "allow Glob" vs
     "allow Bash(find:*)")
  2. Dedicated tools produce cleaner, more reviewable output
  3. Claude's system prompt already directs it to prefer these tools
"""

import json
import re
import sys

# Map of blocked commands -> (replacement tool, guidance message)
BLOCKED_COMMANDS = {
    "find": (
        "Glob",
        "Use the Glob tool to find files by pattern (e.g., pattern='**/*.cs'). "
        "It supports glob patterns and is faster than find.",
    ),
    "grep": (
        "Grep",
        "Use the Grep tool to search file contents. "
        "It supports regex, glob/type filters, context lines, and output modes.",
    ),
    "rg": (
        "Grep",
        "Use the Grep tool instead of rg. "
        "It supports the same regex patterns, file type filters, and context lines.",
    ),
    "cat": (
        "Read",
        "Use the Read tool to read file contents. "
        "It shows line numbers and supports offset/limit for large files.",
    ),
    "head": (
        "Read",
        "Use the Read tool with the 'limit' parameter to read the first N lines.",
    ),
    "tail": (
        "Read",
        "Use the Read tool with 'offset' and 'limit' parameters to read from "
        "a specific position in a file.",
    ),
    "sed": (
        "Edit",
        "Use the Edit tool for file modifications (find-and-replace). "
        "For read-only viewing, use the Read tool.",
    ),
    "awk": (
        "Grep or Edit",
        "Use the Grep tool to search/extract content, or the Edit tool to "
        "modify files. For read-only viewing, use the Read tool.",
    ),
}

# Match the first "real" command, skipping:
#   - leading whitespace
#   - env-var assignments (VAR=val ...)
#   - absolute path prefixes (/usr/bin/find -> find)
FIRST_CMD_RE = re.compile(
    r"""^\s*
        (?:\w+=\S*\s+)*   # optional env-var assignments
        (?:/\S+/)?         # optional absolute path prefix
        (\w+)              # the command name
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

    m = FIRST_CMD_RE.match(command)
    if not m:
        sys.exit(0)

    cmd_name = m.group(1)

    if cmd_name in BLOCKED_COMMANDS:
        tool, guidance = BLOCKED_COMMANDS[cmd_name]
        deny(
            f"BLOCKED: `{cmd_name}` has a dedicated Claude Code tool. {guidance} "
            f"Do NOT use Bash for this operation."
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
