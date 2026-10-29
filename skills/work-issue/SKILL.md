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

**Follow-up sensitivity**: the invoking prompt may set how aggressively Step 9 files follow-up issues (`follow-up sensitivity: <level>`). See below. Default is `normal`.

---

## Follow-up Sensitivity

Step 8's bug analysis is adversarial — run against a mature or legacy codebase it will
essentially always surface *something real*. Filing all of it is how a backlog becomes a
branching process: every closed issue spawns more than one new issue, the backlog stops
converging, and each generation drifts further from the goal (fixing the tooling that
tests the fixes to the engine). This knob is the throttle.

**The caller sets it in the invoking prompt.** If unset, use the repo's declared bar
(below), else `normal`.

| Level | File a follow-up issue when… |
|---|---|
| `all` | anything the analysis surfaced. Use when hardening a component you are about to build on. |
| `normal` *(default)* | it changes user-visible or contract behavior, corrupts a persisted artefact, or blocks other tracked work. |
| `strict` | it blocks the current milestone. Nothing else. |
| `none` | never. Everything goes in the PR description. |

**Nothing is discarded silently, at any level.** A finding that does not clear the bar is
recorded in the PR description under a `## Observed, not filed` heading — one line each,
with the file and a one-sentence claim. The information survives in the PR where the code
lives; it just does not become backlog. If the user later wants one promoted, it is right
there.

**Two things the knob never suppresses**, because both are already handled as confirmed
bugs rather than follow-ups:

- Anything from the OWASP sanity check (8b). Security problems get fixed, not filed.
- CRITICAL or HIGH render-cycle findings (8c).

**A repo may declare its own bar.** If the repo's `AGENTS.md`/`CLAUDE.md` states a filing
test, apply it instead of the generic level — it is more specific than anything this file
can say. Quote it in the PR description when you use it to reject a finding, so the call
is auditable.

---

## Critical Rule: Isolate Incidental Breakage

If you encounter pre-existing build, test, or lint breakage on your branch that is **unrelated to your assigned issue scope**, the goal is to keep the fix *separable* — reviewable and revertable on its own — not to avoid fixing it.

**First, confirm it is actually pre-existing.** Check out the base branch (or `git stash` your work) and re-run the failing command. If it fails there too, it is pre-existing. Say so explicitly in the PR description. If it only fails on your branch, it is yours — fix it inline as normal work.

Then pick the path that matches your situation:

**Path A — the breakage blocks your commit** (pre-commit hooks run the full suite, so you cannot commit at all until it passes). This is the common case; do not fight it.
1. Fix it with the **minimum** change that unblocks you.
2. Commit it **separately, before your feature work**, labeled `fix: incidental <what> (pre-existing on <base>)`. Never fold it into a feature commit.
3. File a Plane issue recording the breakage and your fix, so the root cause is tracked:
   ```bash
   plane issue create -p <PROJECT> --name "fix: <breakage>" --description "Pre-existing on <base>, patched incidentally in <branch>. Root cause not addressed." --priority medium
   ```
4. Call it out under a **Pre-existing breakage** heading in the PR description.

**Path B — the breakage does not block you** (it is in a test you are not running, a file you are not touching, or CI-only). Do not fix it. Record or file it according to the repo's backlog policy (default: file the Plane issue as above) and note it in the PR description. Leave the code alone.

**Path C — the fix is large, risky, or needs judgment** (touches many files, changes shared behavior, or you are unsure it is correct). Stop and surface it.
- **Interactive:** ask the user how to proceed.
- **Autonomous:** file the Plane issue, note the blocker in the PR description, and continue with whatever scope you *can* complete. Do not guess at a broad fix.

**Why separability matters:** when parallel agents each fix the same breakage differently inside their own feature commits, the divergence produces cascading merge conflicts. A separate, clearly-labeled commit rebases and reverts cleanly; a fix buried inside a feature commit does not.

**Never** silence breakage to get past it — no skipping tests, no `--no-verify`, no suppressing lint rules, no `TreatWarningsAsErrors` downgrades. If you cannot fix it honestly, use Path C.

---

## Step 1: Read the issue

Fetch the issue using the `plane` CLI (determine the project identifier from `docs/plane.md` or the issue ID prefix):

```bash
plane issue get-by-sequence-id --identifier <ISSUE-ID> --expand state,labels,assignees -o json
```

Save the UUID from the output for later update/comment commands. Extract the title, description, acceptance criteria, labels, priority, and links. Read the repo's `docs/plane.md` and `CLAUDE.md`/`AGENTS.md` for issue-workflow requirements. Summarize it in 2-3 sentences.

Update the issue state to **In Progress** using the `plane` CLI:
```bash
plane issue update -p <PROJECT> --work-item-id <UUID> --state <in-progress-state-id>
```
(Use `plane state list -p <PROJECT> -o json` to find the state ID if needed.)

