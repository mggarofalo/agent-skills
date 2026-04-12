# Phase 2: Implementer

## Purpose

Execute the plan from Phase 1 — write code, create a branch, and commit the changes. This phase transforms the plan into working code.

## Inputs

- The plan from Phase 1 (in the state file)
- Project conventions (from AGENTS.md / state file header)
- The branch name derived from the Plane issue identifier

## Steps

### 1. Read the Plan

- Read the state file and extract the Phase 1 plan
- Understand the files to modify/create, the approach, and the design decisions
- If no plan exists in the state file, **stop and fail** — Plan phase must run first

### 2. Set Up the Branch

- Check if a worktree already exists for this issue's branch
- If not, create a worktree using the project's branch strategy:
  - Construct the branch name from the issue identifier (e.g., `feat/receipts-123-feature-name`)
  - Create the worktree: `git worktree add .claude/worktrees/<branch-name> -b <branch-name>`
- Change working directory to the worktree

### 3. Implement the Changes

- Follow the plan step by step
- For each file to modify:
  - Read the file first
  - Make targeted edits using the `Edit` tool
  - Follow existing patterns and conventions from the codebase
- For each file to create:
  - Use the `Write` tool
  - Follow the project's file organization and naming conventions
- Key implementation principles:
  - Follow the plan's approach — don't deviate without good reason
  - Match existing code style exactly (indentation, naming, patterns)
  - Don't add unnecessary abstractions or over-engineer
  - Handle errors at system boundaries only
  - Don't add comments unless the logic is non-obvious

### 4. Build Verification

- Run the project's build command (from AGENTS.md or detected during init):
  - .NET: `dotnet build`
  - Node: `npm run build` or `yarn build`
  - Python: syntax check or type check if configured
  - Swift: `swift build`
- If the build fails:
  - Read the error output
  - Fix the build errors
  - Re-run the build
  - Repeat until the build succeeds or it's clear the issue is structural (then fail)

### 5. Commit the Changes

#### 5a. Discover allowed commit scopes

Before composing the commit message, determine whether the repo restricts Conventional Commits scopes. Picking a scope from the feature name (e.g., `ynab`, `auth`, `checkout`) without checking the allowlist is the most common way this phase produces PRs that fail CI. Check in this order and stop at the first hit:

1. **GitHub Actions workflows** — search `.github/workflows/*.yml` for `amannn/action-semantic-pull-request`. If found, extract the `scopes:` list from the action's `with:` block (it may be newline-separated or comma-separated).
2. **commitlint config** — check `commitlint.config.js`, `commitlint.config.cjs`, `commitlint.config.mjs`, `commitlint.config.ts`, `.commitlintrc`, `.commitlintrc.js`, `.commitlintrc.json`, `.commitlintrc.yml`. Extract the `scope-enum` rule values.
3. **package.json** — check for a top-level `commitlint` key with a `rules.scope-enum` entry.
4. **Git hooks** — read `.husky/commit-msg`, `.githooks/commit-msg`, or any `commit-msg` hook referenced from `core.hooksPath`. Look for explicit scope validation (e.g., a regex or `case` statement against a fixed list). Note: the pre-commit hook's allowlist may differ from the CI workflow's allowlist — always prefer the CI allowlist when both are present, since CI is the gate that blocks merge.
5. **Fallback** — if nothing matches, treat scopes as unrestricted.

Record the discovered allowlist (or `unrestricted`) in the state file under Phase 2 as `**Allowed Scopes:** <list>`.

#### 5b. Select a scope from the allowlist

Pick a scope from the discovered allowlist that best matches the file paths touched by this commit:

- Prefer the scope whose name maps most directly to the primary directory in the diff (e.g., changes rooted in `src/Application/` → `application`, `src/Infrastructure/` → `infrastructure`, `src/Client/` → `client`).
- If changes span multiple allowed scopes, pick the one with the largest share of modified lines, or the most architecturally significant layer.
- **Do not** pick a scope based on the feature or integration name unless that name is in the allowlist. A feature-name scope like `ynab` is a natural choice but will bounce at CI if the allowlist is `api, client, domain, application, infrastructure, …`.
- If no allowed scope matches the diff, **fail the commit step**: print the allowed scopes and the files changed, and ask the user which scope to use via `AskUserQuestion`. In autonomous mode, pick the most architecturally significant allowed scope, note the assumption in the state file under `**Scope Assumption:**`, and proceed.

#### 5c. Compose and commit

- Stage the changed/created files (be specific — don't use `git add -A`).
- Compose the message using the project's conventional commit format from AGENTS.md, with the scope chosen in 5b.
- Default format if no convention specified: `feat(<scope>): <description>`. If scopes are unrestricted and no natural scope applies, omit the `(<scope>)` parens entirely.
- Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` in the commit message.

### 6. Update State File

Append implementation details to the state file:

```markdown
## Phase 2: Implement
**Status:** pass (or fail)
**Branch:** <branch-name>
**Worktree:** <worktree-path>
**Allowed Scopes:** <discovered list, or `unrestricted`, plus source (workflow yaml / commitlint / package.json / hooks / fallback)>
**Commits:**
- `<hash>`: <commit message>
**Files Changed:**
- <file1> — <summary of change>
- <file2> — <summary of change>
**Build Output:** <pass/fail with summary>
```

## Pass/Fail Criteria

- **Pass:** Build succeeds after implementation
- **Fail:** Build errors remain after implementation attempts

## Remediation Context

When this phase is re-invoked for remediation (fixing Review or Security findings):
1. Read the failing phase's findings from the state file
2. Address each CRITICAL finding specifically
3. Re-run the build to verify fixes don't break anything
4. Commit the fixes as a separate commit with message: `fix(<scope>): address <phase> findings`
5. Append remediation details to the state file under the original Phase 2 section
