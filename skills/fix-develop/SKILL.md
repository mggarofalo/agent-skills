---
name: fix-develop
description: >
  Codifies the "never fix incidental breakage in a feature PR" workflow.
  Stash in-progress work, branch from develop, land a minimal fix, rebase
  the original branch, and resume. Invokable from within work-issue/sdlc
  agents when they detect pre-existing breakage.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
user_invocable: true
argument: "[issue-id-or-description] — optional context for the breakage being fixed"
---

# fix-develop

**Purpose:** When a feature-branch agent encounters pre-existing build/test/lint breakage that is unrelated to its assigned scope, route the fix through a separate PR off `develop` (or `main` if no `develop` exists) instead of mixing it into the feature PR. This prevents collateral merge damage from parallel agents fixing the same breakage differently.

## YOU MUST EXECUTE ALL STEPS BELOW

This is a **checklist you must execute**, not documentation. Every step has a side effect — none can be skipped. If you stop early, the invoking agent is left in a broken state.

## When to Use

- A work-issue or sdlc agent encountered a failing build, failing test, or lint error on its feature branch that is clearly **not** introduced by its own changes and **not** within its assigned scope.
- The user explicitly invokes `/fix-develop` with a breakage description.
- Any other scenario where a minimal fix belongs on `develop` rather than inside a feature PR.

## When NOT to Use

- The breakage was introduced by your own in-progress work (fix it in-branch).
- The fix is one line and typo-level (< 30 seconds): land it in the current feature branch as a separate commit labeled `fix: incidental ...`.
- The breakage is actually part of the assigned scope.

---

## Argument Parsing

The argument (if any) is freeform context — an issue ID (e.g., `RECEIPTS-599`), a short description of the breakage (`"pre-commit failing on trailing whitespace in AGENTS.md"`), or empty.

- If an issue ID is provided, use it for branch naming and commit message scope.
- If a description is provided, slugify it for the branch name.
- If nothing is provided, ask the invoker for a short description (or infer one from recent command output if running autonomously).

---

## Step 1: Record original state

Capture everything needed to resume the invoking agent's work cleanly.

1. Record the current branch: `git branch --show-current`. Save as `ORIGINAL_BRANCH`.
2. Record the current commit SHA: `git rev-parse HEAD`. Save as `ORIGINAL_SHA`.
3. Detect the base branch of the repo:
   - If `git show-ref --verify --quiet refs/heads/develop` or `git show-ref --verify --quiet refs/remotes/origin/develop` — base is `develop`.
   - Otherwise — base is `main`.
   Save as `BASE_BRANCH`.
4. Run `git status --porcelain` to see whether there is any in-progress work.

If `ORIGINAL_BRANCH` equals `BASE_BRANCH`, you are **not** inside a feature branch — abort and tell the invoker that `/fix-develop` is only for use from inside a feature branch.

## Step 2: Stash any in-progress work

If `git status --porcelain` showed any modified, staged, or untracked files:

```bash
git stash push --include-untracked -m "fix-develop: auto-stash from <ORIGINAL_BRANCH> at <ORIGINAL_SHA>"
```

Record whether you stashed (`DID_STASH=true|false`). If `DID_STASH=false`, skip the stash-pop in Step 10.

Do **not** use `git stash -k` — the fix branch must start from a clean working tree.

## Step 3: Check out base and pull

```bash
git checkout <BASE_BRANCH>
git pull --ff-only origin <BASE_BRANCH>
```

If the pull fails (divergent history, conflict): stop, restore `ORIGINAL_BRANCH`, pop the stash, and surface the error. Do not force anything.

## Step 4: Create the fix branch

Build a short slug from the argument (max ~5 words, lowercased, non-alphanumeric → hyphens):

```bash
git checkout -b fix/incidental-<slug>
```

If no argument was provided, use `fix/incidental-develop-<ORIGINAL_SHA-short>`.

## Step 5: Implement the minimal fix

1. Reproduce the breakage locally (re-run the failing command: pre-commit, the failing test, the failing build step).
2. Identify the **smallest** change that unbreaks it. Do not refactor. Do not tidy adjacent code. Do not fix other issues you notice.
3. Make the change.
4. Re-run the previously-failing command and verify it passes.

**Scope discipline:** if you find yourself touching more than one or two files, stop and ask whether this really belongs in a single `/fix-develop` PR or should be a tracked issue instead.

## Step 6: Run pre-commit hooks

```bash
pre-commit run --files <changed-files>
```

Fix any issues pre-commit surfaces. Do not skip hooks.

