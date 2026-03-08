---
name: agent-skills
description: >
  Scaffold, remove, or list skills, hooks, commands, agents, and config in the
  agent-skills repo. Encodes all repo conventions so Claude follows them correctly.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
user_invocable: true
argument: "<add|remove|list> [type] [name] — manage repo content"
---

# Agent-Skills Meta-Skill

Manage the agent-skills repo: scaffold new content with correct templates, remove content with full cleanup, or list the current inventory.

## Usage

```
/agent-skills add <type> <name>     — scaffold new content
/agent-skills remove <type> <name>  — delete content and clean up registrations
/agent-skills list [type]           — show current inventory
```

**Types:** `skill`, `hook`, `command`, `agent`, `config`

---

## Phase 1: Validate

1. Confirm the current working directory is the agent-skills repo root. Check for the presence of `install.py` and the `skills/`, `hooks/`, `commands/`, `agents/`, `config/` directories. If not found, tell the user and stop.
2. Parse the argument string into `<verb>` (`add`, `remove`, `list`), `<type>`, and `<name>`.
3. If arguments are missing or invalid, ask using AskUserQuestion.
4. For `add`: confirm `<name>` doesn't already exist for that type. For `remove`: confirm it does exist.

---

## Phase 2: List

If the verb is `list`, display the current inventory and stop.

1. Read `README.md` from the repo root.
2. If `<type>` is specified, show only that section's table. Otherwise show all tables.
3. Format output as the table contents. Done — no further phases needed.

---

## Phase 3: Scaffold (add verb only)

Create files using the templates below based on `<type>`.

### Skill

Create `skills/<name>/SKILL.md`:

```yaml
---
name: <name>
description: <ask user or infer from name>
allowed-tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
user_invocable: false
---
```

Follow with a markdown body. Ask the user for:
- Description (one line)
- Whether it should be user-invocable (if yes, add `argument:` field)
- Which tools it needs (offer common sets)

Use imperative tone for task instructions. Use numbered phases/steps for workflow skills. Follow the conventions from existing skills (work-issue, reflect, init-repo).

### Hook

Create `hooks/<name>.py`:

```python
"""Claude Code PreToolUse hook: <one-line description>.

<Multi-line explanation of what this hook blocks and why.>
"""

import json
import sys


def deny(reason: str) -> None:
    """Output JSON denial to stdout and exit."""
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

    # TODO: Add detection logic here
    # if <condition>:
    #     deny("BLOCKED: <reason with guidance on what to do instead>")

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
```

Ask the user for:
- What the hook should block and why
- Which tool(s) it matches (`Bash`, `Read|Edit|Write|Glob|Grep`, etc.)

Add `import re` only if regex patterns are needed. Keep the template minimal — the user fills in the detection logic.

### Command

Create `commands/<name>.md`:

```yaml
---
description: <one-line description>
argument-hint: [optional-args]
allowed-tools: Bash, Read, Glob, Grep
---

<Markdown instructions for the command.>
```

Ask the user for description and what the command does.

### Agent (Native)

Create `agents/<name>.md`:

```yaml
---
name: <name>
description: <multi-line description>
model: opus
color: pink
---

# <Agent Title>

<System prompt / instructions as markdown.>
```

Ask the user for:
- Description
- Model (opus or sonnet)
- What the agent does (system prompt content)

### Agent (SDK / Python)

Create `agents/<name>/` directory with:

1. `main.py` — entry point with `Claude()` client setup
2. `prompts.py` — system prompts as string constants
3. `schemas.py` — Pydantic models for structured output (if needed)
4. `pyproject.toml` — package metadata with `anthropic` dependency
5. `.env.example` — template for required environment variables

Ask the user for the agent's purpose and design before scaffolding.

### Config

Create the file in `config/<name>.<ext>`. Ask the user what the config file does and where it should be symlinked to under `~/.claude/`.

---

## Phase 4: Register

After creating files, register them in the appropriate places.

### Hook registration

1. **settings.json.example**: Read `config/settings.json.example`. Add the hook to the appropriate matcher group under `hooks.PreToolUse`. If no matching group exists, create one. Use `~` paths:

   ```json
   {
     "type": "command",
     "command": "python ~/.claude/hooks/<name>.py",
     "timeout": 10
   }
   ```

2. **Live settings.json**: Read `~/.claude/settings.json`. Add the same entry. The live file may use absolute paths — match the existing style.

3. **Symlink**: Hooks are picked up automatically via the `hooks/` directory symlink. No code change needed in install.py for hooks.

### Config registration

1. **install.py**: Add a `link_file()` call. Read the file first, then add the new line in the appropriate section (after the existing `link_file` calls for config):

   ```python
   link_file(REPO_DIR / "config" / "<filename>", CLAUDE_DIR / "<target-name>")
   ```

2. If the config should be referenced in `settings.json.example`, update that too.

### Skills, commands, agents (native)

No registration needed — these are picked up automatically via the directory symlinks.

### Agents (SDK)

No registration in install.py needed — install.py already globs `agents/*/pyproject.toml` and installs them.

---

## Phase 5: Remove (remove verb only)

1. **Delete the files:**
   - Skill: remove `skills/<name>/` directory
   - Hook: remove `hooks/<name>.py`
   - Command: remove `commands/<name>.md`
   - Agent (native): remove `agents/<name>.md`
   - Agent (SDK): remove `agents/<name>/` directory
   - Config: remove `config/<name>.<ext>`

2. **Clean up registrations:**
   - Hook: remove entries from both `config/settings.json.example` and `~/.claude/settings.json`.
   - Config: remove the `link_file()` call from `install.py`. Remove the symlink under `~/.claude/`.
   - Skills/commands/agents: no cleanup needed (directory symlinks handle it).

3. **Verify** the removal didn't break JSON syntax in settings files. Read them back and confirm they parse.

---

## Phase 6: Update README

After add or remove, update `README.md` in the repo root.

1. Read the current README.
2. Find the correct inventory table for the type:
   - Skills: `### Skills` table — columns: `Skill`, `Description`
   - Commands: `### Commands` table — columns: `Command`, `Description`
   - Agents: `### Agents` table — columns: `Agent`, `Type`, `Description`
   - Hooks: `### Hooks` table — columns: `Hook`, `Matches`, `Description`
   - Config: `### Config` table — columns: `File`, `Description`
3. For `add`: insert a new row in alphabetical order. Bold the name. For hooks, include the `Matches` column value. For agents, include the `Type` column (Native or SDK).
4. For `remove`: delete the row.
5. Use Edit to make the change — do not rewrite the entire README.

---

## Phase 7: Install

Run the installer to re-create symlinks:

```bash
python install.py
```

This picks up new hooks (via glob), new config (if install.py was updated), and verifies all symlinks are intact.

---

## Phase 8: Commit

Stage and commit all changes:

```bash
git add -A
git commit -m "feat(agent-skills): <add|remove> <type> <name>"
```

Ask the user if they want to push.

---

## Rules

- Never overwrite existing files without asking the user first.
- Always read files before editing them.
- Keep settings.json files valid JSON — verify after editing.
- Use `~` paths in `settings.json.example`; match existing style in live `settings.json`.
- Hooks use a directory symlink (like skills/commands/agents) — no install.py edit needed for hooks.
- Config files DO need an install.py edit (explicit `link_file()` call).
- Alphabetical order in README tables and install.py entries.
