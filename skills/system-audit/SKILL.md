---
name: system-audit
description: >
  Audit the Claude Code system for staleness, redundancy, gaps, and token waste.
  Covers skills, hooks, commands, agents, config, plugins, MCPs, memory files, and
  CLAUDE.md guidance. Produces actionable recommendations: deprecate, consolidate,
  add, update. Can be invoked manually or run periodically as hygiene.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, AskUserQuestion
user_invocable: true
argument: "[focus] — optional focus area: skills | hooks | memory | guidance | plugins | gaps | all (default: all)"
---

# System Audit

You are auditing the user's Claude Code system for health, efficiency, and completeness. This is a meta-skill: it examines the tooling itself, not a codebase.

**Two complementary goals:**
1. **What's dead weight?** — Find things to deprecate, consolidate, or trim
2. **What's missing?** — Find recurring patterns that should be formalized as skills, hooks, agents, or guidance

Work through the phases below in order. Skip phases outside the requested focus area.

---

## Phase 0: Resolve Paths and Parse Arguments

### Paths

Resolve these once and reference throughout:

| Variable | Resolution |
|----------|------------|
| `$SKILLS_REPO` | Glob for `~/Source/agent-skills`. If not found, check `~/.claude/skills` symlink target. |
| `$SKILLS_DIR` | `$SKILLS_REPO/skills/` |
| `$HOOKS_DIR` | `$SKILLS_REPO/hooks/` |
| `$COMMANDS_DIR` | `$SKILLS_REPO/commands/` |
| `$AGENTS_DIR` | `$SKILLS_REPO/agents/` |
| `$CONFIG_DIR` | `$SKILLS_REPO/config/` |
| `$SETTINGS` | `~/.claude/settings.json` |
| `$MEMORY_DIR` | From system prompt (`You have a persistent auto memory directory at ...`) or Glob `~/.claude/projects/*/memory/MEMORY.md` |
| `$GLOBAL_CLAUDE_MD` | `~/.claude/CLAUDE.md` |

### Arguments

Parse the optional focus area from the skill argument:
- No argument or `all` → run all phases
- `skills` → Phase 1 only
- `hooks` → Phase 2 only
- `memory` → Phase 3 only
- `guidance` → Phase 4 only
- `plugins` → Phase 5 only
- `gaps` → Phase 6 only

---

## Phase 1: Skills & Commands & Agents Audit

### 1a. Inventory

Read every `SKILL.md` in `$SKILLS_DIR/*/SKILL.md`. For each skill, record:
- Name, description, `user_invocable`, `allowed-tools`
- Whether it has `references/` subdirectory
- Line count (proxy for complexity)

Read every command in `$COMMANDS_DIR/*.md`. Read every agent in `$AGENTS_DIR/` (both `.md` files and `*/` directories).

### 1b. Overlap Detection

Compare every pair of skills for functional overlap. Check:
- Do two skills read the same Plane issue and create a branch? (likely overlap)
- Do a skill and a command invoke the same agent? (redundancy)
- Does a skill duplicate a built-in plugin's capability? (check plugin list in `$SETTINGS`)

Flag pairs with >40% step overlap.

### 1c. Staleness Detection

For each skill, check:
- **Hardcoded paths**: Grep for absolute paths or project-specific references (e.g., `Receipts.slnx`, specific directory names). These make skills non-portable.
- **Outdated tool references**: Does the skill reference tools or commands that no longer exist?
- **Version-pinned assumptions**: Does the skill assume a specific version of a tool?

### 1d. Usage Signal (if session data available)

Check `~/.claude/projects/*/` for session data. If conversation logs exist, grep for skill invocation patterns (`/skill-name`, `Skill tool` calls). Flag skills with zero invocations across all sessions.

If no session data is available, skip this step and note it.

### Output

For each finding, tag it:
- `[DEPRECATE]` — remove entirely
- `[CONSOLIDATE]` — merge with another item
- `[UPDATE]` — fix staleness/hardcoding
- `[KEEP]` — healthy, no action needed

---

## Phase 2: Hooks Audit

### 2a. Inventory

Read every `.py` file in `$HOOKS_DIR/`. For each hook, record:
- Name, what it blocks, which tools it matches
- Whether it's registered in `$SETTINGS` (check `hooks.PreToolUse`)

### 2b. Redundancy Check

Check if any hook enforces behavior that:
- Claude Code now handles natively (e.g., worktree isolation, tool routing)
- Another hook already covers (overlapping patterns)
- A CLAUDE.md instruction duplicates (belt-and-suspenders)

