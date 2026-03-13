---
name: resolve-conflicts
description: >
  Resolve merge conflicts on a PR by rebasing onto its target branch, resolving
  conflicts per-category (generated, lock files, semantic, etc.), validating the
  result, and force-pushing. Use when a PR has fallen behind its target and has
  conflicts blocking merge.
user_invocable: true
argument: "<PR-URL-or-number>"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

## YOU MUST EXECUTE ALL STEPS BELOW

This is a **checklist you must execute**, not documentation. You are responsible for every step. After completing each step, move to the next one. If you stop early, the task is incomplete.

After exiting plan mode or after any context compaction, re-read this file (`~/.claude/skills/resolve-conflicts/SKILL.md`) to get the full checklist back in context.

## Execution Modes

This skill supports two modes. Detect which mode you are in **before starting Step 1**.

**Interactive mode** (default): You are running in a direct conversation with the user. Ask clarifying questions for ambiguous conflicts and request push authorization.

**Autonomous mode**: You are running as a subagent, or the invoking prompt contains "autonomous", "plan approved", or "headless". In this mode:
- Do NOT use `EnterPlanMode` or `AskUserQuestion` — these block and you cannot receive interactive responses.
- Make reasonable assumptions instead of asking questions; document assumptions in the report.
- For push: requires explicit "force-push approved" in the invoking prompt. Otherwise stop with local-only resolution.

---

## Step 1: Fetch PR metadata

```bash
gh pr view <PR> --json number,title,body,headRefName,baseRefName,state,commits
```

- Extract the head branch, base branch, title, body, and commit list.
- Verify the PR state is `OPEN`. If not, stop and report.
- Save the head and base branch names for use throughout.

## Step 2: Read reference issues

Extract Plane issue IDs from the PR title, body, and branch name (pattern: `RECEIPTS-\d+`).

For each issue ID found:
1. Fetch the issue:
   ```bash
   plane issue get-by-sequence-id --identifier <ID> --expand state,labels,assignees -o json
   ```
2. If the script fails (exit code non-zero), check `docs/issues/` for archived issue markdown files.

Also extract context from the PR's commit messages (already fetched in Step 1).

This context is **critical** for resolving semantic conflicts in Step 6 — it tells you the *intent* behind the PR's changes.

## Step 3: Prepare workspace

1. Verify a clean working tree:
   ```bash
   git status --porcelain
   ```
   If there are uncommitted changes, **stop** and report. Do not stash or discard — the user may have work in progress.

2. Fetch latest:
   ```bash
   git fetch origin
   ```

3. Checkout the head branch:
   ```bash
   git checkout <head-branch>
   ```

4. Check if rebase is needed:
   ```bash
   git merge-base --is-ancestor origin/<base-branch> <head-branch>
   ```
   If exit code is 0, the head branch already contains all base commits. **Short-circuit**: report "Already up to date" and stop.

## Step 4: Attempt rebase

```bash
git rebase origin/<base-branch>
```

- If the rebase completes cleanly (exit code 0), skip to **Step 8**.
- If the rebase stops with conflicts, continue to Step 5.

## Step 5: Categorize conflicts

List conflicted files:
```bash
git diff --name-only --diff-filter=U
```

For each conflicted file, assign a category based on path and type:

| Category | Patterns | Strategy |
|----------|----------|----------|
| **generated** | `*.g.cs`, `openapi/generated/*`, `src/client/src/generated/*`, `API.json` | Accept base version, regenerate after all conflicts resolved |
| **openapi-spec** | `openapi/spec.yaml` | Accept-both (additive merge — both sides add endpoints/schemas) |
| **lock-file** | `package-lock.json` | Accept base version + `npm install` after resolution |
| **binary** | Non-text files (images, etc.) | Escalate (interactive) / accept ours (autonomous) |
| **non-overlapping** | Different hunks in same file (no overlapping line ranges) | Accept both sides — merge manually |
| **semantic** | Same lines changed by both sides | Analyze intent from issue context + PR description + commits |

