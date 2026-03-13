# Phase 6: Product Acceptance

## Purpose

Final quality gate — validate that ALL acceptance criteria from the Plane issue are met by the implementation, tests, and review/security findings. This phase is the last check before the issue is marked as Done.

## Inputs

- The Plane issue (re-fetched for latest description)
- The full state file (all prior phase results)
- The codebase (to verify implementation details)

## Steps

### 1. Re-Fetch the Plane Issue

Fetch the latest issue description (it may have been updated since the pipeline started):

```bash
plane issue get-by-sequence-id --identifier <ISSUE-ID> --expand state,labels,assignees -o json
```

### 2. Parse Acceptance Criteria

Extract acceptance criteria from the issue description. Common formats:
- Markdown checklists: `- [ ] criterion`
- Numbered lists: `1. criterion`
- "Acceptance Criteria" or "Requirements" section headers
- Bullet points under a "Definition of Done" section

If the issue has no clear acceptance criteria, derive them from the issue title and description — what would a reasonable product owner expect to be done?

### 3. Evaluate Each Criterion

For each acceptance criterion, cross-reference against:

#### Implementation Evidence
- Does the code change address this criterion? (Read the relevant files)
- Is the behavior implemented as specified?

#### Test Evidence
- Is there a test that validates this criterion? (From Phase 5 QA report)
- Does the test pass?

#### Review/Security Evidence
- Were there any review or security findings related to this criterion?
- Have they been resolved?

For each criterion, produce a verdict:

```markdown
| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| <text> | PASS | <specific evidence: file, test, or phase reference> |
| <text> | FAIL | <what's missing or incorrect> |
```

### 4. Visual Verification (If Applicable)

Read `~/.claude/skills/sdlc/references/browser-testing.md` for full `agent-browser` usage.

**Determine applicability:** If any acceptance criteria reference UI behavior, visual appearance, user flows, or page content — visual verification applies.

**When applicable:**
1. Start the project's dev server in the background
2. For each UI-related acceptance criterion:
   - Navigate to the relevant page
   - Verify the criterion is met by inspecting the DOM (`agent-browser snapshot -i -c`) or checking rendered content (`agent-browser get text`)
   - Take an annotated screenshot as evidence: `agent-browser screenshot --annotate .sdlc/evidence/accept-<criterion-number>.png`
   - If the criterion involves an interaction (e.g., "user can submit the form"), perform the interaction and verify the result
3. Reference screenshots in the evidence column of the acceptance criteria table
4. Close the browser: `agent-browser close`
5. Stop the dev server

### 5. Determine Overall Result

- **ALL criteria PASS:** Pipeline succeeds
- **ANY criterion FAILS:** Pipeline fails at this phase

### 6. On Pass — Close the Loop

1. **Post a summary comment** on the Plane issue (use `plane comment add -p <PROJECT> --work-item-id <UUID> --comment-html "<html>"`):

```markdown
## SDLC Pipeline Summary

**Issue:** <identifier> — <title>
**Result:** PASS

| Phase | Status | Notes |
|-------|--------|-------|
| Plan | Pass | <1-line summary> |
| Implement | Pass | <N files changed, M commits> |
| Review | Pass | <findings summary> |
| Security | Pass | <threat model summary> |
| QA | Pass | <test summary> |
| Accept | Pass | <N/N criteria met> |

**Branch:** `<branch-name>`
```

2. **Update the issue status** to "Done":
   ```bash
   plane issue update -p <PROJECT> --work-item-id <UUID> --state <done-state-id>
   ```

3. **Clean up the state file:** Delete `.sdlc/<identifier>.md`

4. **Report to user:** Summarize what was done and confirm the issue is closed

### 7. On Fail — Surface Gaps

1. **Do NOT update issue status** — leave it as-is

2. **Report failing criteria** with specifics:
   - What criterion failed
   - What evidence was expected but missing
   - Suggested remediation (new code, new tests, or manual action needed)

3. **Write results to state file:**

```markdown
## Phase 6: Accept
**Status:** fail

### Acceptance Criteria Evaluation
| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| <text> | PASS | <evidence> |
| <text> | FAIL | <what's missing> |

### Unmet Criteria
- <criterion>: <what needs to happen to meet it>

**Summary:** <N/M criteria met. Failing criteria require: <action needed>>
```

4. **Stop the pipeline** — Acceptance failures always require user guidance

## Pass/Fail Criteria

- **Pass:** Every acceptance criterion has a PASS verdict with supporting evidence
- **Fail:** Any acceptance criterion has a FAIL verdict

## Important Notes

- This phase should be thorough but fair — don't fail criteria that are clearly met just because the evidence isn't perfectly documented
- If a criterion is ambiguous, interpret it reasonably in the context of the feature
- Don't introduce new requirements beyond what's in the issue description
- The Plane comment should be a concise summary, not a dump of the full state file
