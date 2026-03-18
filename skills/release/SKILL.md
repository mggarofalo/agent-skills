---
name: release
description: >
  Automate the develop-to-main release workflow: pre-flight checks (CI green,
  no open PRs targeting develop, commits to release), create a conventional-commit
  PR, wait for CI, merge, and monitor the release-please pipeline. Use when the
  user says "release", "release develop to main", "cut a release", or similar.
user_invocable: true
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

## YOU MUST EXECUTE ALL STEPS BELOW

This is a **checklist you must execute**, not documentation. You are responsible for every step. After completing each step, move to the next one. If you stop early, the task is incomplete.

After exiting plan mode or after any context compaction, re-read this file (`~/.claude/skills/release/SKILL.md`) to get the full checklist back in context.

## Execution Modes

This skill supports two modes. Detect which mode you are in **before starting Step 1**.

**Interactive mode** (default): You are running in a direct conversation with the user. Ask for confirmation before merging and report status at each milestone.

**Autonomous mode**: You are running as a subagent, or the invoking prompt contains "autonomous", "plan approved", or "headless". In this mode:
- Do NOT use `EnterPlanMode` or `AskUserQuestion` — these block and you cannot receive interactive responses.
- Stop after Step 5 (PR created and CI passing). Do NOT merge — return the PR URL so the parent/user can review.

---

## Step 1: Pre-flight checks

Run all of these checks. If any fail, **stop and report** — do not proceed.

### 1a. Fetch latest state

```bash
git fetch origin
```

### 1b. Check for unreleased commits

```bash
git log --oneline origin/main..origin/develop
```

If there are **no commits**, stop and report: "Nothing to release — develop is even with main."

### 1c. Check for open PRs targeting develop

```bash
gh pr list --base develop --state open --json number,title,url
```

If there are open PRs, **stop and report** them. These should be merged or closed before releasing.

- **Interactive:** Ask the user if they want to proceed anyway.
- **Autonomous:** Stop. Open PRs targeting develop are a blocker.

### 1d. Verify CI is green on develop

```bash
gh run list --branch develop --limit 1 --json status,conclusion,name
```

The most recent CI run on `develop` must have `conclusion: "success"`. If it failed or is still running:

- **Interactive:** Report the status and ask the user if they want to wait or proceed.
- **Autonomous:** Stop. CI must be green.

### 1e. Check for an existing develop-to-main PR

```bash
gh pr list --base main --head develop --state open --json number,title,url
```

If one already exists, **do not create a new one**. Report the existing PR and skip to Step 3 (wait for CI on the existing PR).

## Step 2: Create the release PR

### 2a. Analyze the commits for the PR body

Review the commit log from Step 1b. Group commits by type (feat, fix, test, chore, docs, refactor, etc.) for the PR summary.

### 2b. Determine the PR title

Use the conventional commit format: `chore: release develop to main`

### 2c. Create the PR

```bash
gh pr create --base main --head develop --title "chore: release develop to main" --body "$(cat <<'EOF'
## Summary
<grouped bullet points by commit type, e.g.:>
<- **Features:** ...>
<- **Fixes:** ...>
<- **Tests:** ...>
<- **Chores:** ...>
<- **Docs:** ...>

## Release pipeline
After merge, the following happens automatically:
1. release-please opens (or updates) a Release PR with version bump and changelog
2. Release PR auto-merges
3. GitHub Release is created with a git tag
4. Docker images are built and published to GHCR
5. sync-develop workflow creates a PR to sync main back into develop

## Test plan
- [ ] CI passes on this PR
- [ ] release-please creates the Release PR after merge
EOF
)"
```

Report the PR URL.

**You are not done. Continue to Step 3.**

## Step 3: Wait for CI

```bash
gh pr checks <PR-NUMBER> --watch
```