To detect non-text files:
```bash
git diff --numstat --diff-filter=U
```
Files with `-` for added/removed lines are binary.

## Step 6: Resolve per category

Work **least-ambiguous first**: generated → lock-file → openapi-spec → non-overlapping → binary → semantic.

### Generated files
```bash
git checkout origin/<base-branch> -- <file>
git add <file>
```
Do NOT manually merge — these will be regenerated in the post-resolution step.

### Lock files (`package-lock.json`)
```bash
git checkout origin/<base-branch> -- package-lock.json
git add package-lock.json
```
Will run `npm install` in the post-resolution step to reconcile with the head branch's `package.json`.

### OpenAPI spec (`openapi/spec.yaml`)
Read the conflict markers. Both sides typically add new paths/schemas. Accept both additions:
1. Read the file with conflict markers.
2. Edit to include both sides' additions (remove markers, keep all new content).
3. Verify YAML validity.
4. `git add openapi/spec.yaml`

### Non-overlapping conflicts
The conflict markers show changes to different parts of the file. Include both sets of changes:
1. Read the file with conflict markers.
2. Edit to include changes from both sides in their respective locations.
3. `git add <file>`

### Binary files
- **Interactive:** Ask the user which version to keep.
- **Autonomous:** Accept ours (the head branch version):
  ```bash
  git checkout --ours <file>
  git add <file>
  ```

### Semantic conflicts
These are the hardest — the same lines were modified by both sides for different reasons.

1. Read the conflict markers carefully.
2. Use the Plane issue context from Step 2 to understand:
   - What the PR's changes intended to accomplish
   - What the base branch changes (merged since the PR was opened) intended to accomplish
3. The PR represents **active work** — its intent should generally be preserved. The base changes represent **merged context** that must be incorporated.
4. Write a resolution that satisfies both intents.
5. `git add <file>`

- **Interactive:** If the intent is truly ambiguous, show the conflict and both contexts to the user and ask how to resolve.
- **Autonomous:** Make a best-effort resolution. Document the assumption in the final report.

### Post-resolution: Regenerate artifacts

After all conflicts in this commit are resolved:

1. **Regenerate .NET generated code:**
   ```bash
   dotnet build Receipts.slnx
   ```
   This regenerates `openapi/generated/API.json` and `*.g.cs` files.

2. **Regenerate TypeScript types (if client files were involved):**
   ```bash
   npx openapi-typescript openapi/generated/API.json -o src/client/src/generated/api.ts
   ```

3. **Reconcile lock files (if package.json changed):**
   ```bash
   npm install
   cd src/client
   npm install
   cd -
   ```

4. Stage any regenerated files:
   ```bash
   git add openapi/generated/ src/client/src/generated/ src/Presentation/API/Generated/
   ```
   Also stage `package-lock.json` and `src/client/package-lock.json` if they changed.

## Step 7: Continue rebase

```bash
git rebase --continue
```

- If more commits conflict, **loop back to Step 5** for the new set of conflicts.
- If a commit becomes empty after resolution:
  ```bash
  git rebase --skip
  ```
- Repeat until the rebase completes.

## Step 8: Validate

Run the project's validation pipeline (mirrors pre-commit hooks):

```bash
dotnet format Receipts.slnx --verify-no-changes
```
If formatting fails, fix automatically:
```bash
dotnet format Receipts.slnx
```
Then re-check.

```bash
Jwt__Key=build-time-spec-extraction-only-not-for-runtime dotnet build Receipts.slnx -p:TreatWarningsAsErrors=true --no-restore
```

```bash
dotnet test Receipts.slnx --no-build --verbosity normal
```

```bash
npx tsc --noEmit --project src/client/tsconfig.json
```

```bash
npx eslint src/client/src
```

**If validation fails:**
- **Interactive:** Enter plan mode to diagnose and fix.
- **Autonomous:** Attempt to fix automatically (up to 2 retries). If still failing after retries, abort the rebase cleanly and report:
  ```bash
  git rebase --abort
  ```

