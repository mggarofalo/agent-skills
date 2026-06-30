# SKILL.md Frontmatter Reference

## All Fields

| Field                      | Required    | Description |
| :------------------------- | :---------- | :---------- |
| `name`                     | No          | Display name. Lowercase letters, numbers, and hyphens only (max 64 chars). |
| `description`              | Recommended | What the skill does and when to use it. Claude uses this to decide when to apply the skill. |
| `argument-hint`            | No          | Hint shown during autocomplete. Example: `[issue-number]` |
| `disable-model-invocation` | No          | Set to `true` to prevent Claude from automatically loading this skill. |
| `user-invocable`           | No          | Set to `false` to hide from the `/` menu. Defaults to `true`. |
| `allowed-tools`            | No          | Tools Claude can use without asking permission when this skill is active. |
| `model`                    | No          | Model to use when this skill is active. Options: `opus`, `sonnet`, `haiku`. |
| `effort`                   | No          | Effort level when this skill is active. Options: `low`, `medium`, `high`, `max`. |
| `context`                  | No          | Set to `fork` to run in a forked subagent context. |
| `agent`                    | No          | Which subagent type to use when `context: fork` is set. |
| `hooks`                    | No          | Hooks scoped to this skill's lifecycle. |
| `paths`                    | No          | Glob patterns that limit when this skill is activated. |
| `shell`                    | No          | Shell for inline commands. Accepts `bash` (default) or `powershell`. |

## String Substitutions

| Variable               | Description |
| :--------------------- | :---------- |
| `$ARGUMENTS`           | All arguments passed when invoking the skill. |
| `$ARGUMENTS[N]`        | Access a specific argument by 0-based index. |
| `$N`                   | Shorthand for `$ARGUMENTS[N]`. |
| `${CLAUDE_SESSION_ID}` | The current session ID. |
| `${CLAUDE_SKILL_DIR}`  | The directory containing the skill's `SKILL.md` file. |

## Dynamic Context Injection

The `` !`<command>` `` syntax runs shell commands before the skill content is sent to Claude. The command output replaces the placeholder. Useful for injecting dynamic state like git branch, current date, or environment info.

## Invocation Control

| Frontmatter                      | You can invoke | Claude can invoke | When loaded into context |
| :------------------------------- | :------------- | :---------------- | :----------------------- |
| (default)                        | Yes            | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes            | No                | Description not in context, full skill loads when you invoke |
| `user-invocable: false`          | No             | Yes               | Description always in context, full skill loads when invoked |

## Example Frontmatter Patterns

**Simple user-invocable skill:**
```yaml
---
name: my-skill
description: >
  Does X when the user asks for Y. Use this whenever
  the user mentions Z or wants to accomplish W.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---
```

**Skill with arguments:**
```yaml
---
name: work-issue
description: >
  End-to-end implementation of a Plane issue.
  Use when the user says "work <issue>" or "pick up <issue>".
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
argument-hint: "<issue-id>"
---
```

**Auto-triggered skill (no user invocation):**
```yaml
---
name: enforce-style
description: >
  Enforces code style guidelines. Triggers automatically
  when Claude writes or edits TypeScript files.
user-invocable: false
paths: ["**/*.ts", "**/*.tsx"]
---
```

**Forked subagent skill:**
```yaml
---
name: accessibility-audit
description: >
  Audit web pages for WCAG 2.1 AA compliance.
context: fork
agent: accessibility-audit
allowed-tools: Bash, Read, Grep, Glob
---
```
