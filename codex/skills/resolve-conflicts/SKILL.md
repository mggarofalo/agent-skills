---
name: resolve-conflicts
description: Resolve merge conflicts on an open pull request by rebasing its branch onto the target, preserving both sides' intent, validating the result, and force-pushing only with explicit authorization.
---

# Resolve pull request conflicts

This workflow rewrites branch history. Inspect first, preserve unrelated work, and use `--force-with-lease` only after authorization.

## Establish scope

1. Read the PR metadata, commits, base branch, head branch, and linked issue context.
2. Confirm the PR is open and the current checkout belongs to the intended repository.
3. Require a clean working tree. Do not stash or discard user changes as part of this workflow.
4. Fetch the remote and check whether the base is already an ancestor of the head. Stop as already current when no rebase is needed.

If the head branch is checked out in another worktree, use that worktree or ask the user how to proceed; do not detach or remove it behind their back.

## Rebase and classify conflicts

Rebase the head onto `origin/<base>`. For each conflicted commit, classify files using repository evidence:

- generated artifacts: preserve source inputs and regenerate;
- lock files: resolve manifests first, then regenerate with the repository's package manager;
- additive structured files: merge both valid additions and validate the format;
- binary files: require user direction unless one side is clearly generated;
- non-overlapping text: preserve both changes;
- semantic conflicts: reconstruct both intents from the PR, commits, issues, tests, and surrounding code.

Do not hardcode project-specific solution names, generated paths, or validation commands. Read the applicable `AGENTS.md`, package manifests, and existing scripts.

Resolve the least ambiguous files first. Stage only resolved paths, verify no conflict markers remain, and continue the rebase. Skip a commit only when its change is genuinely empty after resolution, never to bypass a difficult conflict.

## Validate

Run the repository's documented formatting, generation, build, type-check, lint, and test commands in proportion to the diff. Review the final range diff against the pre-rebase branch when useful to ensure the rebase did not silently drop intent.

If validation fails because of the resolution, fix it and keep the correction with the appropriate rebased commit when practical. If failure is pre-existing or resolution intent remains ambiguous, stop with the rebase state intact or abort cleanly, whichever preserves the clearest recovery path, and report exactly what remains.

## Push

Before pushing, verify the current branch matches the PR head and fetch again. A history rewrite requires explicit user authorization unless the invoking request already clearly authorized resolving and force-pushing this PR.

Push only with:

```bash
git push --force-with-lease origin <head-branch>
```

If the lease is rejected, stop. Someone else changed the branch; do not retry against their work.

## Report

List each conflicted file, its category, resolution, validation results, assumptions, and push status. Include any remaining manual follow-up.