- **Interactive:** If anything is ambiguous, ask before proceeding.
- **Autonomous:** If anything is ambiguous, make a reasonable assumption and note it. Continue.

## Step 2: Verify or create a branch

Check the current branch, worktree, and status before changing anything:

```bash
git branch --show-current
git status --porcelain
```

- **Already on an issue branch** (e.g. the launcher created it via `claude -w`): skip branch creation, proceed to Step 3.
- **On `main` or a non-issue branch** (user ran `/work-issue` directly): create the branch with the standard naming convention:

```bash
git checkout <base> && git pull --ff-only   # <base> is main unless overridden
git checkout -b <prefix>/<issue-id-lower>-<slugified-title>
```

Preserve any unrelated uncommitted changes the user has — never reset, discard, or absorb them into the issue. If they would block the checkout, stop and ask.

Naming rules: lowercase issue ID, slugified title (non-alphanumeric → hyphens, max ~5 words).

Prefixes (conventional commit style): `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`, `perf/`, `ci/`

Examples: `feat/mgg-54-docker-compose-configuration`, `fix/eng-456-null-pointer-on-login`

## Step 3: Plan

Your plan must include:

1. The code changes (files, approach, edge cases, tests)
2. ALL the remaining steps from this checklist (steps 4-10)
3. An instruction to re-read `~/.claude/skills/work-issue/SKILL.md` after plan approval

- **Interactive:** Enter plan mode. Present the plan to the user for approval. When the user approves (e.g. "looks good", "approved", "go ahead", or any affirmative response), **immediately exit plan mode** (`ExitPlanMode`) and proceed to Step 4. Do NOT ask follow-up questions, solicit additional feedback, or cycle back through the plan after approval.
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

1. Review `git diff` and `git status`. Stage only the files belonging to this issue (by path — never `git add -A` over unrelated user changes).
2. Commit with a Conventional Commit message referencing the issue ID.
3. Verify the branch, then push: `git push -u origin HEAD`

**You are not done. Continue to step 7.**

## Step 7: Open a PR

```bash
gh pr create --title "<concise title>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points describing what changed and why>

Resolves <ISSUE-ID>

## Validation
<Exact commands run and their results>

## Assumptions and pre-existing breakage
<Assumptions made; pre-existing failures confirmed on base — omit if none>

## Known limitations
<Known gaps; `## Observed, not filed` findings are added in Step 9 — omit if none>

EOF
)"
```

**You are not done. Continue to step 8.**

## Step 8: Run analyses

Determine what the diff actually contains, then run the applicable analyses **in parallel** — they are independent.

```bash
gh pr diff --name-only > "${TMPDIR:-/tmp}/changed-files.txt"
```

**8a. Bug analysis** — always runs. Invoke `/find-bugs` on the PR you just created.

**8b. OWASP sanity check** — a quick read of your own diff, not a formal audit. Skip for docs- or asset-only diffs. Read the changed lines once more and ask whether this change introduces any of:

- **Access control** — a new endpoint, query, or handler that does not check the caller owns the resource
- **Injection** — user input reaching SQL/shell/HTML without parameterization or escaping (including `dangerouslySetInnerHTML`)
- **Secrets** — a key, token, connection string, or password added to code, config, or a test fixture
- **Sensitive data** — PII or credentials newly written to logs, error responses, or client-visible payloads
- **Auth** — a change to login, session, token, or password-reset logic
- **Deserialization / SSRF** — untrusted input deserialized, or used to build a URL the server then fetches
- **Dependencies** — a new package added, or a version pinned backwards

Most diffs hit none of these — say nothing and move on. If one *does* apply, note it in the PR description and treat a real problem as a confirmed bug in Step 9. Only if the diff looks broadly security-sensitive (touches auth, or adds an externally-reachable surface) escalate to the full static scan:
```
/owasp-top-10 --diff
```

**8c. React render-cycle QA** — conditional, and **repo-dependent**. Run it only if *both* of these hold:
1. The diff contains `.tsx` or `.jsx` files — check the actual paths, do not assume a directory layout:
   ```bash
   grep -qE '\.(tsx|jsx)$' "${TMPDIR:-/tmp}/changed-files.txt" && echo "react files present"
   ```
2. A `react-render-qa` agent is actually available in this repo — it is defined per-repo, not globally:
   ```bash
   ls .claude/agents/react-render-qa.md 2>/dev/null
   ```

If both hold, launch it via the Task tool:
```
Task tool:
  subagent_type: react-render-qa
  prompt: |
    Analyze the PR on the current branch for React render-cycle bugs.
    Run `gh pr diff` to get the diff, then follow your analysis workflow.
