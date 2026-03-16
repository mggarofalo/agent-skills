# Hooks

PreToolUse hooks that run before tool calls in Claude Code. Each hook reads a JSON payload from stdin and either exits silently (allow) or writes a deny decision to stdout.

## How they work

Registered in `~/.claude/settings.json` under `hooks.PreToolUse`. Each hook runs with a 10-second timeout. If a hook denies a command, Claude Code receives the denial reason and adjusts its approach.

## Hook inventory

### reject-compound-bash.py

Blocks Bash commands that hide intent from the permission system:
- `bash -c` / `sh -c` wrappers (hides real commands from permission matching)
- `npx --prefix <path>` (unnecessary flag that breaks permission matching)

### prefer-dedicated-tools.py

Blocks shell commands that have dedicated Claude Code tools:
- `find` → Glob
- `grep` / `rg` → Grep
- `cat` / `head` / `tail` → Read
- `sed` / `awk` → Edit / Grep

### enforce-worktree-paths.py

Blocks file tools (Read, Edit, Write, Glob, Grep) from escaping a git worktree. When an agent runs inside `.claude/worktrees/<name>/`, all file operations must target the worktree — not the original repo root.

### block-destructive-ops.py

Blocks high-consequence commands that are hard or impossible to reverse. Designed as the safety net for `--dangerously-skip-permissions` mode.

**Git:**
- `git reset --hard` (destroys uncommitted changes)
- `git push --force` to main/master (rewrites shared history; `--force-with-lease` and feature branches are allowed)
- `git clean -f` (permanently deletes untracked files)
- `git checkout -- .` / `git restore .` (discards all unstaged changes)

**Filesystem:**
- `rm -rf` with broad targets: `.`, `..`, `~`, `/`, `/*`, `*` (catastrophic data loss; specific paths like `node_modules` are allowed)

**Network:**
- `curl`/`wget` piped to `bash`/`sh` (arbitrary code execution)

Strips quoted strings and heredoc content before matching to avoid false positives.

## Adding a new hook

1. Create a Python script in this directory
2. Register it in `settings.json`
3. The script receives JSON on stdin with `tool_name` and `tool_input`
4. Exit 0 silently to allow, or write a deny JSON to stdout
