---
name: work-issue
description: Implement a Plane issue end to end when the user says work, pick up, implement, or do an issue; covers issue state, branch, plan, code, tests, commit, PR, adversarial review, CI, merge, and closure.
---

# Work a Plane issue

Complete the lifecycle while respecting the user's authorization for external mutations. A request to work an issue authorizes normal issue, branch, push, and PR actions; ask before merge unless the user already approved merging.

## 1. Read and claim the issue

Use the Plane skill and available Plane CLI or MCP tools to resolve the project and retrieve the issue, including acceptance criteria, state, labels, priority, and links. Read applicable `docs/plane.md` and `AGENTS.md` requirements. Summarize the intended behavior and move the issue to In Progress.

Ask a question only when missing information would materially change the implementation or external result. Otherwise state reasonable assumptions in the plan and PR.

## 2. Prepare the branch

Inspect the current branch, worktree, status, remote, and PR state before changing branches.

- If already on the correct issue branch or in a Codex-managed worktree for this task, keep it.
- Otherwise update the requested base branch with a fast-forward-only pull and create `<type>/<issue-id-lower>-<short-slug>`.
- Preserve all unrelated user changes. Never reset, discard, or absorb them into the issue.

## 3. Plan through completion

Maintain a working plan that covers implementation, tests, validation, commit, push, PR, review, remediation, CI, merge, and Plane closure. Use Codex plan tooling for meaningful multi-step work without requiring a separate approval ceremony unless the user asks for one.

## 4. Implement and validate

Read the relevant code, tests, and guidance. Make the smallest coherent change that satisfies the acceptance criteria. Add or update tests for changed behavior and edge cases. Run the repository's documented focused checks, then broader validation proportional to risk. Run pre-commit hooks when present and fix failures honestly.

### Pre-existing breakage

Confirm suspected pre-existing failures against the base when practical. Keep unrelated fixes separable:

- If a tiny fix is required to commit, make the minimum correction in its own clearly labeled commit and record it in the PR.
- If it does not block this issue, leave the code alone and record or file it according to the repository's backlog policy.
- If it is large, risky, or ambiguous, stop and ask rather than expanding scope.

Never suppress checks, use `--no-verify`, or weaken warnings to make the branch pass.

## 5. Commit, push, and open the PR

Review the diff and status, stage only issue files, and use a Conventional Commit that references the issue. Verify the branch immediately before pushing, then push with upstream tracking.

Open a PR against the resolved base with:

- a concise summary tied to acceptance criteria;
- the Plane issue reference;
- exact validation performed;
- assumptions and pre-existing breakage;
- any known limitations or observed-but-not-filed findings.

## 6. Run adversarial review

Invoke `$find-bugs` on the PR. For code diffs, also inspect the changed lines for access-control, injection, secrets, sensitive logging, authentication, unsafe deserialization, SSRF, and dependency risk. Invoke `$owasp-top-10 --diff` only when the diff is broadly security-sensitive or the user requests a formal audit.

When applicable skills or repository guidance explicitly request additional independent reviews, run them concurrently and wait for all results. Do not invent unavailable Claude agent types or depend on `.claude/settings.local.json`.

## 7. Triage findings

Fix confirmed in-scope bugs before merge, add tests, rerun validation, and push follow-up commits. Treat real security findings as fixes, not backlog deferrals.

For out-of-scope findings, apply the repository's filing policy. Otherwise use this default bar:

- file a follow-up when it changes user-visible or contract behavior, risks persisted data, or blocks tracked work;
- record lower-impact observations in the PR under `Observed, not filed`;
- never silently discard a review finding.

## 8. CI, merge, and close

Watch CI. Diagnose and fix failures caused by the branch; distinguish pre-existing or infrastructure failures with evidence. Repeat until required checks pass or a genuine blocker remains.

Ask before merging unless the user already authorized it. Use the repository's required merge method; do not assume squash when release tooling depends on individual commits. After merge, move the Plane issue to Done and add a closing comment when that is the project convention.

## Finish

Return the issue, branch, PR URL, implementation summary, validation, review outcome, merge state, and any follow-up issues. Do not stop at an open PR when the request and authorization include merge.

## Parallel issue work

Use subagents only when the user or applicable guidance requests parallel issue work. Before delegating, verify independent file scopes, `.parallel-sensitive` if present, and a healthy shared base. One agent owns one branch or worktree. Serialize issues that touch the same shared files, generated schemas, dependency locks, or unhealthy base behavior.