### 2c. Effectiveness Check

For each hook, assess:
- Does the denial message give Claude actionable guidance? (Good hooks say "do X instead", not just "blocked")
- Is the matching pattern too broad? (blocking legitimate commands)
- Is the matching pattern too narrow? (missing variants it should catch)

### Output

Tag each hook: `[DEPRECATE]`, `[UPDATE]`, `[KEEP]`.

---

## Phase 3: Memory Audit

### 3a. Read All Memory Files

Glob for all `MEMORY.md` and `*.md` files in every `$MEMORY_DIR` across all projects under `~/.claude/projects/`.

### 3b. Staleness Detection

For each entry in each memory file, check:
- **Version references**: Does it mention a specific version that may be outdated? (e.g., "Bun v1.3.10-canary.63")
- **Workaround entries**: Is the underlying problem likely fixed? (check if the workaround references a bug number or version)
- **Tool path references**: Do referenced paths still exist? (spot-check with Glob)
- **Duplicate entries**: Is the same fact documented in multiple memory files?

### 3c. Documentation Duplication

Cross-reference memory entries against:
- Hook docstrings (hooks document themselves; memory shouldn't repeat)
- Skill SKILL.md files (skills document their own conventions)
- CLAUDE.md files (guidance shouldn't be duplicated across tiers)

### 3d. Token Cost Assessment

Count lines in each memory file. Files loaded into every session cost tokens proportional to their size. Flag files over 50 lines — are all lines earning their keep?

### Output

For each stale, duplicate, or oversized entry:
- `[REMOVE]` — delete the entry
- `[MOVE]` — relocate to correct file (e.g., from MEMORY.md to a domain file)
- `[UPDATE]` — revise with current information
- `[KEEP]` — still accurate and useful

---

## Phase 4: Guidance Audit (CLAUDE.md files)

### 4a. Read All CLAUDE.md Files

Read `$GLOBAL_CLAUDE_MD` and Glob for `**/CLAUDE.md` in active project directories.

### 4b. Effectiveness Assessment

For each CLAUDE.md, evaluate:
- **Token efficiency**: How many tokens does this file consume per session? Is every line earning its keep?
- **Actionability**: Does each instruction change Claude's behavior? Or is it informational-only?
- **Enforcement**: Is the instruction enforced by a hook (reliable) or just stated (best-effort)?
- **Scope correctness**: Is project-specific guidance in the global file? Is global guidance in a project file?

### 4c. Missing Guidance

Check for common guidance gaps:
- **Workflow decision tree**: When to use which skill? When to parallelize vs. serialize?
- **Build/test commands**: Are they documented per-project or discovered each session?
- **Branch strategy**: Documented once or rediscovered?
- **Known friction points**: Are common agent trip-ups documented?

### Output

For each finding:
- `[TRIM]` — remove or shorten (not earning its tokens)
- `[MOVE]` — relocate to correct scope
- `[ADD]` — new guidance needed
- `[KEEP]` — working well

---

## Phase 5: Plugins & MCPs Audit

### 5a. Inventory

Read `$SETTINGS` and extract:
- All enabled plugins (under `plugins` or `enabledPlugins`)
- All MCP server configurations
- All permission rules

### 5b. Relevance Check

For each plugin:
- Does the user work in this language/framework? Cross-reference against project directories and session history.
- Does it overlap with a custom skill?

For each MCP:
- Is it actively used? (Check for tool calls in session data if available)
- Does it require authentication that may have expired?

### 5c. Missing Integrations

Based on observed workflow patterns, identify MCPs or plugins that should exist but don't:
- Does the user frequently shell out to a CLI that could be an MCP? (e.g., `gh`, `docker`, `aspire`)
- Are there communication tools the user mentions but can't access? (e.g., Slack, Teams)
- Are there monitoring/observability gaps?

### Output

For each item:
- `[REMOVE]` — unused, remove from settings
- `[ADD]` — missing integration that would help
- `[KEEP]` — actively used

---

## Phase 6: Gap Analysis

This phase synthesizes findings from all previous phases to identify what's MISSING.

### 6a. Pattern Mining

Review the conversation history (if available) or the user's project structure for recurring manual work:
- Tasks the user does repeatedly that aren't captured as skills
- Multi-step sequences that could be automated
- Decisions the user makes repeatedly that could be encoded as guidance

### 6b. Skill Gaps

For each identified pattern, assess:
- Would a skill save meaningful time? (>3 steps, done more than twice)
- Would a hook prevent a recurring mistake?
- Would an agent definition formalize a subagent pattern?
- Would a CLAUDE.md entry prevent re-learning?

### 6c. Cross-Cutting Concerns

Check for systemic gaps:
- **Orchestration**: Are parallel agent patterns ad-hoc or formalized?
- **Testing**: Is there a consistent testing skill/pattern?
- **Release**: Is the release flow (version, tag, publish, close issues) automated?
- **Monitoring**: Can agents self-assess their own effectiveness?

### Output

For each gap:
- `[SKILL]` — should be a new skill
- `[HOOK]` — should be a new hook
- `[AGENT]` — should be a new agent definition
- `[GUIDANCE]` — should be a CLAUDE.md/MEMORY.md entry
- `[MCP]` — should be an MCP integration

---

## Phase 7: Report

Present findings as a structured report to the user.

### Format

```
## System Audit Report

### Dead Weight (deprecate/remove)
| Item | Type | Reason | Action |
|------|------|--------|--------|
| ... | skill/hook/memory/plugin | ... | DEPRECATE/REMOVE |

### Consolidation Opportunities
| Items | Type | Overlap | Recommendation |
|-------|------|---------|----------------|
| ... | skill+skill / skill+command | ... | Merge into X |

### Staleness (update needed)
| Item | Type | Issue | Fix |
|------|------|-------|-----|
| ... | memory/skill/guidance | ... | UPDATE: ... |

### Token Waste
| File | Lines | Tokens (est.) | Recommendation |
|------|-------|---------------|----------------|
| ... | N | ~N*4 | TRIM/MOVE/KEEP |

### Missing (gaps to fill)
| Pattern | Frequency | Recommendation | Type |
|---------|-----------|----------------|------|
| ... | ... | ... | SKILL/HOOK/AGENT/GUIDANCE/MCP |
```

### Severity

Rank findings by impact:
1. **High** — Wastes significant tokens every session, causes errors, or blocks workflows
2. **Medium** — Adds friction or confusion, fixable with moderate effort
3. **Low** — Nice-to-have cleanup, no urgency

---

## Phase 8: Apply Changes

After presenting the report, ask the user what to apply.

Use AskUserQuestion:
- question: "Which audit recommendations should I apply now?"
- header: "Apply fixes"
- multiSelect: true
- options: (group by action type, max 4)
  - "Remove dead weight (N items)"
  - "Consolidate overlapping skills/commands"
  - "Update stale memory entries"
  - "Add missing guidance"

For approved changes:
1. Re-read each target file before editing
2. Use Edit for modifications, Write only for new files
3. For skill/hook removals: use the `/agent-skills remove` convention if in the agent-skills repo
4. For settings.json changes: verify JSON validity after editing
5. Report each change as it's applied

---

## Periodic Hygiene Mode

This skill is designed to run periodically, not just on demand. When Claude detects any of these signals, it should suggest running `/system-audit`:

- **Session count milestone**: Every ~50 sessions or ~1 month since last audit
- **After major system changes**: New skill added, hook modified, plugin installed
- **After project lifecycle events**: Project completed, archived, or abandoned
- **Memory file growth**: When any MEMORY.md exceeds 60 lines
- **Skill creation burst**: When 2+ skills are created in a short period (overlap risk)

When suggesting proactively, say:
> "It's been [N sessions / N weeks] since the last system audit. Want me to run `/system-audit` to check for staleness and gaps?"

Track the last audit date in `$MEMORY_DIR/MEMORY.md` under a `## System Audit` section:
```
## System Audit
- Last audit: YYYY-MM-DD
- Findings applied: N of M
- Next suggested: ~YYYY-MM-DD
```

---

## Rules

- **Read before judging.** Never flag something as stale without reading its contents.
- **No false positives.** Only flag items you're confident about. "Might be unused" is not enough — check.
- **Respect the user's system.** This is an audit, not a rewrite. Recommend, don't dictate.
- **Minimize token cost of the audit itself.** Use Glob/Grep before Read. Don't read files you won't analyze.
- **No compound Bash commands** — no `&&`, `||`, `;` (hook constraint).
- **Cross-reference, don't duplicate.** If a finding applies to multiple phases, report it once in the most relevant phase.
- **Actionable recommendations only.** Every finding must have a concrete next step.