If the repo has no pre-commit, run the project's equivalent (e.g., `dotnet format`, `npm run lint`, etc.) as defined in `AGENTS.md` or `CLAUDE.md`.

## Step 7: Commit

Use a conventional-commits message. Scope should match the affected area:

```bash
git add <changed-files>
git commit -m "fix(<scope>): <short description of the incidental fix>"
```

The commit body should briefly explain **why** this is a standalone fix and not part of a feature PR. Reference the original issue ID if one was provided.

## Step 8: Push and open PR

```bash
git push -u origin HEAD
```

```bash
gh pr create --base <BASE_BRANCH> --title "fix(<scope>): <short description>" --body "$(cat <<'EOF'
## Summary
Incidental fix for pre-existing breakage on `<BASE_BRANCH>`. Split out of <ORIGINAL_BRANCH> so it can land independently and avoid collateral merge damage from parallel feature PRs.

## What was broken
<concise description of the failure>

## Fix
<concise description of the change>

## Test plan
- [ ] Previously failing command now passes
- [ ] Pre-commit hooks pass
EOF
)"
```

Record the PR URL as `FIX_PR_URL`.

## Step 9: Wait for merge (or hand off)

Two modes:

**Interactive mode** (user is watching):
1. Wait for CI: `gh pr checks --watch`
2. When CI passes, ask the user to review and merge, OR (if the fix is trivial and the user pre-approved) run `gh pr merge --squash --delete-branch`.
3. After merge, `git checkout <BASE_BRANCH> && git pull --ff-only origin <BASE_BRANCH>` to pick up the merged commit.

**Autonomous / hand-off mode** (invoked from inside another skill):
1. Do NOT merge automatically. Return `FIX_PR_URL` to the caller and stop here with a clear status: "Fix PR opened at <URL>. Waiting for merge. Rebase and resume must happen after the fix lands."
2. The caller (or user) merges, then re-invokes the rebase/resume steps manually or via a follow-up call.

If the invoker is running in autonomous mode and cannot wait, skip to reporting and let the parent decide. Do not rebase an unmerged fix into the feature branch.

## Step 10: Rebase the original branch onto the fix

Only run this step after the fix PR has actually merged. Verify with `git log --oneline origin/<BASE_BRANCH> | head` and confirm the fix commit is present.

1. Check out the original branch:
   ```bash
   git checkout <ORIGINAL_BRANCH>
   ```
2. Rebase onto the updated base:
   ```bash
   git fetch origin <BASE_BRANCH>
   git rebase origin/<BASE_BRANCH>
   ```
3. If conflicts arise, resolve them (or hand off to the user). Never `git rebase --skip` past real conflicts.

## Step 11: Pop the stash

If `DID_STASH=true`:

```bash
git stash pop
```

If `git stash pop` fails due to conflicts, leave the stash in place and surface the conflict to the invoker. Do not drop the stash.

## Step 12: Verify and resume

1. Run `git status` to confirm the working tree matches the invoker's expectations (same modified/untracked files as before stash, plus whatever the rebase brought in).
2. Re-run the originally failing command (the one that triggered `/fix-develop`) and confirm it now passes.
3. Report to the caller:
   - `FIX_PR_URL`
   - That the original branch has been rebased onto the updated base
   - That the stash has been popped (if applicable)
   - That the originally failing command now passes

The invoker can now resume its work.

---

## Rules

- **Never force-push.** Not to the fix branch, not to the original branch.
- **Never amend** the fix commit after pushing; add a follow-up commit if you need to iterate.
- **Minimal scope.** One logical fix per `/fix-develop` invocation. If you find two unrelated breakages, open two separate fix PRs.
- **Never skip pre-commit hooks.**
- **Never drop the stash** without confirming the working tree is clean and resumable.
- **Never merge your own fix PR without the user's approval** in interactive mode. In autonomous mode, stop at Step 8 and return the URL.
- If any step fails in a way you can't recover from: restore `ORIGINAL_BRANCH`, pop the stash, and surface the error. Leave the repo in the state you found it.

## Invocation from Other Skills

The `work-issue` and `sdlc` skills reference this skill in their "Critical Rule: Never Fix Incidental Breakage in a Feature PR" sections. When those skills detect pre-existing breakage, they should:

1. Pause their own workflow.
2. Invoke `/fix-develop <issue-id-or-description>`.
3. Wait for it to complete (interactive) or surface the fix-PR URL and stop (autonomous).
4. Resume their workflow only after the fix is merged and the rebase/stash-pop have completed.
