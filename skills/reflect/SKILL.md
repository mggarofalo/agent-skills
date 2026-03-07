---
name: reflect
description: Reflect on this session — extract learnings, update memory and guidance files, update domain knowledge, and surface prompt clarity hints
allowed-tools: Read, Edit, Write, Glob, AskUserQuestion
---

# Session Reflection

You are conducting an autonomous retrospective on this conversation. Your job is self-improvement: analyze what happened, surface what you got wrong or could do better, and propose concrete changes. Do NOT default to interviewing the user — they invoked /reflect to get your analysis, not to answer questions.

**Core principle:** Reflect first, ask only if genuinely stuck.

Your goals are:
1. Autonomously identify what went well, what went wrong, and what should change
2. Extract durable learnings worth persisting to memory or guidance files
3. Surface areas where Claude's behavior should improve (wrong assumptions, wasted turns, missed context)
4. Identify prompt clarity patterns the user should know about
5. Apply approved updates with user confirmation

Work through the phases below in order.

---

## Phase 0: Resolve the Memory Directory

The auto-memory directory varies per project. Before doing anything else, determine it:

1. Check the system prompt for a line like `You have a persistent auto memory directory at ...`. Extract that path — this is `$MEMORY_DIR`.
2. If not found, Glob for `C:/Users/mggar/.claude/projects/*/memory/MEMORY.md` and use the directory of the first match.
3. If still not found, fall back to `C:/Users/mggar/.claude/projects/C--Users-mggar/memory/`.

Use `$MEMORY_DIR` for all MEMORY.md and domain knowledge file references throughout.

---

## Phase 1: Autonomous Session Analysis

