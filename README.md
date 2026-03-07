# agent-skills

Canonical source for Claude Code skills, commands, agents, hooks, and config. Clone on any machine and run the install script to set up symlinks.

## Structure

```
skills/          -> ~/.claude/skills
commands/        -> ~/.claude/commands
agents/          -> ~/.claude/agents
hooks/           ~/.claude/hooks/*.py  (per-file symlinks)
config/
  statusline.py    -> ~/.claude/statusline-command.py
  keybindings.json -> ~/.claude/keybindings.json
  settings.json.example  (template — copied only if settings.json is missing)
```

## Setup

```bash
git clone https://github.com/mggarofalo/agent-skills.git ~/Source/agent-skills
cd ~/Source/agent-skills
```

**Windows (PowerShell):**
```powershell
.\install.ps1
cd agents\pr-bug-finder; pip install -e .
```

**macOS / Linux / Git Bash:**
```bash
./install.sh
cd agents/pr-bug-finder && pip install -e .
```

## Syncing changes

Since `~/.claude/skills`, `commands`, and `agents` are symlinks into this repo, any edits are already reflected here. To push:

```bash
./sync.sh                        # push everything
./sync.sh skills commands        # push specific folders
./sync.sh -m "add new skill"     # custom commit message
```

On other machines, just `git pull` — symlinks pick up the changes automatically.

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
| **init-repo** | GitHub repo scaffolding with CI, guidance files, and config per language |
| **owasp-top-10** | OWASP Top 10 security audit (static, dependency, and runtime) |
| **powershell-expert** | PowerShell scripting, modules, and GUI development reference |
| **pr-bug-finder** | Adversarial 3-agent pipeline for finding bugs in PRs |
| **reflect** | Session retrospective — extract learnings, update memory and guidance files |
| **sdlc** | Structured SDLC pipeline: Plan, Implement, Review, Security, QA, Accept |
| **work-issue** | End-to-end Linear issue implementation workflow |

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

| Hook | Description |
|------|-------------|
| **reject-compound-bash** | Blocks `&&`/`||`/`;` chaining, `bash -c` wrappers, `npx --prefix` |
| **normalize-git-dash-c** | Blocks `git -C` and `git -c` flags that break permission matching |
| **prefer-dedicated-tools** | Blocks `find`/`grep`/`cat`/`sed`/etc. in favor of Glob/Grep/Read/Edit |

### Config

| File | Description |
|------|-------------|
| **statusline.py** | Status line with git branch, worktree detection, context usage bar |
| **keybindings.json** | Custom Claude Code keybindings |
| **settings.json.example** | Template with hooks, plugins, and statusline configuration |
