---
name: skill-creator
description: >
  Design and author Claude Code skills with best practices from Thariq Shihipar
  and the Anthropic team. Use this skill whenever the user wants to create a new
  skill, write a SKILL.md, design a slash command, build a skill from scratch,
  improve an existing skill, or asks about skill authoring best practices. Also
  triggers when the user says "make a skill", "new skill", "skill for X", or
  "how should I write a skill".
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent, WebFetch
argument-hint: "[skill-name or description]"
---

# Skill Creator

Design and author effective Claude Code skills, guided by Thariq Shihipar's published principles from the Anthropic Claude Code team.

Before doing anything, read `${CLAUDE_SKILL_DIR}/references/thariq-guidance.md` for the full philosophy. Keep it loaded as your north star throughout. Refer to `${CLAUDE_SKILL_DIR}/references/frontmatter-reference.md` when you need frontmatter field details.

---

## Phase 1: Understand the Intent

Start by understanding what the user wants the skill to do. If they gave a name or description in `$ARGUMENTS`, use that as a starting point. Otherwise, ask.

Gather these essentials through conversation (don't dump a form -- ask naturally):

1. **What does the skill do?** Get a concrete description of the task it automates or guides.
2. **What archetype is it?** Map it to one of Thariq's nine categories (Library/API Reference, Product Verification, Data Fetching, Business Process, Code Scaffolding, Code Quality, CI/CD, Runbook, Infrastructure Ops). This frames the design.
3. **Who invokes it?** The user via `/slash-command`, Claude automatically, or both?
4. **What does it need?** Tools, external services, MCP servers, scripts, templates.
5. **What goes wrong?** Ask for known gotchas, edge cases, or past failures. Per Thariq: "The highest-signal content in any skill is the Gotchas section."

---

## Phase 2: Design the Skill

Before writing any files, present a design brief to the user. This is the architectural decision point.

### 2a. Choose the freedom level

Per Thariq's guidance, match specificity to fragility:

- **High freedom** (text instructions only): The skill gives context and lets Claude decide how to execute. Good for creative tasks, code review, analysis.
- **Medium freedom** (pseudocode with decision points): A preferred workflow exists but Claude adapts to context. Good for most workflow skills.
- **Low freedom** (exact scripts and commands): The operation is fragile and must be done precisely. Good for deployments, infrastructure, data migrations.

Present this choice to the user with a recommendation based on what they described.

### 2b. Plan the file structure

Decide what the skill directory needs:

```
skill-name/
├── SKILL.md              # Always required
├── references/           # If SKILL.md would exceed ~400 lines
│   └── *.md              # Domain knowledge, checklists, API docs
├── scripts/              # If the skill runs repeatable code
│   └── *.sh / *.py       # Validation, generation, data fetching
├── templates/            # If the skill produces structured output
│   └── *.md / *.json     # Output format templates
└── examples/             # If examples help Claude understand expectations
    └── *.md              # Input/output pairs
```

Most skills only need `SKILL.md`. Only add subdirectories when there's a concrete reason -- don't scaffold empty folders.

### 2c. Draft the description

This is the most important piece. Per Thariq: Claude undertriggers skills, so descriptions should be slightly "pushy."

Write the description and show it to the user. It must:
- State what the skill does in third person
- List specific trigger phrases and contexts
- Include synonyms for the core concept
- Err on the side of triggering too often (the user can always dismiss)

---

## Phase 3: Write the Skill

### 3a. Write SKILL.md

Compose the frontmatter and body. Follow these principles from Thariq:

**On tone:** Explain *why* things matter rather than using heavy-handed MUSTs. If you catch yourself writing ALWAYS or NEVER in caps, reframe it as reasoning. "Claude responds better to understanding the reasoning than to capitalized imperatives."

**On content:** Every line must earn its tokens. Challenge each paragraph:
- "Does Claude already know this?" If yes, cut it.
- "Does this paragraph justify its token cost?" If not, trim it.
- "Am I stating the obvious?" Focus on what pushes Claude beyond default patterns.

**On structure:**
- Keep the body under 500 lines
- Use numbered phases for workflow skills
- Use imperative tone for instructions ("Read the file", "Verify the output")
- Include a Gotchas section compiled from real failure points
- Put lengthy reference material in `references/` files, not inline

**On scripts:** If test prompts would consistently result in Claude writing the same helper script, bundle it in `scripts/`. "That's a strong signal the skill should bundle that script."

### 3b. Write reference files (if needed)

Reference files should:
- Stay one level deep from SKILL.md (no nested references)
- Include a table of contents if over 100 lines
- Contain domain knowledge that doesn't change often

### 3c. Write scripts (if needed)

Scripts should:
- Handle errors explicitly rather than punting to Claude
- Be executable and self-contained
- Include a usage comment at the top
- Use forward slashes for paths (never Windows-style backslashes)

---

## Phase 4: Review Against Thariq's Checklist

Before presenting the skill to the user, run through this checklist (from Thariq's guidance and official Anthropic best practices). Report the results.

- [ ] Description is specific, includes key terms, and is slightly "pushy"
- [ ] Description includes both what the skill does AND when to use it
- [ ] SKILL.md body is under 500 lines
- [ ] Heavy reference content is in separate files (if applicable)
- [ ] No time-sensitive information that will go stale
- [ ] Consistent terminology throughout
- [ ] Examples are concrete, not abstract
- [ ] File references are one level deep from SKILL.md
- [ ] Workflows have clear numbered steps
- [ ] Scripts handle errors rather than punt to Claude (if applicable)
- [ ] Gotchas section exists and reflects real failure modes
- [ ] No ALWAYS/NEVER in caps without explaining why
- [ ] Freedom level matches task fragility
- [ ] Token budget is respected -- no obvious bloat

---

## Phase 5: Place the Skill

Determine where the skill should live:

| Location | Path | When to use |
|----------|------|-------------|
| Personal | `~/.claude/skills/<name>/SKILL.md` | User's own productivity tools |
| Project | `.claude/skills/<name>/SKILL.md` | Project-specific workflows shared with team |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Distributable, reusable across projects |

Ask the user which location fits. Default to personal (`~/.claude/skills/`) unless they indicate otherwise.

Write the files to the chosen location. If the user has the `agent-skills` repo and wants the skill there, tell them to use `/agent-skills add skill <name>` for proper registration, or offer to write directly if they prefer.

---

## Phase 6: Test Prompts

Per Thariq, create at least 3 test prompts -- a mix of should-trigger and should-not-trigger scenarios. Present them to the user:

**Should trigger:**
- 2-3 prompts that should activate this skill

**Should NOT trigger:**
- 1-2 prompts that are adjacent but shouldn't activate it

Ask the user if they want to run any of these now to validate. If they do, note the results and suggest description or body adjustments based on what you observe.

---

## Phase 7: Iteration Guidance

After the skill is written, remind the user of Thariq's iteration loop:

> The best way to understand skills is to get started, experiment, and see what works. Most skills began as a few lines and a single gotcha, and got better because people kept adding to them as Claude hit new edge cases.

Suggest they:
1. Use the skill on a real task
2. Read the transcript (not just the output) to see where Claude struggled
3. Add gotchas for any failure points
4. Remove lines that aren't pulling their weight
5. If Claude keeps generating the same helper code, bundle it as a script
6. Generalize from feedback -- don't overfit to specific examples

---

## Rules

- Never write a skill without understanding the user's intent first. Ask before assuming.
- Always show the design brief (Phase 2) before writing files. Get alignment.
- Prefer editing an existing skill over creating a new one if the user has something close.
- If the user asks to *improve* a skill, read it first, then apply Thariq's principles to identify what's not pulling its weight.
- Reference files go in `references/`, not inline in SKILL.md.
- The description is the hardest part to get right. Spend time on it.
