---
name: system-audit
description: Audit a Codex setup for stale, redundant, broken, overly broad, or missing skills, hooks, custom agents, plugins, MCP servers, configuration, and AGENTS.md guidance.
---

# Codex system audit

Audit the tooling itself. Default to reporting findings; apply changes only when the user asks for an audit plus remediation.

## Resolve the active setup

Inspect the active `CODEX_HOME`, falling back to `~/.codex`. Locate:

- user skills at `~/.agents/skills` and `$CODEX_HOME/skills`;
- repository skills under applicable `.agents/skills` directories;
- hooks in active `hooks.json`, inline config, and enabled plugins;
- custom agents in `$CODEX_HOME/agents` and project `.codex/agents`;
- `$CODEX_HOME/config.toml` and applicable project `.codex/config.toml`;
- global and project `AGENTS.md` files;
- enabled plugins and MCP servers from active configuration.

If `~/Source/agent-skills/codex` exists, treat it as the likely personal source of truth and verify the live links before judging drift.

## Audit skills

For each skill, record its name, description, source path, supporting resources, and line count. Check:

- duplicate names or more than 40% workflow overlap;
- descriptions that are too broad, too long, or poor activation boundaries;
- Claude-only paths, tool names, slash commands, plan-mode primitives, or model names;
- absolute project paths and version-pinned assumptions;
- references that exist but are unreachable from `SKILL.md`;
- scripts that are untested, non-portable, or no longer called;
- overlap with enabled built-in or plugin skills.

Tag each item `[KEEP]`, `[UPDATE]`, `[CONSOLIDATE]`, or `[DEPRECATE]`. Do not use usage history as proof of disuse unless the available history is complete enough to support that claim.

## Audit hooks

For every hook definition and script, verify:

- the event and matcher use current Codex names;
- the command points at a Codex-owned path;
- the script consumes the documented event shape;
- denial output and exit codes are valid;
- the timeout is supported for that event;
- the message explains a safe alternative;
- the matcher is neither broader nor narrower than the implementation;
- worktree logic recognizes `$CODEX_HOME/worktrees` and custom roots;
- the hook is trusted or clearly pending review.

Treat hooks as guardrails, not complete security boundaries. Flag protection that assumes Claude `Read`, `Glob`, or `Grep` calls when Codex actually performs the work through `Bash` or `apply_patch`.

## Audit agents, plugins, and MCP

Check custom-agent TOML for required fields, focused descriptions, safe sandboxes, and unnecessary model overrides. Compare custom agents and skills with enabled plugin capabilities.

For plugins and MCP servers, distinguish configured and usable, awaiting authentication, installed but disabled, stale or duplicated, and genuinely missing. Never remove or disable an integration based only on speculation.

## Audit guidance and token cost

Read applicable `AGENTS.md` files. Check whether each instruction is actionable, scoped correctly, and not duplicated in a hook or skill. Prefer repository-specific build, test, branch, and architecture guidance near the repository rather than in the global file.

Estimate context cost using file size and line count. Flag large always-loaded guidance only when concrete content can move to a skill or reference without reducing reliability.

## Report

Lead with high-impact findings. For each finding include severity, tag, exact evidence, the recommended change, and whether applying it requires hook re-trust or a Codex restart.

Include a compact inventory and explicitly say when no evidence supports removal. If remediation was requested, preserve unrelated configuration, validate every changed artifact, and summarize what remains pending.
