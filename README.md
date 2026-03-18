# agent-skills

Canonical source for Claude Code skills, commands, agents, hooks, and config. Clone on any machine and run `python install.py` to set up symlinks.

## Structure

```
skills/          -> ~/.claude/skills
commands/        -> ~/.claude/commands
agents/          -> ~/.claude/agents
hooks/           -> ~/.claude/hooks
config/
  statusline.py    -> ~/.claude/statusline-command.py
  keybindings.json -> ~/.claude/keybindings.json
  settings.json.example  (template — copied only if settings.json is missing)
```

## Setup

```
git clone https://github.com/mggarofalo/agent-skills.git ~/Source/agent-skills
cd agent-skills
python install.py
```

Works on macOS, Linux, Windows (PowerShell, Git Bash, WSL). Automatically installs Python agent packages via `uv` (falls back to `pip`).

### Windows symlink prerequisites

The installer creates symlinks, which on Windows require one of:

1. **Developer Mode** (recommended) — Settings > Privacy & Security > For developers > Developer Mode: On
2. An elevated (admin) shell

Additionally, if you use Git Bash, set the `MSYS` environment variable so `ln -s` creates real symlinks instead of copies:

```
# Permanent (user-level env var — applies to all future shells)
[System.Environment]::SetEnvironmentVariable('MSYS', 'winsymlinks:nativestrict', 'User')

# Or per-session in ~/.bashrc
export MSYS=winsymlinks:nativestrict
```

Also ensure git is configured to preserve symlinks on clone:

```
git config --global core.symlinks true
```

## Syncing changes

Since `~/.claude/skills`, `commands`, and `agents` are symlinks into this repo, any edits are already reflected here. Commit and push as normal. On other machines, `git pull` picks up changes automatically.

## Adding new content

| Type | How |
|------|-----|
| Skill | Create `skills/<name>/SKILL.md` (and optional `references/` dir) |
| Command | Create `commands/<name>.md` |
| Agent (native) | Create `agents/<name>.md` |
| Agent (SDK) | Create `agents/<name>/` with Python source and `pyproject.toml` |
| Hook | Add Python script to `hooks/` and register in `settings.json` |
| Config | Add to `config/` and update both install scripts with a new link entry |

## What's included

### Skills

| Skill | Description |
|-------|-------------|
| **accessibility-audit** | WCAG 2.1 AA compliance audit using agent-browser and static analysis |
| **agent-skills** | Scaffold, remove, or list skills, hooks, commands, agents, and config |
| **init-repo** | GitHub repo scaffolding with CI, guidance files, and config per language |
| **owasp-top-10** | OWASP Top 10 security audit (static, dependency, and runtime) |
| **powershell-expert** | PowerShell scripting, modules, and GUI development reference |
| **reflect** | Session retrospective — extract learnings, update memory and guidance files |
| **resolve-conflicts** | Resolve merge conflicts on a PR by rebasing, resolving per-category, and force-pushing |
| **sdlc** | Structured SDLC pipeline: Plan, Implement, Review, Security, QA, Accept |
| **system-audit** | Audit Claude Code system for staleness, redundancy, gaps, and token waste |
| **work-issue** | End-to-end Plane issue implementation workflow |

### Commands

| Command | Description |
|---------|-------------|
| **find-bugs** | Invoke the pr-bug-finder agent from Claude Code |

### Agents

| Agent | Type | Description |
|-------|------|-------------|
| **accessibility-audit** | Native | Pre-commit accessibility audit gate |
| **pr-bug-finder** | SDK (Python) | Hunter/challenger/synthesizer adversarial bug analysis |

### Hooks

| Hook | Matches | Description |
|------|---------|-------------|
| **reject-compound-bash** | `Bash` | Blocks `&&`/`||`/`;` chaining, `bash -c` wrappers, `npx --prefix` |
| **normalize-git-dash-c** | `Bash` | Blocks `git -C` and `git -c` flags that break permission matching |
| **prefer-dedicated-tools** | `Bash` | Blocks `find`/`grep`/`cat`/`sed`/etc. in favor of Glob/Grep/Read/Edit |
| **enforce-worktree-paths** | `Read\|Edit\|Write\|Glob\|Grep` | Prevents agents in worktrees from reading/writing the original repo root |

### Config

| File | Description |
|------|-------------|
| **statusline.py** | Status line with git branch, worktree detection, context usage bar |
| **keybindings.json** | Custom Claude Code keybindings |
| **settings.json.example** | Template with hooks, plugins, and statusline configuration |

