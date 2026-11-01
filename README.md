# agent-skills

Canonical source for parallel Claude Code and Codex skills, agents, hooks, and config. Each host has its own native layer so improvements do not break the other.

## Structure

```
skills/          -> ~/.claude/skills
commands/        -> ~/.claude/commands
agents/          -> ~/.claude/agents
hooks/           -> ~/.claude/hooks
router/          -> ~/.claude/agent-router and ~/.codex/agent-router
config/
  statusline.py    -> ~/.claude/statusline-command.py
  keybindings.json -> ~/.claude/keybindings.json
  settings.json.example  (template — copied only if settings.json is missing)
codex/
  skills/        -> ~/.agents/skills
  hooks/         -> ~/.codex/hooks
  agents/        -> ~/.codex/agents
  config/hooks.json -> ~/.codex/hooks.json
  config/tui.toml    (native Codex status-line source)
```

## Setup

```
git clone https://github.com/mggarofalo/agent-skills.git ~/Source/agent-skills
cd agent-skills
python install.py

# Install the separate Codex-native layer
python install-codex.py
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

Claude links point at the top-level directories. Codex links point at `codex/`. Edit the matching host layer; do not change the Claude copy solely to fix a Codex behavior or vice versa.

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
| **agent-skills** | Scaffold, remove, or list skills, hooks, commands, agents, and config |
| **bulk-read** | Route large mechanical reads through a low-cost stateless worker and return source-located bullets |
| **clear-writing** | Plain-English writing style for reports, summaries, and guidance |
| **code-write** | Generate a new pattern-matching file from a required reference through a low-cost stateless worker |
| **curriculum-research** | Compare and trial curricula against a learner’s observed skills and family constraints |
| **fix-develop** | Land a fix on the base branch as its own PR, then rebase and resume |
| **idiomatic-swift** | Build and review Swift and SwiftUI using current language conventions and native Apple platform behavior |
| **init-repo** | GitHub repo scaffolding with CI, guidance files, branch-protection rulesets, and config per language |
| **learning-expectations** | Interpret age and grade expectations from standards, milestones, and content guides |
| **marvelcdb** | MarvelCDB (Marvel Champions) card database CLI — pipeable local lookups, deckbuilding data, OAuth2 deck editing |
| **owasp-top-10** | OWASP Top 10 security audit (static code and dependency scanning) |
| **plane** | Plane CLI reference — auto-generated, regenerate after every CLI upgrade |
| **qlmarkdown** | Render Markdown to standalone styled HTML via qlmarkdown_cli (cmark-gfm) |
| **recall** | Search past Claude Code and Codex session history (temporal, topic, graph) |
| **ramp-reimbursements** | Collect AT&T bills into a local PDF cache and prepare monthly Ramp reimbursement drafts |
| **reflect** | Session retrospective — extract learnings, update memory and guidance files |
| **rex-orchestration** | Delegate to Claude workers in Rex terminals instead of subagents; orchestrator and worker protocol |
| **resolve-conflicts** | Resolve merge conflicts on a PR by rebasing, resolving per-category, and force-pushing |
| **system-audit** | Audit Claude Code system for staleness, redundancy, gaps, and token waste |
| **work-issue** | End-to-end Plane issue implementation workflow |

### Commands

| Command | Description |
|---------|-------------|
| **find-bugs** | Invoke the pr-bug-finder agent from Claude Code |

### Agents

| Agent | Type | Description |
|-------|------|-------------|
| **pr-bug-finder** | SDK (Python) | Hunter/challenger/synthesizer adversarial bug analysis |

### Hooks

| Hook | Event / Matches | Description |
|------|-----------------|-------------|
| **large-file read router** | PreToolUse · `Read\|Bash` | Redirects reads over 350 lines to a low-cost stateless worker |
| **block-destructive-ops** | PreToolUse · `Bash\|Read\|Edit\|Write` | Safety net for `--dangerously-skip-permissions`: blocks destructive git/filesystem/network ops, `bash -c`/`sh -c` wrapper evasion, and reads/writes of sensitive files |
| **block-private-tracker-refs** | PreToolUse · `Bash\|PowerShell`, browser text entry, email send/draft | Blocks mentions of a private issue tracker (hosts and work-item IDs from an uncommitted local config) in outward-facing actions: commits/pushes/`gh`/`glab` in any repo with a remote, HTTP requests to external hosts, browser typing, email. Also usable as `commit-msg`/`pre-push` git hooks in external clones |
| **enforce-worktree-paths** | PreToolUse · `Read\|Edit\|Write\|Glob\|Grep` | Prevents agents in worktrees from reading/writing the original repo root |
| **session-recall export** | Stop · PostCompact · SubagentStop · SessionEnd | Incrementally exports bounded transcript chunks and coalesces QMD update/embed work |

### Low-cost worker router

The shared `router/` layer keeps mechanical token-heavy work out of the frontier model's
context. A `PreToolUse` guard redirects unbounded `Read`, `cat`, `head`, `tail`, `less`, and
`more` calls when they would return more than 350 lines. Bounded reads of at most 350 lines
still pass through. The `bulk-read` skill returns source-located bullets; `code-write` creates
one new file from a required reference and a specification.

Claude workers use Haiku with tools disabled and session persistence off. Codex workers use
Luna at low reasoning effort in an ephemeral, read-only session. Both launchers cap worker
calls at 30 seconds. Override their models with `AGENT_ROUTER_CLAUDE_MODEL` or
`AGENT_ROUTER_CODEX_MODEL`; override the line threshold with `AGENT_ROUTER_LINE_THRESHOLD`.

### Config

| File | Description |
|------|-------------|
| **statusline.py** | Status line with git branch, worktree detection, context usage bar |
| **keybindings.json** | Custom Claude Code keybindings |
| **settings.json.example** | Template with hooks, plugins, and statusline configuration |

## Codex-native layer

The `codex/` tree carries rewritten versions of all 16 shared skills plus a native **find-bugs** skill. Claude's SDK bug-finder remains untouched; Codex uses a read-only `pr_bug_finder` custom agent and parallel reviewer workflow instead.

The **ramp-reimbursements** skill (in both layers) collects missing AT&T phone and internet bills, maintains a local PDF cache with expected billing dates, and prepares monthly Ramp drafts using the $75 phone cap, payment dates, duplicate checks, and pending-payment handling.

Codex hooks use native `Bash` and `apply_patch` events, route large shell reads through the shared worker, recognize Codex-managed Git worktrees, protect Codex configuration, and refresh Claude history in place plus Codex history under `~/.agent-history/codex-sessions`. Transcript refresh runs after every completed turn, compaction, subagent, and session. It parses only newly appended rollout bytes, preserves the full pre-compaction transcript in bounded chunks, coalesces concurrent workers, and runs QMD only when chunks changed. The live hook definition is `codex/config/hooks.json`.

The native Codex status line is defined in `codex/config/tui.toml`. It mirrors the useful parts of Claude's scripted status line with directory, Git branch and branch changes, model and reasoning level, context usage, session tokens, and estimated thread cost. Codex supports a single line of predefined fields, so Claude's dirty-file counters, duration, and literary context messages do not have native equivalents.

Run `python install-codex.py` after pulling changes. Existing non-linked Codex files are backed up under `~/.codex/backups/`, and changed hook definitions must be reviewed with `/hooks`.
