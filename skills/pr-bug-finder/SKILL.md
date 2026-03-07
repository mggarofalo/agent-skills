---
name: pr-bug-finder
description: >
  This skill should be used when the user asks to "review a PR for bugs",
  "find bugs in this PR", "analyze PR for defects", "bug hunt this PR",
  or when performing a comprehensive PR review that would benefit from
  adversarial bug analysis. Runs a three-agent adversarial pipeline:
  Bug Hunter, Bug Challenger, and Synthesizer.
---

## What This Tool Does

The PR bug-finder runs an adversarial analysis pipeline with three sequential agents:

1. **Bug Hunter** — Analyzes the diff and surrounding codebase to find real bugs. Scored on finding genuine issues (penalized for false positives).
2. **Bug Challenger** — Independently verifies each reported bug against the actual code. Can confirm, reject (false positive), or mark as follow-up (real issue but pre-existing/out of scope).
3. **Synthesizer** — Combines both outputs into a structured markdown report.

The pipeline is orchestrated from Python — each step must complete before the next starts, guaranteeing a report is always produced.

## How to Invoke

For a GitHub PR:
```bash
env -u CLAUDECODE python ~/.claude/agents/pr-bug-finder/main.py <pr-url> --cwd $(pwd)
```

For a local diff file:
```bash
env -u CLAUDECODE python ~/.claude/agents/pr-bug-finder/main.py --diff <path> --cwd $(pwd)
```

From stdin:
```bash
git diff main...HEAD | env -u CLAUDECODE python ~/.claude/agents/pr-bug-finder/main.py --diff - --cwd $(pwd)
```

Options:
- `--cwd DIR` — Set working directory for codebase context (default: current directory)
- `--max-budget USD` — Set maximum cost cap (default: $2.00)
- `--output-dir DIR` — Directory for output files (default: auto-created in /tmp)

Progress streams to stderr with timestamps. The command prints the report file path to stdout.

## Reading the Output

The command writes output files incrementally and prints the report path to stdout. Use the `Read` tool to read the report file.

If you pass `--output-dir`, you can monitor progress by reading intermediate files as they appear:
- `hunter.md` — Written after the Bug Hunter completes (step 1 of 3)
- `challenger.md` — Written after the Bug Challenger completes (step 2 of 3)
- `report.md` — Written after the Synthesizer completes (step 3 of 3)

## How to Interpret the Report

The report contains:
- **Confirmed Bugs** — Real bugs in code changed by the PR, verified by the challenger. High-confidence findings that should be addressed before merge.
- **Follow-Up Recommendations** — Real issues the challenger verified as genuine but pre-existing or out of scope. Should be filed as separate defect reports, not block this PR.
- **Rejected Findings** — Issues the challenger determined were false positives with concrete reasoning.
- **Statistics** — Counts for confirmed, follow-up, rejected, and severity breakdown.

## What to Do with the Results

After reading the report file, present the full markdown report to the user. Then follow the full workflow below.

### Phase 1: Present Findings

Summarize the report to the user. Highlight confirmed bugs by severity (critical/high first). Briefly mention follow-ups and rejections.

### Phase 2: File Follow-Up Issues

If there are **follow-up recommendations** (real issues that are pre-existing or out of scope for this PR), file them as Linear issues before moving on to remediation.

For each follow-up, ask the user which team/project to file under (or use a sensible default if the user has established a preference). Use the MCP linear tool if available, or ask the user how they'd like the issue filed. Include the bug ID, description, location, and challenger's reasoning in the issue body.

If the user declines to file any or all follow-ups, skip them.

### Phase 3: Remediation Plan

If there are **confirmed bugs**, enter plan mode to design a remediation:

1. For each confirmed bug, plan the specific code fix based on the report's location, justification, and suggested fix.
2. The plan must include:
   - The fix for each confirmed bug
   - Running all pre-commit hooks and ensuring they pass
   - Committing the changes (one commit for all bug fixes, or one per bug if they're independent — use judgement)
   - Pushing to the correct PR branch (verify with `git branch --show-current` and `gh pr view --json headRefName -q .headRefName` that you're on the right branch before pushing)
   - Waiting for CI to complete

After the user approves the plan, implement the fixes.

### Phase 4: Commit and Push

1. Fix each confirmed bug.
2. Run pre-commit hooks. If they fail, fix the issues and retry until they pass.
3. Commit the changes.
4. Verify you are on the PR branch:
   ```bash
   CURRENT=$(git branch --show-current)
   EXPECTED=$(gh pr view --json headRefName -q .headRefName)
   ```
   If `$CURRENT` != `$EXPECTED`, do NOT push. Alert the user.
5. Push to the PR branch: `git push`

### Phase 5: CI Results

After pushing, monitor CI:

```bash
gh pr checks --watch
```

**If CI passes:** Ask the user if they're ready to merge. If yes, merge with `gh pr merge --squash` (or the repo's preferred merge method).

**If CI fails:**
1. Review the CI failure output: `gh pr checks` to identify which checks failed, then `gh run view <run-id> --log-failed` for details.
2. Diagnose and fix the failures autonomously.
3. Run pre-commit hooks, commit, verify branch, and push again.
4. If you are unsure about a fix or the failure is ambiguous, ask the user before proceeding. Do not guess at fixes for failures you don't understand.
5. Repeat until CI passes, then ask the user about merging.

## When to Use

- Thorough bug analysis of a PR before merge
- When the user specifically asks to find bugs or defects
- Complex PRs with non-trivial logic changes

## When NOT to Use

- Style, formatting, or documentation reviews (use standard PR review)
- Simple typo fixes or dependency bumps
- When the user just wants a quick review, not deep bug analysis
