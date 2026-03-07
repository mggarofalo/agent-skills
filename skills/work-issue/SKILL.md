---
name: work-issue
description: >
  This skill should be used when the user says "work <issue>", "pick up <issue>",
  "implement <issue>", "do <issue>", or any variation where they hand you a Linear
  issue (by ID, URL, or description) and expect end-to-end implementation through
  to merge. Covers the full lifecycle: read issue, branch, plan, implement, commit,
  push, open PR, run adversarial bug analysis, remediate, and merge.
---

## YOU MUST EXECUTE ALL STEPS BELOW

This is a **checklist you must execute**, not documentation. You are responsible for every step. After completing each step, move to the next one. You are NOT done until the PR is merged. If you stop early, the task is incomplete.

After exiting plan mode or after any context compaction, re-read this file (`~/.claude/skills/work-issue/SKILL.md`) to get the full checklist back in context.

---

## Step 1: Read the issue

Use the MCP linear tool to read the issue. Extract the title, description, acceptance criteria, labels, and priority. Summarize it to the user in 2-3 sentences. If anything is ambiguous, ask before proceeding.

## Step 2: Create a branch

```bash
git checkout main && git pull
git checkout -b <prefix>/<issue-id>-short-description
```

Prefixes (conventional commit style): `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`, `perf/`, `ci/`

Examples: `feat/ENG-123-user-validation`, `fix/ENG-456-null-pointer-on-login`

## Step 3: Plan

Enter plan mode. Your plan must include:

1. The code changes (files, approach, edge cases, tests)
2. ALL the remaining steps from this checklist (steps 4-10)
3. An instruction to re-read `~/.claude/skills/work-issue/SKILL.md` after plan approval

Present the plan to the user for approval.

## Step 4: Re-read this file

After the user approves the plan, re-read `~/.claude/skills/work-issue/SKILL.md` before doing anything else. Context may have been compacted and you may have lost the remaining steps.

## Step 5: Implement

1. Implement the code changes from the plan.
2. Write or update tests as appropriate.
3. Run the test suite to verify nothing is broken.
4. Run pre-commit hooks and fix any issues until they pass.

**You are not done. Continue to step 6.**

## Step 6: Commit and push

1. Stage and commit with a message referencing the issue ID.
2. Push the branch: `git push -u origin HEAD`

**You are not done. Continue to step 7.**

## Step 7: Open a PR

```bash
gh pr create --title "<concise title>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points describing what changed and why>

Resolves <LINEAR-ISSUE-ID>

## Test plan
<How to verify the changes work>

EOF
)"
```

**You are not done. Continue to step 8.**

## Step 8: Run bug analysis

Invoke `/find-bugs` on the PR you just created. Wait for the analysis to complete. Read the report file.

**You are not done. Continue to step 9.**

## Step 9: Triage bug analysis results

**If there are follow-up recommendations:** File Linear issues for each using the MCP linear tool. Ask the user which team/project if not obvious.

**If there are confirmed bugs:** Plan remediation for each bug (you may enter plan mode again). After user approval, fix them, run pre-commit hooks until they pass, commit, and push.

**If no confirmed bugs and no follow-ups:** Continue to step 10.

**You are not done. Continue to step 10.**

## Step 10: Wait for CI and merge

1. Run `gh pr checks --watch` to wait for CI.
2. **If CI passes:** Ask the user if they're ready to merge. If yes: `gh pr merge --squash`
3. **If CI fails:** Review with `gh pr checks` and `gh run view <run-id> --log-failed`. Fix autonomously if you can; ask the user if you're unsure. Commit, push, repeat until CI passes.
4. After merge, update the Linear issue status if the MCP linear tool supports it.

**You are done.**

---

## Rules

- **Never force-push** unless the user explicitly asks.
- **Verify the branch** before every push — `git branch --show-current` must match the branch you created.
- **Pre-commit hooks must pass** before every commit. Fix issues, don't skip hooks.
- If any step fails in a way you can't recover from, stop and explain to the user.

## When to Use

- User says "work <issue>", "pick up <issue>", "implement <issue>", "do <issue>"
- User provides a Linear issue ID, URL, or title and expects full implementation

## When NOT to Use

- User just wants to discuss an issue without implementing it
- User wants a code review on existing work (use pr-bug-finder instead)
- User is mid-implementation and just needs help with a specific part
