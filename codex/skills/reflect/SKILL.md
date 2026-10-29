---
name: reflect
description: Reflect on the current Codex session, identify durable workflow or project learnings, and propose concise updates to AGENTS.md, skills, hooks, or maintained knowledge files.
---

# Session reflection

Analyze the conversation and observable outcomes before asking the user anything. The goal is to preserve useful learning without turning one session into permanent clutter.

## Assess the session

Summarize:

- what worked and why;
- incorrect assumptions, wasted turns, missed context, tool misuse, or scope drift;
- prompt ambiguity that materially affected the result;
- non-obvious environment, workflow, project, or domain facts learned.

Use concrete evidence from the session. Do not manufacture criticism to fill every category.

## Decide what is durable

Classify each learning:

- global personal guidance: applies across repositories and belongs in `~/.codex/AGENTS.md`;
- project guidance: belongs in the nearest applicable `AGENTS.md`;
- reusable workflow: belongs in a skill;
- mechanical enforcement: belongs in a hook;
- maintained domain note: belongs in an existing project knowledge file;
- one-off: report it but do not persist it.

Codex memories are product-managed state, not a text file to edit directly. Do not modify SQLite databases or invent a memory path. Prefer explicit maintained files only when the learning is stable and actionable.

## Read before proposing

Read each proposed target and its applicable parent guidance. Check for duplicates, scope conflicts, and whether a skill or hook already owns the rule. Keep always-loaded guidance short.

## Propose changes

Present the reflection first, followed by exact minimal diffs for each proposed file. Explain the session evidence and why that file is the right scope.

Do not apply reflection-derived changes until the user approves them. This approval requirement applies even when the original session involved broad editing authority, because reflection changes future behavior beyond the completed task.

After approval, re-read targets, apply only the approved changes, validate affected skills or hooks, and summarize what was preserved.
