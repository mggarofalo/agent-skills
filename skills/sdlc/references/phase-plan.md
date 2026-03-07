# Phase 1: Planner

## Purpose

Understand the Linear issue and produce a structured implementation plan. This phase analyzes requirements, explores the codebase, and documents the approach before any code is written.

## Inputs

- Linear issue (already fetched during initialization — available in state file)
- Project context (AGENTS.md, LINEAR.md, CLAUDE.md — summarized in state file header)
- The full codebase

## Steps

### 1. Understand the Requirements

- Read the issue description, acceptance criteria, and any comments from the state file
- If the issue has related/blocking issues, fetch them with `mcp__plugin_linear_linear__get_issue` to understand dependencies
- Identify what the user is actually asking for — separate the "what" from the "how"

### 2. Explore the Codebase

- Use `Glob` and `Grep` to find files relevant to the feature
- Read key files to understand existing patterns, architecture, and conventions
- Identify:
  - Files that need to be **modified** (and which parts)
  - Files that need to be **created**
  - Files that serve as **reference implementations** (similar features already built)
  - Test files that need new test cases

### 3. Produce the Plan

Write a structured plan with these sections:

```markdown
### Summary
<2-3 sentences describing what will be built and why>

### Files to Modify
| File | Change | Rationale |
|------|--------|-----------|
| <path> | <what changes> | <why> |

### Files to Create
| File | Purpose |
|------|---------|
| <path> | <what it does> |

### Approach
<Step-by-step implementation approach. Be specific about patterns to follow,
existing code to reuse, and the order of operations.>

### Design Decisions
- <Decision 1>: <rationale>
- <Decision 2>: <rationale>

### Risks & Edge Cases
- <Risk/edge case 1>: <mitigation>
- <Risk/edge case 2>: <mitigation>

### Dependencies
- <Any blocking issues, external services, or prerequisites>
```

### 4. Write to State File

Append the plan to the state file under `## Phase 1: Plan`:

```markdown
## Phase 1: Plan
**Status:** pass
**Output:**
<the structured plan from step 3>
```

### 5. Update Linear Issue

- Update the issue status to "In Progress" using `mcp__plugin_linear_linear__update_issue`

## Pass/Fail Criteria

This phase always passes — it produces a plan. If the issue lacks sufficient detail to plan, use `AskUserQuestion` to clarify requirements before producing the plan.

## Output

The structured plan written to the state file. This is the primary input for the Implement phase.
