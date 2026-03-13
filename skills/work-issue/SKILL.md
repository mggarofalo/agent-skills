---
name: work-issue
description: >
  This skill should be used when the user says "work <issue>", "pick up <issue>",
  "implement <issue>", "do <issue>", or any variation where they hand you a Plane
  issue (by ID, URL, or description) and expect end-to-end implementation through
  to merge. Covers the full lifecycle: read issue, branch, plan, implement, commit,
  push, open PR, run adversarial bug analysis, remediate, and merge.
---

## YOU MUST EXECUTE ALL STEPS BELOW

This is a **checklist you must execute**, not documentation. You are responsible for every step. After completing each step, move to the next one. If you stop early, the task is incomplete.

After exiting plan mode or after any context compaction, re-read this file (`~/.claude/skills/work-issue/SKILL.md`) to get the full checklist back in context.

## Execution Modes

This skill supports two modes. Detect which mode you are in **before starting Step 1**.

**Interactive mode** (default): You are running in a direct conversation with the user. Use plan mode, ask clarifying questions, and request merge approval as described below.

**Autonomous mode**: You are running as a subagent, or the invoking prompt contains "autonomous", "plan approved", or "headless". In this mode:
- Do NOT use `EnterPlanMode` or `AskUserQuestion` — these block and you cannot receive interactive responses.
- Plan inline instead of entering plan mode.
- Make reasonable assumptions instead of asking questions; document assumptions in the PR description.
- Stop after Step 9 (bug analysis + triage). Do NOT merge — return the PR URL so the parent/user can review.

**Base branch override**: The invoking prompt may specify a target branch other than `main` (e.g., `develop`, `release/1.0`). When a base branch is specified:
- **Step 2**: Branch from the specified base instead of `main`. If already on an issue branch based on the target, skip branch creation as usual.
- **Step 7**: Use `gh pr create --base <target-branch>` to target the specified branch.
- This is common in batch processing where multiple issues aggregate into a single release branch.

---

## Step 1: Read the issue

Fetch the issue:

```bash
python ~/.claude/scripts/plane-get-issue.py <ISSUE-ID>
```

Save the UUID from the output for later update/comment commands. Extract the title, description, acceptance criteria, labels, and priority. Summarize it in 2-3 sentences.

- **Interactive:** If anything is ambiguous, ask before proceeding.
- **Autonomous:** If anything is ambiguous, make a reasonable assumption and note it. Continue.

## Step 2: Verify or create a branch

Check the current branch:

```bash
git branch --show-current
```

- **Already on an issue branch** (e.g. the launcher created it via `claude -w`): skip branch creation, proceed to Step 3.
- **On `main` or a non-issue branch** (user ran `/work-issue` directly): create the branch with the standard naming convention:

```bash
git checkout main && git pull
git checkout -b <prefix>/<issue-id-lower>-<slugified-title>
```

Naming rules: lowercase issue ID, slugified title (non-alphanumeric → hyphens, max ~5 words).

Prefixes (conventional commit style): `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`, `perf/`, `ci/`

Examples: `feat/mgg-54-docker-compose-configuration`, `fix/eng-456-null-pointer-on-login`

## Step 3: Plan

Your plan must include:

1. The code changes (files, approach, edge cases, tests)
2. ALL the remaining steps from this checklist (steps 4-10)
3. An instruction to re-read `~/.claude/skills/work-issue/SKILL.md` after plan approval

- **Interactive:** Enter plan mode. Present the plan to the user for approval.
- **Autonomous:** Write the plan inline (do NOT call `EnterPlanMode`). Proceed immediately to Step 4.

## Step 4: Re-read this file

Re-read `~/.claude/skills/work-issue/SKILL.md` before doing anything else. Context may have been compacted and you may have lost the remaining steps.

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

Resolves <ISSUE-ID>

## Test plan
<How to verify the changes work>

EOF
)"
```

**You are not done. Continue to step 8.**

## Step 8: Run bug analysis and React render-cycle QA

Run these analyses **in parallel** — they are independent:

1. **Bug analysis**: Invoke `/find-bugs` on the PR you just created.
2. **React render-cycle QA** (conditional): Check whether the diff contains React files (`*.tsx`, `*.jsx` under `src/client/`). If yes, launch the `react-render-qa` agent via the Task tool:

```
Task tool:
  subagent_type: react-render-qa
  prompt: |
    Analyze the PR on the current branch for React render-cycle bugs.
    Run `gh pr diff` to get the diff, then follow your analysis workflow.