Do NOT interview the user by default. Instead, scan the full conversation yourself and produce a structured self-assessment. Only use AskUserQuestion if you encounter genuine ambiguity that blocks your analysis (e.g., you can't tell whether the user was satisfied with an outcome, or two interpretations of an event are equally plausible).

### Self-Assessment Output

Present your findings to the user under the heading **"Session Reflection"** with these sections:

#### What Went Well
- Approaches, tool sequences, or decisions that were effective
- Moments where Claude correctly anticipated what the user needed

#### What Could Improve
This is the most important section. Be honest and specific:
- Wrong assumptions Claude made (and what the correct assumption should have been)
- Wasted turns — places where Claude asked unnecessary questions, took a wrong path, or over-engineered
- Missed context — things Claude should have noticed from the conversation or environment but didn't
- Scope mismatches — did too much, did too little, or misread what was being asked
- Tool misuse — used the wrong tool, made unnecessary tool calls, or failed to parallelize

#### Prompt Clarity Observations
- Moments where the user's prompt was ambiguous and how Claude handled it
- Suggestions for the user (phrased constructively, not critically) on how to get better results

Keep each bullet to one concise line. No padding or filler.

---

## Phase 2: Categorize Learnings

From your self-assessment, categorize actionable findings:

### A. Technical / Environment Facts
Things that are true about this user's environment that Claude should remember:
- Tool paths, executable quirks, OS-specific behavior
- Commands that were discovered or fixed
- Services, APIs, configs that are present/absent

### B. Workflow Patterns
Approaches that worked well and should be reused:
- File organization conventions followed
- Git or CI patterns used
- Testing or debugging approaches that succeeded

### C. Project-Specific Conventions
Patterns only relevant to the current repo/codebase:
- Naming conventions, architecture decisions, forbidden patterns
- Known quirks of the codebase or its toolchain

### D. Domain Knowledge Gained
Technology-specific learnings worth adding to a domain reference file:
- Patterns, idioms, or gotchas specific to a language/framework/tool (e.g., PowerShell, Python, TypeScript, Docker)
- Corrections to wrong mental models — things Claude or the user assumed that turned out to be wrong
- Version-specific behavior differences discovered this session
- Integration patterns between tools that aren't obvious

**Domain detection**: Identify which technology domains were central to the session (e.g., "PowerShell", "React", "SQL Server"). For each domain, check if a knowledge file exists at `$MEMORY_DIR/{domain-slug}.md`.

Tag domain findings as `[DOMAIN:{name}]` (e.g., `[DOMAIN:powershell]`).

Only persist knowledge that:
- Is non-obvious and wouldn't be in basic docs
- Is specific to this user's environment or workflow
- Corrects a misconception or fills a gap that surfaced in the session

### E. Claude Behavior Corrections
Things Claude got wrong or had to be corrected on:
- Wrong assumptions that should be stated explicitly in CLAUDE.md
- Instructions that needed repeating — a sign they should be written down

### F. Prompt Anti-Patterns (surfaced as tips, not written to files)
Messages from the user that caused confusion or extra turns:
- Vague scope ("fix things", "improve this")
- Missing context Claude had to ask for
- Multiple unrelated tasks bundled together
- Implicit constraints Claude had to infer

For each finding, tag it:
- `[MEMORY]` → global auto-memory (`MEMORY.md`)
- `[GLOBAL]` → global CLAUDE.md at `~/.claude/CLAUDE.md`
- `[PROJECT]` → project CLAUDE.md (nearest to working directory)
- `[PROMPT-HINT]` → user-facing clarity tip (not written to any file)
- `[SKIP]` → one-off, not worth persisting

Only tag findings as `[MEMORY]` or `[GLOBAL]` if they would apply across many different sessions or projects. Default to `[PROJECT]` or `[SKIP]` when scope is narrow.

`[DOMAIN:{name}]` findings should be short, actionable entries — a gotcha, a pattern, a correction. Not full tutorials. The domain file is a quick-reference cheat sheet, not documentation.

### When to Ask the User

Only use AskUserQuestion during this phase if:
- You genuinely cannot determine whether the user was satisfied with an outcome
- Two equally valid interpretations of a session event exist and the difference matters for what you'd persist
- A finding could go into multiple target files and the user's preference isn't clear

If none of these apply, proceed without asking.

---

## Phase 3: Read Existing Files Before Proposing Changes

Before drafting any updates, read the target files to avoid duplicating what's already there and to match the existing style:

1. Read `$MEMORY_DIR/MEMORY.md`
2. For each `[DOMAIN:{name}]` finding: check if `$MEMORY_DIR/{name}.md` exists (Glob it). Read it if found.
3. Check for a global CLAUDE.md: Glob for `C:/Users/mggar/.claude/CLAUDE.md`
4. Check for a project CLAUDE.md: Glob for `CLAUDE.md` in the current working directory, and parent directories up to 3 levels

Read each file that exists. Skip files that don't exist.

**If a domain file doesn't exist yet**: propose creating it with a minimal structure:
```
# {Domain} Knowledge

## Environment Notes
[user-specific environment facts]

## Key Patterns
[quick-reference patterns with code snippets]

## Common Gotchas
[non-obvious traps specific to this env/workflow]
```
Add a link to it from MEMORY.md under a `## Domain Knowledge` section.

---

## Phase 4: Propose Specific Changes

For each file with tagged findings, draft a minimal, concrete update.

**Format each proposal as:**

```
### Proposed update: [file path]

**Why:** [one sentence — what session event motivates this]

**Change:**
[diff block or the exact new lines to add]
```

**Rules for proposals:**
- One line per concept. CLAUDE.md and MEMORY.md are loaded into every prompt — brevity reduces cost.
- No verbose explanations in the files themselves
- Do not duplicate existing content
- Do not add section headers unless a new section is genuinely needed
- Prefer appending to existing sections over creating new ones
- Never persist one-off session details (specific filenames, temp values, WIP notes)

**For prompt clarity hints:** Do NOT write these to any file. Present them directly in your response as a bulleted list under a "Prompt Clarity Tips" heading.

---

## Phase 5: Ask the User What to Apply

After presenting all proposals and prompt hints, use AskUserQuestion to confirm:

**Question:**
- question: "Which of the proposed updates would you like to apply?"
- header: "Apply updates"
- multiSelect: true
- options: (one per proposed file, e.g.)
  - MEMORY.md — global auto-memory
  - {domain}.md — domain knowledge file (e.g., powershell.md)
  - ~/.claude/CLAUDE.md — global guidance
  - ./CLAUDE.md — project guidance

Use the actual filenames from your proposals as option labels. If there are more than 4 proposed files, group minor ones together (e.g., "All CLAUDE.md updates") to stay within the 4-option limit.

If none of the above match exactly, use the actual file names from the proposals as option labels.

---

## Phase 6: Apply Approved Changes

For each approved file:

1. Re-read the file (to catch any edits since Phase 3)
2. Use Edit (not Write) to make minimal targeted additions — do not reformat or restructure existing content
3. Confirm each edit by reporting: "Updated [file path]: added [brief description of what was added]"

If a file doesn't exist yet and needs to be created (e.g., global CLAUDE.md), use Write to create it with only the minimal content needed.

---

## Phase 7: Summary

Close the reflection with a brief summary:

**Session Reflection Summary**
- Files updated: [list or "none"]
- Key learnings preserved: [2-4 bullet points, max one line each]
- Prompt clarity tips: [bulleted list of actionable hints for the user — omit if none surfaced]

Keep the summary tight. No padding.
