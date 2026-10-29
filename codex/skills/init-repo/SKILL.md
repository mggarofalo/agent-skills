---
name: init-repo
description: Initialize a GitHub repository under mggarofalo with language-appropriate CI, repository guidance, editor and Git configuration, pre-commit checks, and default-branch rules.
---

# Initialize a repository

Build a usable repository, not a frozen copy of an old template. Discover current toolchain versions and existing files before writing anything.

## Inputs and defaults

Resolve the repository name and language or framework from the request or local files. Ask only when either materially changes the result and cannot be inferred.

Defaults:

- GitHub owner: `mggarofalo`;
- default branch: `main`;
- visibility: public unless the user specifies otherwise;
- commits: Conventional Commits;
- guidance: `AGENTS.md` is authoritative; add a minimal `CLAUDE.md` redirect only when Claude compatibility is wanted;
- Plane workspace: discover from the CLI or existing documentation rather than hardcoding it.

## Preflight

1. Check whether the target directory and Git repository already exist.
2. Read existing `README`, guidance, package manifests, CI, editor config, and Git attributes.
3. Verify `gh auth status` before creating or mutating a remote.
4. Determine supported runtime versions from current official actions, installed tooling, manifests, or the user's request. Do not copy old pinned versions from this skill.
5. Preserve every existing file unless the user explicitly authorizes replacement.

## Create or connect the repository

Use `gh repo create mggarofalo/<name>` with the resolved visibility and description. Clone only when the project does not already exist locally. For an existing repository, add or verify `origin` without reinitializing history.

## Scaffold the project

Create only files the stack needs:

- `.gitignore` from an appropriate current template plus local worktree and agent-state exclusions;
- `.gitattributes` with intentional line endings;
- `.editorconfig` matching the language formatter;
- `.github/workflows/ci.yml` using supported action majors and the repository's real build, lint, type-check, and test commands;
- pre-commit configuration when the project has deterministic local checks;
- `AGENTS.md` containing prerequisites, architecture, exact development and validation commands, branch workflow, and commit conventions;
- `docs/plane.md` only when a Plane project is in scope.

Do not assume every stack has the same package manager, solution name, simulator, test runner, or generated files. Detect these from the repository or ask one focused question.

## CI requirements

CI should use reproducible installs and the same commands documented in `AGENTS.md`. Give jobs stable human-readable names because branch rules refer to job names. Validate YAML and, where practical, run the local equivalents before the first push.

## Guidance requirements

Keep `AGENTS.md` concise and repository-specific. Include:

- required tools and versions;
- setup, build, test, lint, format, and run commands;
- important architecture and generated-code boundaries;
- the branch and PR workflow actually used by the repository;
- Plane metadata requirements when applicable;
- Conventional Commit examples relevant to the project.

If creating `CLAUDE.md`, make it only a redirect to `AGENTS.md`; do not duplicate guidance.

## Commit, push, and protect main

Review the full diff, run validation, then create the initial commit and push `main`.

After `main` and CI exist, create a GitHub ruleset named `main protection` targeting `~DEFAULT_BRANCH`. Prefer rules for deletion protection, non-fast-forward protection, PRs, and required status checks. Resolve required check names from the workflow job `name` fields. If GitHub rejects required checks in a ruleset for the current plan, use the supported branch-protection fallback and report the split configuration.

Use zero required approving reviews for the user's solo repositories unless the user requests a different policy. Never guess a status-check context: a nonexistent required check blocks every merge.

## Finish

Verify the remote, default branch, clean working tree, workflow syntax, ruleset contents, and required checks. Report the repository URL, created or preserved files, local validation, CI jobs, and protection mechanism.

Do not create empty placeholder architecture sections, overwrite existing documentation, or weaken protection to make a push succeed.