- **If CI passes:** Continue to Step 4.
- **If CI fails:** Review the failure:
  ```bash
  gh pr checks <PR-NUMBER>
  gh run list --branch develop --limit 1 --json databaseId,conclusion
  gh run view <RUN-ID> --log-failed
  ```
  - **Interactive:** Report the failure details and ask the user how to proceed.
  - **Autonomous:** Stop and report the failure. Do not attempt to fix CI on the release PR.

**You are not done. Continue to Step 4.**

## Step 4: Merge the release PR

- **Interactive:** Ask the user for confirmation before merging.
- **Autonomous:** Stop here. Return the PR URL and status. Do NOT merge.

Once confirmed (interactive only):

```bash
gh pr merge <PR-NUMBER> --merge
```

Use `--merge` (not `--squash`) to preserve the individual commit history on main — release-please parses individual conventional commits to generate the changelog.

Report the merge result.

**You are not done. Continue to Step 5.**

## Step 5: Monitor the release pipeline

After the merge, the release-please workflow runs automatically. Monitor it:

### 5a. Wait for release-please to run

```bash
gh run list --branch main --workflow release-please.yml --limit 1 --json status,conclusion,databaseId,url
```

If status is not `completed`, wait briefly and re-check (up to 3 minutes, checking every 30 seconds).

### 5b. Check for the Release PR

```bash
gh pr list --label "autorelease: pending" --state open --json number,title,url
```

If a Release PR exists, report it. The Release PR auto-merges via the workflow, so no manual action is needed.

### 5c. Check for the sync-develop PR

```bash
gh pr list --base develop --head main --state open --json number,title,url
```

If a sync PR was created, report it.

### 5d. Report final status

Output a summary:

```
## Release Summary

| Step | Status |
|------|--------|
| Pre-flight checks | pass |
| Release PR | <URL> |
| CI | pass |
| Merge | merged |
| Release-please | <running/completed/Release PR URL> |
| Sync-develop PR | <URL or "pending"> |

### Commits released
<commit list from Step 1b>

### Expected version bump
<Based on commit types: feat → minor, fix → patch, breaking → major>
```

**You are done.**

---

## Rules

- **Never force-push** — this skill does not modify any branches.
- **Use `--merge` not `--squash`** — release-please needs individual conventional commits to generate the changelog correctly.
- **Do not proceed past blockers** — if pre-flight checks fail, stop and report.
- **No compound Bash commands** — no `&&`, `||`, `;` in a single Bash call (hook constraint). Use separate sequential calls.
- **Do not create the PR if one already exists** — pick up the existing one.

## When to Use

- User says "release", "release develop to main", "cut a release", "are we ready to release?" (and confirms)
- User wants to ship what's on `develop` to `main`
- A parent agent needs to trigger a release after aggregating work on `develop`

## When NOT to Use

- User wants to release a hotfix (hotfix branches go directly to main, not through develop)
- User wants to manually cherry-pick commits to main
- User is asking about the release process without wanting to execute it
- There is nothing new on `develop` to release

## Edge Cases Handled

- **Nothing to release** — Step 1b detects no delta and short-circuits
- **Open PRs targeting develop** — Step 1c blocks (or asks in interactive mode)
- **CI failing on develop** — Step 1d blocks before creating the PR
- **Release PR already exists** — Step 1e skips PR creation, jumps to CI monitoring
- **CI fails on the release PR** — Step 3 reports failure details
- **release-please hasn't run yet** — Step 5a polls briefly before reporting

## Orchestration (Parallel / Subagent Execution)

A parent agent can invoke this skill to release after completing a batch of work.

### How to invoke from a parent agent

```
Task tool:
  subagent_type: general-purpose
  model: opus
  prompt: |
    You are running in autonomous mode.
    Use the /release skill to create a release PR from develop to main.
    Do not merge — return the PR URL and CI status.
```

### Permission prerequisites

The project's `.claude/settings.local.json` must auto-allow:

- `Bash(gh:*)` — for GitHub CLI operations
- `Bash(git fetch:*)` — for fetching latest state

### Constraints

- Only one release PR should exist at a time. The skill checks for this.
- The skill does not modify any source code — it only creates and merges PRs.
