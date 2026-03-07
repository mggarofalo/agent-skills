# Phase 3: Reviewer

## Purpose

Perform a thorough code review of the implementation. This phase catches logic errors, convention violations, and code quality issues before they reach production.

## Inputs

- The plan from Phase 1 (in state file — to understand intent)
- Implementation details from Phase 2 (branch, files changed)
- Project conventions (from AGENTS.md / state file header)

## Steps

### 1. Gather the Diff

- Read the state file to identify the branch and base
- Run `git diff main...<branch>` (or appropriate base branch from AGENTS.md) to get the full diff
- Also read each changed file in full to understand context around the changes

### 2. Review Checklist

For each changed file, evaluate:

#### Logic & Correctness
- Does the code do what the plan says it should?
- Are there off-by-one errors, null reference risks, or race conditions?
- Are edge cases handled (empty inputs, boundary values, error states)?
- Is the control flow correct (early returns, loop conditions, exception handling)?

#### Convention Adherence
- Does the code follow the project's naming conventions (from AGENTS.md)?
- Does it match the file organization patterns?
- Does it follow the commit message format?
- Are imports/using statements organized per convention?

#### Code Quality
- Is there unnecessary duplication?
- Are names descriptive and consistent with the codebase?
- Is the code readable without excessive comments?
- Are abstractions at the right level (not over/under-engineered)?

#### Performance
- Are there N+1 query patterns?
- Are there unnecessary allocations in hot paths?
- Are there blocking calls where async is expected?
- Are collections sized appropriately?

#### Error Handling
- Are errors handled at system boundaries?
- Are error messages helpful for debugging?
- Are resources properly disposed/cleaned up?

### 3. Confidence-Based Filtering

Only report findings you are **highly confident** about. For each potential finding:
- Can you point to a specific line and explain the exact problem?
- Is this a real issue or a style preference?
- Would a senior engineer on this project agree this is a problem?

If you're not confident, don't report it.

### 4. Categorize Findings

- **CRITICAL:** Must fix before merge. Bugs, data loss risks, security issues, broken functionality.
- **WARNING:** Should fix. Convention violations, performance concerns, maintainability issues.
- **INFO:** Optional improvements. Style suggestions, minor refactoring opportunities.

### 5. Write Review Report

Append to state file:

```markdown
## Phase 3: Review
**Status:** pass (or fail)
**Findings:**

### CRITICAL
- [<file>:<line>] <description of the issue and why it's critical>

### WARNING
- [<file>:<line>] <description>

### INFO
- [<file>:<line>] <description>

**Summary:** <1-2 sentence overall assessment>
```

## Pass/Fail Criteria

- **Pass:** No CRITICAL findings
- **Fail:** One or more CRITICAL findings exist

## On Failure

When this phase fails, the orchestrator will:
1. Extract the CRITICAL findings from the state file
2. Route them to the Implementer phase for remediation
3. The Implementer will fix the specific issues
4. This Review phase will re-run to verify the fixes

The re-run should:
- Re-evaluate the full diff (including fixes)
- Verify each previous CRITICAL finding is addressed
- Check that fixes didn't introduce new issues
- Append the re-review results to the state file (don't overwrite the original review)