```

If no React files are in the diff, skip the React QA.

Wait for both analyses to complete. Read the report files.

**You are not done. Continue to step 9.**

## Step 9: Triage analysis results

Triage results from **both** bug analysis and React render-cycle QA (if it ran).

**React render-cycle QA findings:**
- **CRITICAL or HIGH findings:** These are bugs. Fix them before merging — same as confirmed bugs below.
- **MEDIUM findings:** File Plane issues for each (same as follow-up recommendations below):
  ```bash
  python ~/.claude/scripts/plane-create-issue.py --name "<title>" --description "<markdown description>" --priority medium
  ```

**Bug analysis findings:**

**If there are follow-up recommendations:** File Plane issues for each:
```bash
python ~/.claude/scripts/plane-create-issue.py --name "<title>" --description "<markdown description>" --priority medium
```
- **Interactive:** Ask the user which team/project if not obvious.
- **Autonomous:** Use the same team and project as the source issue.

**If there are confirmed bugs:** Fix them, run pre-commit hooks until they pass, commit, and push.
- **Interactive:** You may enter plan mode to plan remediation.
- **Autonomous:** Plan remediation inline and proceed directly to the fix.

**If no confirmed bugs and no follow-ups from either analysis:** Continue to step 10.

- **Autonomous:** You are done. Return the PR URL and a summary of what was implemented, any assumptions made, and any follow-up issues filed. Do NOT proceed to Step 10.

**You are not done. Continue to step 10.**

## Step 10: Wait for CI and merge

> **Autonomous mode stops after Step 9.** This step is interactive-only.

1. Run `gh pr checks --watch` to wait for CI.
2. **If CI passes:** Ask the user if they're ready to merge. If yes: `gh pr merge --squash`
3. **If CI fails:** Review with `gh pr checks` and `gh run view <run-id> --log-failed`. Fix autonomously if you can; ask the user if you're unsure. Commit, push, repeat until CI passes.
4. After merge, update the Plane issue status:
   ```bash
   python ~/.claude/scripts/plane-update-state.py <UUID> "Done"
   ```

**You are done.**

---

## Rules

- **Never force-push** unless the user explicitly asks.
- **Verify the branch** before every push — `git branch --show-current` must match the branch you created.
- **Pre-commit hooks must pass** before every commit. Fix issues, don't skip hooks.
- If any step fails in a way you can't recover from, stop and explain to the user (interactive) or return a clear error summary (autonomous).

## When to Use

- User says "work <issue>", "pick up <issue>", "implement <issue>", "do <issue>"
- User provides a Plane issue ID, URL, or title and expects full implementation

## When NOT to Use

- User just wants to discuss an issue without implementing it
- User wants a code review on existing work (use pr-bug-finder instead)
- User is mid-implementation and just needs help with a specific part

## Orchestration (Parallel / Subagent Execution)

A parent agent can spawn multiple work-issue agents in parallel to work on independent issues concurrently. Each agent runs in an isolated worktree so there are no file conflicts.

### Launcher script

The launcher (`~/.claude/skills/work-issue/launch.py`) builds a deterministic branch name and starts Claude Code in a worktree. It keeps naming logic in one testable place.

**Interactive use:**
```bash
python ~/.claude/skills/work-issue/launch.py --type feat --issue MGG-54 --title "Docker Compose Configuration"
```

**Autonomous use:**
```bash
python ~/.claude/skills/work-issue/launch.py --type feat --issue MGG-54 --title "Docker Compose Configuration" --prompt "/work-issue MGG-54"
```

**Dry run** (print branch name and exit):
```bash
python ~/.claude/skills/work-issue/launch.py --type feat --issue MGG-54 --title "Docker Compose Configuration" --dry-run
# → feat/mgg-54-docker-compose-configuration
```

### How to invoke without the launcher

```
Task tool:
  subagent_type: general-purpose
  model: opus
  isolation: worktree
  run_in_background: true
  prompt: |
    You are running in autonomous mode. Use the /work-issue skill to implement <ISSUE-ID>.
    Execute the full lifecycle through bug analysis (Steps 1-9). Do not merge.
```

### Prerequisites

### Permission prerequisites

The project's `.claude/settings.local.json` must auto-allow these permissions — background agents cannot prompt for interactive grants:

- `Edit` and `Write` — for modifying source files
- `Bash(git push:*)` — for pushing branches to remote
- `Bash(npm install:*)` — if the project has JS/TS dependencies

Worktree isolation provides the safety boundary — agents can only modify their isolated copy of the repo.

### Worktree initialization

Projects with frontend dependencies should configure a `WorktreeCreate` hook in `.claude/settings.json` to run dependency installation automatically. Without this, worktrees lack `node_modules` and agents cannot run pre-commit hooks or frontend tests. See Claude Code docs on [hooks](https://code.claude.com/docs/en/hooks) for the `WorktreeCreate` event.

### What the parent agent should do

1. **Spawn** one agent per issue, all in parallel with `isolation: "worktree"`.
2. **Wait** for agents to complete. Each returns a PR URL and summary.
3. **Review** the PRs (or ask the user to review them).
4. **Merge** approved PRs and update Plane issue status.

### Constraints

- Only parallelize issues that don't touch the same files. If two issues modify the same code, work them sequentially.
- The parent agent should not duplicate work the subagent is doing.
- Each agent handles its own bug analysis and follow-up issue filing.
