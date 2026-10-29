---
name: find-bugs
description: Run adversarial correctness review on a GitHub pull request, local diff, or diff file using independent Codex reviewers, then verify and synthesize only evidence-backed findings.
---

# Find bugs adversarially

Use this when the user asks for bug analysis or when `$work-issue` reaches its review stage. This is a read-only review workflow; do not edit code or file follow-up issues unless the caller separately asks.

## Resolve the diff

Interpret a bare number as a GitHub PR number, never a Plane issue. Accept a PR number or URL, `local`, or a diff file path. With no argument, detect the current PR; if none exists, use the current branch against its likely base only when that comparison is unambiguous.

Gather the diff, changed-file list, PR description, commits, and applicable repository guidance. Keep the diff available to every reviewer, but require them to inspect surrounding source and tests before asserting behavior.

## Independent passes

Spawn two read-only `pr_bug_finder` subagents in parallel:

1. Hunter: find concrete functional, security, data-integrity, concurrency, resource, error-handling, and compatibility defects introduced or exposed by the diff.
2. Challenger: independently analyze the same diff for likely false positives, hidden guards, existing tests, reachability, and pre-existing behavior. The challenger must form its own view rather than merely agreeing with the hunter.

Ask both agents for file and line evidence, a reproducible scenario, severity, scope, and tests that support or refute the claim. Wait for both.

If subagent delegation is unavailable, run the two passes sequentially yourself and disclose that limitation.

## Verify and synthesize

Re-open every candidate location. Reject style preferences, missing comments, speculative risks without a concrete execution path, and claims contradicted by nearby guards or tests.

Classify surviving items:

- Confirmed bug: real and introduced or directly exposed by the diff.
- Follow-up: real but pre-existing or outside the diff's responsibility.
- Rejected: not a bug or unsupported by evidence.

Use critical only for credible release-blocking security, data loss or corruption, or crashes on a production path. Prefer fewer verified findings over a long speculative list.

## Report

Lead with confirmed bugs ordered by severity. For each include category, exact location, scenario, evidence, scope, and a concise fix direction. Then list follow-ups and rejected candidates with the reason. If nothing survives verification, say so plainly and note any material test gaps that limited confidence.
