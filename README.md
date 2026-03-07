# agent-skills

Canonical source for Claude Code skills, commands, agents, and config. Clone on any machine and run `install.sh` to set up symlinks.

## Structure

```
skills/          -> ~/.claude/skills
commands/        -> ~/.claude/commands
agents/          -> ~/.claude/agents
config/
  statusline.py  -> ~/.claude/statusline.py
  keybindings.json -> ~/.claude/keybindings.json (if exists)
  settings.json.example  (template, not symlinked)
```

## Setup (new machine)

```bash
git clone https://github.com/mggarofalo/agent-skills.git ~/Source/agent-skills
cd ~/Source/agent-skills
./install.sh
```

Optional:
```bash
cd agents/pr-bug-finder && pip install -e .
```

## Syncing changes

Since `~/.claude/skills`, `commands`, and `agents` are symlinks into this repo, any edits are already reflected here. To push:

```bash
# Push everything
./sync.sh

# Push specific folders
./sync.sh skills commands

# Custom commit message
./sync.sh -m "add new skill for X"
```

On other machines, just `git pull` — symlinks pick up the changes automatically.

## Adding new content

- **Skill:** Create `skills/<name>/SKILL.md`
- **Command:** Create `commands/<name>.md`
- **Agent:** Create `agents/<name>/` with source files
- **Config file:** Add to `config/` and update `install.sh` with a new `link_file` entry

## What's included

### Skills
- **pr-bug-finder** — Adversarial 3-agent pipeline for finding bugs in PRs
- **work-issue** — End-to-end Linear issue implementation workflow

### Commands
- **find-bugs** — Invoke the PR bug-finder agent from Claude Code

### Agents
- **pr-bug-finder** — Python agent using Claude Agent SDK with hunter/challenger/synthesizer pipeline

### Config
- **statusline.py** — Custom Claude Code status line showing git branch and model info
- **settings.json.example** — Template for Claude Code settings
