# Hooks

PreToolUse hooks that run before every Bash tool call in Claude Code. Each hook reads a JSON payload from stdin and either exits silently (allow) or writes a deny decision to stdout.

## How they work

Registered in `~/.claude/settings.json` under `hooks.PreToolUse`. Each hook runs with a 10-second timeout. If a hook denies a command, Claude Code receives the denial reason and adjusts its approach.

## Hook inventory

### reject-compound-bash.py

Blocks compound commands that undermine Claude Code's permission system:
- `&&`, `||`, `;` operators outside quoted strings (forces separate tool calls)
- `bash -c` / `sh -c` wrappers (hides real commands from permission matching)
- `npx --prefix <path>` (unnecessary flag that breaks permission matching)

### normalize-git-dash-c.py

Blocks `git` flags that appear before the subcommand:
- `git -C <path> <subcmd>` — tells Claude to `cd` first, then run `git <subcmd>`
- `git -c <key=val> <subcmd>` — tells Claude to drop the `-c` flag

These flags break permission matching because Claude Code matches on the first token after `git`.

### prefer-dedicated-tools.py

Blocks shell commands that have dedicated Claude Code tools:
- `find` → Glob
- `grep` / `rg` → Grep
- `cat` / `head` / `tail` → Read
- `sed` / `awk` → Edit / Grep

## Adding a new hook

1. Create a Python script in this directory
2. Register it in `settings.json` (and `config/settings.json.example`)
3. The script receives JSON on stdin with `tool_name` and `tool_input`
4. Exit 0 silently to allow, or write a deny JSON to stdout
