# Phase 5: QA

## Purpose

Write tests, run the test suite, and validate the implementation against the issue's acceptance criteria. This phase ensures the feature works correctly and has adequate test coverage.

## Inputs

- The plan from Phase 1 (what was intended)
- Implementation details from Phase 2 (what was built)
- Review and security findings from Phases 3-4 (any edge cases surfaced)
- Acceptance criteria from the issue (in state file header)
- Project test conventions (from AGENTS.md / state file header)

## Steps

### 1. Analyze Test Coverage Gaps

- Read the implementation details from the state file to know which files changed
- Find existing test files for the changed code:
  - Use conventions from AGENTS.md (test file location, naming patterns)
  - Common patterns: `*.test.ts`, `*.spec.ts`, `*Tests.cs`, `test_*.py`, `*_test.go`
- Read existing tests to understand the testing patterns used in this project
- Identify what's NOT tested:
  - New public methods/functions without tests
  - New edge cases introduced by the changes
  - Error handling paths
  - Integration points

### 2. Write Tests

For each coverage gap, write tests following the project's existing patterns:

#### Test Categories
- **Unit tests:** Test individual functions/methods in isolation
  - Happy path (expected inputs → expected outputs)
  - Edge cases (empty, null, boundary values)
  - Error cases (invalid inputs, failure modes)
- **Integration tests:** Test components working together
  - API endpoint tests (if applicable)
  - Database interaction tests (if applicable)
  - Service-to-service tests (if applicable)

#### Test Writing Principles
- Follow the Arrange-Act-Assert (AAA) pattern
- Use descriptive test names that explain the scenario
- Match the project's existing test style exactly
- Don't test implementation details — test behavior
- Don't test framework/library code — test YOUR code
- Use existing test helpers, fixtures, and utilities from the project

### 3. Run the Test Suite

- Run the project's test command (from AGENTS.md or detected):
  - .NET: `dotnet test`
  - Node: `npm test` or `yarn test`
  - Python: `pytest`
  - Swift: `swift test`
  - Go: `go test ./...`
- Capture test output including:
  - Total tests run / passed / failed / skipped
  - Names of any failing tests
  - Error messages and stack traces for failures

### 4. Handle Test Failures

If tests fail, triage each failure:

#### Test Bug (test is wrong)
- The test has incorrect expectations
- The test doesn't account for intentional behavior changes
- **Action:** Fix the test and re-run

#### Code Bug (code is wrong)
- The test correctly identifies a bug in the implementation
- **Action:** Report as a failure — the orchestrator will route to Implementer

To distinguish: read both the test and the code carefully. If the test expectation matches the plan's intended behavior and the acceptance criteria, the code is likely wrong. If the test expectation contradicts the plan, the test is likely wrong.

### 5. Browser Testing (If Applicable)

Read `~/.claude/skills/sdlc/references/browser-testing.md` for full `agent-browser` usage.

**Determine applicability:** Check if the feature involves user-facing UI by looking at the files changed in Phase 2. If changes touch templates, components, views, pages, stylesheets, or client-side code — browser testing applies. If changes are purely backend, library, or CLI — skip this step.

**When applicable:**
1. Start the project's dev server in the background (command from AGENTS.md or state file)
2. Wait for the server to be ready
3. Navigate to the page(s) affected by the feature
4. Run the following checks:
   - **Render check:** Does the page load without errors? (`agent-browser snapshot -i -c` to verify DOM state)
   - **Interaction check:** Do the new/modified interactive elements work? (Fill forms, click buttons, verify results)
   - **Acceptance criteria check:** For each UI-related acceptance criterion, verify it visually in the browser
   - **Error state check:** Trigger error conditions and verify error messages render correctly
5. Take screenshots as evidence and save to `.sdlc/evidence/` directory
6. Record results in the QA report under a `### Browser Testing` section
7. Close the browser session: `agent-browser close`
8. Stop the dev server

**Browser test failures** count as test failures for pass/fail evaluation.

### 6. Validate Against Acceptance Criteria

For each acceptance criterion from the issue:
- Identify which tests cover this criterion
- If no tests cover it, write one
- Map: criterion → test(s) → pass/fail

### 7. Commit Tests

- Stage only test files
- Commit with message: `test(<scope>): add tests for <feature>`
- Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

### 8. Write QA Report

Append to state file:

```markdown
## Phase 5: QA
**Status:** pass (or fail)

### Test Coverage
**Tests Written:** <N new tests>
**Test Files:**
- <file1> — <what it tests>
- <file2> — <what it tests>

### Test Results
**Total:** <N> | **Passed:** <N> | **Failed:** <N> | **Skipped:** <N>

### Failing Tests (if any)
- `<test name>`: <error summary>
  - **Triage:** test bug / code bug
  - **Details:** <explanation>

### Browser Testing
**Applicable:** yes/no
**Dev Server:** <command used>
**Pages Tested:** <list of URLs>
**Results:**
- <page/flow>: pass/fail — <notes>
**Screenshots:** <list of screenshot paths in .sdlc/evidence/>

### Acceptance Criteria Coverage
| Criterion | Test(s) | Status |
|-----------|---------|--------|
| <criterion 1> | <test name(s)> | Pass/Fail |
| <criterion 2> | <test name(s)> | Pass/Fail |

**Commits:**
- `<hash>`: <commit message>

**Summary:** <1-2 sentence QA assessment>
```

## Pass/Fail Criteria

- **Pass:** All tests pass AND all acceptance criteria have test coverage
- **Fail:** Any test fails (after triaging test bugs) OR acceptance criteria lack coverage

## On Failure

When this phase fails:
- If the failure is a **code bug:** report the failing test name, expected vs actual behavior, and the file/line of the likely code issue. The orchestrator routes to Implementer.
- If the failure is a **test bug:** fix the test directly and re-run (no need to route to Implementer).
- If **acceptance criteria lack coverage:** write the missing tests and re-run.