```

If there are no React files, skip 8c silently — it is not applicable and needs no commentary. If there **are** React files but no `react-render-qa` agent in this repo, also skip it, but say so in one line in the PR description so the gap is visible: `React files changed but no react-render-qa agent is defined in this repo.` Never invoke a `subagent_type` you have not confirmed exists — the Task call will fail.

Wait for all launched analyses to complete. Read the report files.

**You are not done. Continue to step 9.**

## Step 9: Triage analysis results

Triage results from every analysis that actually ran in Step 8. Analyses you skipped produce no findings and need no entry here.

**OWASP sanity-check findings (8b):** Treat anything you flagged as a confirmed bug — fix it before merging. Security problems do not become follow-up issues.

**React render-cycle QA findings (8c):**
- **CRITICAL or HIGH findings:** These are bugs. Fix them before merging — same as confirmed bugs below.
- **MEDIUM findings:** File Plane issues for each (same as follow-up recommendations below):
  ```bash
  plane issue create -p <PROJECT> --name "<title>" --description-html "<description>" --priority medium
  ```

**Bug analysis findings (8a):**

**If there are follow-up recommendations:** Adjudicate each against the active
[follow-up sensitivity](#follow-up-sensitivity) level before filing. File the ones that
clear the bar:
```bash
plane issue create -p <PROJECT> --name "<title>" --description-html "<description>" --priority medium
```
- **Interactive:** Ask the user which team/project if not obvious.
- **Autonomous:** Use the same team and project as the source issue.

List the ones that do not clear it under `## Observed, not filed` in the PR description.
Do not drop them and do not file them.

**If there are confirmed bugs:** Fix them, run pre-commit hooks until they pass, commit, and push.
- **Interactive:** You may enter plan mode to plan remediation.
- **Autonomous:** Plan remediation inline and proceed directly to the fix.

**If no confirmed bugs and no follow-ups from either analysis:** Continue to step 10.

- **Autonomous:** You are done. Return the PR URL and a summary of what was implemented, any assumptions made, and any follow-up issues filed. Do NOT proceed to Step 10.

**You are not done. Continue to step 10.**

## Step 10: Wait for CI and merge

> **Autonomous mode stops after Step 9.** This step is interactive-only.

1. Run `gh pr checks --watch` to wait for CI.
2. **If CI passes:** Ask the user if they're ready to merge (skip asking if the request already authorized merge). Merge with the repository's required merge method (`gh pr merge --squash|--merge|--rebase`) — check the ruleset/guidance; don't assume squash when release tooling (e.g. release-please on integration PRs) depends on individual commits.
3. **If CI fails:** Review with `gh pr checks` and `gh run view <run-id> --log-failed`. Fix failures caused by the branch autonomously if you can; ask the user if you're unsure. Distinguish pre-existing or infrastructure failures with evidence (same failure on base, runner/network errors) rather than assuming. Commit, push, repeat until required checks pass or a genuine blocker remains.
4. After merge, update the Plane issue state to "Done" using the `plane` CLI, and add a closing comment when that is the project convention:
   ```bash
   plane state list -p <PROJECT> -o json   # find the state ID for "Done"
   plane issue update -p <PROJECT> --work-item-id <UUID> --state <state-id>
   ```

Don't stop at an open PR when the request and authorization include merge.

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

1. **Pre-flight checks** (see below) — serialize instead of parallelizing if scopes collide or develop is red.
2. **Spawn** one agent per issue, all in parallel with `isolation: "worktree"`.
3. **Wait** for agents to complete. Each returns a PR URL and summary.
4. **Review** the PRs (or ask the user to review them).
5. **Merge** approved PRs and update Plane issue status.

### Pre-flight checks before launching parallel work-issue agents

**You must run these checks before dispatching any parallel agents. If any check fails, do NOT parallelize.**

1. **Read `.parallel-sensitive`** in the target repo root (if it exists). This file lists paths that are known to produce collateral merge damage when modified by parallel agents (e.g., shared config, lockfiles, entity base classes, DI registration files). One glob or path per line; lines starting with `#` are comments.
2. **Predict scope for each pending issue.** Read each issue's description and infer which files it will touch. Be explicit — write the predicted file set into your plan.
3. **Check for scope collisions against `.parallel-sensitive`.** If two pending scopes both intersect a path listed in `.parallel-sensitive`, do NOT parallelize those two issues — serialize them instead.
4. **Check base-branch health.** If the base branch (`develop`, or `main` for repos without develop) is currently red — failing CI, broken build, failing tests — do NOT dispatch parallel agents. Every agent would independently trip over the same breakage and fix it differently. Land a fix on the base branch first, wait for it to merge, then dispatch.

### Constraints

- Only parallelize issues that don't touch the same files. If two issues modify the same code, work them sequentially.
- The parent agent should not duplicate work the subagent is doing.
- Each agent handles its own bug analysis and follow-up issue filing.
- Each subagent must honor the **Critical Rule: Isolate Incidental Breakage** — pre-existing breakage gets its own labeled commit and a Plane issue, never folded into a feature commit. This matters most under parallel dispatch, where several agents hit the same breakage at once.