If you made fixes during validation, amend them into the appropriate commit or add a fixup commit.

## Step 9: Push

**Interactive:**
1. Verify the branch:
   ```bash
   git branch --show-current
   ```
   Must match the head branch from Step 1.
2. Ask the user for authorization to force-push.
3. Push:
   ```bash
   git push --force-with-lease origin <head-branch>
   ```

**Autonomous:**
1. Verify the branch matches.
2. Check if the invoking prompt contains "force-push approved".
   - If yes: push with `--force-with-lease`.
   - If no: **stop** with local-only resolution. Report that the rebase is complete locally but not pushed.

**Rules:**
- Always `--force-with-lease`, never bare `--force`.
- If `--force-with-lease` is rejected (someone else pushed), report the conflict and stop. Do not retry.

## Step 10: Report

Output a summary table:

```
## Conflict Resolution Report

| File | Category | Strategy | Notes |
|------|----------|----------|-------|
| ... | ... | ... | ... |

### Validation
- Format: pass/fail
- Build: pass/fail
- Tests: pass/fail
- TypeScript: pass/fail
- ESLint: pass/fail

### Push
- Status: pushed / local-only / rejected
- Branch: <head-branch>
- Target: <base-branch>

### Assumptions (autonomous mode only)
- ...
```

**You are done.**

---

## Rules

- **Always `--force-with-lease`**, never bare `--force`.
- **Verify the branch** before every push — `git branch --show-current` must match the PR's head branch.
- **No compound Bash commands** — no `&&`, `||`, `;` in a single Bash call (hook constraint). Use separate sequential calls.
- **Regenerate, don't merge** generated files (`*.g.cs`, `API.json`, generated TypeScript types).
- **Preserve PR intent** for semantic conflicts — the PR is active work; the base is merged context.
- **Abort cleanly** on unrecoverable failure:
  ```bash
  git rebase --abort
  ```
- **Never stash or discard** uncommitted changes — stop and report if the tree is dirty.

## When to Use

- A PR has merge conflicts blocking merge
- User says "resolve conflicts on PR #X" or "rebase PR #X"
- A parent agent needs to bring a branch up to date before merging
- CI shows "branch is out of date" or "merge conflicts"

## When NOT to Use

- The PR is already up to date (Step 3 short-circuits)
- The user wants to manually resolve conflicts themselves
- The branch has complex history that needs interactive rebase (`git rebase -i`)

## Edge Cases Handled

- **Multiple conflicting commits** — Step 7 loops back to Step 5 for each
- **Validation fails after resolution** — retry mechanism (autonomous) or plan mode (interactive)
- **PR already up to date** — Step 3 short-circuits with a report
- **Binary conflicts** — escalate (interactive) or accept ours (autonomous)
- **Empty commits after rebase** — `git rebase --skip`
- **Concurrent push by someone else** — `--force-with-lease` rejects safely
- **Dirty working tree** — Step 3 stops early
- **Generated file conflicts** — accept base, regenerate after resolution
- **Lock file conflicts** — accept base, `npm install` after resolution

## Orchestration (Parallel / Subagent Execution)

A parent agent can invoke this skill to resolve conflicts on a PR before merging.

### How to invoke from a parent agent

```
Task tool:
  subagent_type: general-purpose
  model: opus
  isolation: worktree
  prompt: |
    You are running in autonomous mode with force-push approved.
    Use the /resolve-conflicts skill on PR #<NUMBER>.
    Resolve all conflicts, validate, and push.
```

### Permission prerequisites

The project's `.claude/settings.local.json` must auto-allow:

- `Edit` and `Write` — for resolving conflicts in source files
- `Bash(git push:*)` — for force-pushing the rebased branch
- `Bash(npm install:*)` — for reconciling lock files

### Constraints

- **One agent per PR branch** — concurrent rebases on the same branch will cause force-push conflicts.
- The agent must have the full repo history available (not a shallow clone).
- Worktree isolation is recommended but not required — the skill checks for a clean tree in Step 3.
