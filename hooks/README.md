# Hooks

Hooks that run around tool calls in Claude Code. Each hook reads a JSON payload from stdin and either exits silently (allow) or writes a decision to stdout.

## How they work

Registered in `~/.claude/settings.json` under `hooks` (`PreToolUse` for the guard hooks; `Stop`, `SubagentStop`, `PostCompact` and `SessionEnd` for the export hook). Each hook runs with a short timeout. If a `PreToolUse` hook denies a command, Claude Code receives the denial reason and adjusts its approach.

> **Note:** `bash -c` / `sh -c` wrapper scanning and the destructive-pattern checks were consolidated into `block-destructive-ops.py`. The former standalone `reject-compound-bash.py`, `prefer-dedicated-tools.py`, and `normalize-git-dash-c.py` hooks have been removed.

## Hook inventory

### Large-file read router

The shared `~/.claude/agent-router/read_guard.py` commands inspect `Read` and shell file-read
calls before execution. Reads expected to return more than 350 lines are denied with an exact
`bulk_read.py` delegation command. Targeted `Read` calls with `offset` and `limit <= 350`, and
bounded `head`/`tail` calls, pass through. This cost guard fails open on malformed input; the
safety hooks below remain authoritative.

### enforce-worktree-paths.py

Blocks file tools (Read, Edit, Write, Glob, Grep) from escaping a git worktree. When an agent runs inside `.claude/worktrees/<name>/`, all file operations must target the worktree — not the original repo root.

### block-destructive-ops.py

Blocks high-consequence commands that are hard or impossible to reverse. Designed as the safety net for `--dangerously-skip-permissions` mode.
Matches `Bash`, `Read`, `Write`, and `Edit` tools.

**Git (Bash):**
- `git reset --hard` (destroys uncommitted changes)
- `git push --force` to main/master (rewrites shared history; `--force-with-lease` and feature branches are allowed)
- `git clean -f` (permanently deletes untracked files)
- `git checkout -- .` / `git restore .` (discards all unstaged changes)

**Filesystem (Bash):**
- `rm -rf` with broad targets: `.`, `..`, `~`, `/`, `/*`, `*` (catastrophic data loss; specific paths like `node_modules` are allowed)

**Network (Bash):**
- `curl`/`wget` piped to `bash`/`sh` (arbitrary code execution)
- `curl -d @file` / `curl --data @file` (data exfiltration)

**Sensitive files (Read, Write, Edit):**
- `~/.ssh/**`, `~/.aws/**`, `~/.gnupg/**`, `~/.config/gh/**` (authdirectories)
- `~/.netrc`
- `.env`, `.env.*` (except `.env.example`, `.env.template`,`.env.sample`)
- `*.pem`, `*.key`, `*.pfx`, `*.p12` (except Read under `node_modules/`)
- `.npmrc`, `.pypirc` (package manager auth)
- `id_rsa*`, `id_ed25519*`, `id_ecdsa*` (SSH keys)
- `credentials.json`, `service-account*.json` (cloud credentials)

**Self-modification (Write, Edit only — Read is allowed):**
- `~/.claude/hooks/**` (could disable this very hook)
- `~/.claude/settings.json`, `~/.claude/settings.local.json`
- `**/CLAUDE.md` (could rewrite safety instructions)

Paths are canonicalized with `os.path.realpath()` to defeat `../` traversal and symlink evasion; relative paths resolve against the payload's `cwd`. Bash commands are also split into shell words, and any word that resolves to a sensitive file above is denied, so `cat ~/.ssh/id_rsa` is blocked like a `Read` would be. Most checks run per command segment, so a flag in one segment never combines with a target in another. Strips quoted strings and heredoc content before matching Bash commands to avoid false positives.

### session-end-export.py

Runs on `Stop`, `SubagentStop`, `PostCompact` and `SessionEnd`. The hook itself only touches a pending marker, starts a detached worker and exits 0 (about 0.05s); it never exits 2, which on `Stop` would block the agent from stopping. The worker holds a non-blocking lock and loops while the marker reappears, so bursts of events coalesce into one refresh.

Each pass runs the `recall` skill's `export_sessions.py --json`, which parses only bytes appended since the last run and writes bounded chunks atomically, rewriting only chunks whose content changed. QMD `update` and `embed -c Claude-sessions` run only when something was exported. Logs go to `~/.claude/logs/session-end-export.log`.

## Tests

```bash
python3 -m unittest discover -s hooks -v
```

## Adding a new hook

1. Create a Python script in this directory
2. Register it in `settings.json`
3. The script receives JSON on stdin with `tool_name` and `tool_input`
4. Exit 0 silently to allow, or write a deny JSON to stdout
