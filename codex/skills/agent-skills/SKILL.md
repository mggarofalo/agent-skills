---
name: agent-skills
description: Manage the dual Claude and Codex content in the agent-skills repository, including Codex skills, hooks, custom agents, configuration, installation, and inventory.
---

# Agent skills repository

Manage `~/Source/agent-skills` without changing one agent's setup accidentally while working on the other.

## Repository layout

- `skills/`, `hooks/`, `commands/`, `agents/`, and `config/` are Claude Code sources.
- `codex/skills/`, `codex/hooks/`, `codex/agents/`, and `codex/config/` are Codex-native sources.
- `install.py` installs Claude Code sources.
- `install-codex.py` installs Codex sources.

Do not edit the Claude source merely to make a Codex port work. Apply shared factual improvements to both only when they are genuinely host-independent.

## Add or update a Codex skill

1. Create or edit `codex/skills/<name>/SKILL.md`.
2. Use lowercase letters, digits, and hyphens for the folder and `name`.
3. Keep frontmatter to `name`, `description`, and supported optional metadata. Do not copy Claude-only `allowed-tools`, `user_invocable`, or `argument` fields.
4. Put conditional detail in `references/`, deterministic helpers in `scripts/`, and generated-output material in `assets/` only when useful.
5. Use `$skill-name` in Codex-facing invocation examples.
6. Validate with the bundled Codex skill validator.

When porting a Claude skill, preserve its goal and operational invariants, then translate tool names, paths, plan or approval behavior, subagent instructions, and command syntax. Remove repeated reminders that Codex already receives from system policy.

## Add or update a Codex hook

1. Create or edit `codex/hooks/<name>.py`.
2. Register it in `codex/config/hooks.json`.
3. Match Codex canonical hook tools: shell and unified exec are `Bash`; file edits are `apply_patch` with aliases `Edit` and `Write`.
4. Read the JSON event from stdin. Exit 0 silently to allow. To deny, return the `PreToolUse` decision shape or exit 2 with the reason on stderr.
5. Make denials actionable and fail closed only when the hook is a safety guard whose payload cannot be evaluated.
6. Add focused tests for allow, deny, malformed-input, and host-specific path behavior.

Changed non-managed hook definitions require review with `/hooks` before Codex runs them.

## Add or update a custom Codex agent

Create `codex/agents/<name>.toml` with:

```toml
name = "<name>"
description = "When Codex should delegate to this agent."
sandbox_mode = "read-only"
developer_instructions = """
Focused role instructions.
"""
```

Set a model or reasoning effort only when the role benefits from a deliberate override. Otherwise let it inherit the parent.

## Install and validate

Run `python install-codex.py`, then verify:

- `~/.agents/skills` points to `codex/skills`;
- `~/.codex/hooks`, `~/.codex/hooks.json`, and `~/.codex/agents` point to their Codex sources;
- `~/.codex/config.toml` still parses, enables hooks, and retains unrelated user settings;
- every Codex `SKILL.md` passes `quick_validate.py`;
- hook tests pass and hook commands use Codex paths.

Update the README inventory when adding or removing user-visible content. Do not commit or push unless the user asks.
