---
name: init-repo
description: Initialize a new GitHub repository with CI, guidance files, and config tailored to the project's language/framework. Creates the repo under mggarofalo, sets up GitHub Actions, branch protection rulesets, AGENTS.md, docs/plane.md, CLAUDE.md, .gitignore, .gitattributes, .editorconfig, and pre-commit hooks.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch
---

# Init Repo

Initialize a new GitHub repository with full project scaffolding: CI pipeline, agent guidance, editor config, and git hooks — all tailored to the project's language and framework.

## Inputs

The user may provide these as arguments or you should ask:

1. **Repo name** (required) — the GitHub repository name
2. **Language/framework** (required) — determines templates for CI, linting, .gitignore, .editorconfig
3. **Description** (optional) — one-line repo description
4. **Visibility** (optional, default: public) — public or private
5. **Plane project name** (optional) — if provided, creates docs/plane.md with project reference

## Conventions (mggarofalo standard)

These conventions apply to ALL repos regardless of language:

- **GitHub account:** `mggarofalo`
- **Default branch:** `main`
- **Branch protection:** a ruleset named `main protection` targeting `~DEFAULT_BRANCH` (see Step 9)
- **Commit style:** [Conventional Commits](https://www.conventionalcommits.org/)
- **Branch strategy:** Two-tier (milestone branches → issue branches, squash-merge, worktrees)
- **Plane workspace:** discover from the `plane` CLI config or existing docs — don't hardcode it
- **Agent guidance:** AGENTS.md (primary), CLAUDE.md (redirect to AGENTS.md)

## Execution Steps

### Step 1: Preflight and gather inputs

Build a usable repo, not a frozen copy of an old template. Before writing anything:

1. Check whether the target directory and git repo already exist.
2. Read any existing README, guidance files, package manifests, CI, `.editorconfig`, and `.gitattributes`. Preserve every existing file unless the user explicitly authorizes replacement.
3. Verify `gh auth status` before creating or mutating a remote.
4. Determine current supported runtime and GitHub Action versions from official sources (WebSearch the action's README / release page), installed tooling, or manifests. Do not copy versions from this skill.
5. Detect the stack's package manager, solution/project name, test runner, simulator, and generated files from the repo — don't assume every project matches another. Ask one focused question only when the answer can't be inferred.

If the user didn't provide all required inputs, ask using AskUserQuestion. For language, offer common options:

- Swift/iOS
- .NET/C#
- React/TypeScript
- Python
- Node.js/TypeScript
- Other (specify)

### Step 2: Create the GitHub repo

```bash
gh repo create mggarofalo/<repo-name> --<visibility> --description "<description>" --clone
```

If the directory already exists with a git repo, add the remote instead (never reinitialize existing history; the push happens in Step 8 after validation):
```bash
gh repo create mggarofalo/<repo-name> --<visibility> --description "<description>" --source=. --remote=origin
```

### Step 3: Generate config files

Create only the config files the stack needs. The templates below are shape examples — adapt them to the detected stack.

#### .gitignore

Use the appropriate template for the language. Fetch from GitHub's gitignore templates or use a known good one. Always add:
```
# Worktrees
.worktrees/

# Claude
.claude/settings.local.json
```

#### .gitattributes

Enforce line endings per language:

**Swift/iOS:**
```
*.swift text eol=lf
*.plist text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.md text eol=lf
*.sh text eol=lf
```

**.NET/C#:**
```
*.cs text eol=crlf
*.csproj text eol=crlf
*.sln text eol=crlf
*.slnx text eol=crlf
*.props text eol=crlf
*.targets text eol=crlf
*.razor text eol=crlf
*.cshtml text eol=crlf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.md text eol=lf
*.sh text eol=lf
```

**React/TypeScript / Node.js:**
```
*.ts text eol=lf
*.tsx text eol=lf
*.js text eol=lf
*.jsx text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.md text eol=lf
*.sh text eol=lf
*.css text eol=lf
*.html text eol=lf
```

**Python:**
```
*.py text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.md text eol=lf
*.sh text eol=lf
*.cfg text eol=lf
*.toml text eol=lf
*.ini text eol=lf
```

#### .editorconfig

**Swift/iOS:**
```ini
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

**.NET/C#:** Use the Receipts project's .editorconfig as a starting point (comprehensive C# code style). Read it from `~/Source/Receipts/.editorconfig` if present (otherwise `dotnet new editorconfig`) and adapt.

**React/TypeScript / Node.js:**
```ini
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

**Python:**
```ini
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

### Step 4: Generate GitHub Actions CI

Create `.github/workflows/ci.yml` tailored to the language, using the repo's real build, lint, type-check, and test commands and reproducible installs.

These templates show **shape only**. Replace every `<current…>` placeholder with what Step 1 found (latest supported action major, current runtime LTS, an installed simulator from `xcrun simctl list devices available`). Give jobs stable human-readable `name:` fields — the branch ruleset refers to them.

**Swift/iOS:**
```yaml
name: Swift CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  build:
    name: Build & Test
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@<current-major>
      - name: Build
        run: xcodebuild build -scheme <repo-name> -destination 'platform=iOS Simulator,name=<installed-simulator>' -quiet
      - name: Test
        run: xcodebuild test -scheme <repo-name> -destination 'platform=iOS Simulator,name=<installed-simulator>' -quiet
```

**.NET/C#:**
```yaml
name: .NET CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

env:
  DOTNET_NOLOGO: true
  DOTNET_CLI_TELEMETRY_OPTOUT: true

jobs:
  build:
    name: Build & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<current-major>
      - name: Setup .NET
        uses: actions/setup-dotnet@<current-major>
        with:
          dotnet-version: "<current-lts>.x"
      - name: Restore
        run: dotnet restore
      - name: Build
        run: dotnet build --no-restore -p:TreatWarningsAsErrors=true
      - name: Test
        run: dotnet test --no-build --verbosity normal

  lint:
    name: Code Formatting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<current-major>
      - name: Setup .NET
        uses: actions/setup-dotnet@<current-major>
        with:
          dotnet-version: "<current-lts>.x"
      - name: Restore
        run: dotnet restore
      - name: Check formatting
        run: dotnet format --no-restore --verify-no-changes
```

**React/TypeScript:**
```yaml
name: Frontend CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  build:
    name: Build & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<current-major>
      - name: Setup Node.js
        uses: actions/setup-node@<current-major>
        with:
          node-version: <current-lts>
          cache: npm
      - name: Install dependencies
        run: npm ci
      - name: Lint
        run: npm run lint
      - name: Type check
        run: npm run typecheck
      - name: Test
        run: npm test -- --run
      - name: Build
        run: npm run build
```

**Python:**
```yaml
name: Python CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  build:
    name: Build & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<current-major>
      - name: Setup Python
        uses: actions/setup-python@<current-major>
        with:
          python-version: "<current-supported>"
          cache: pip
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint
        run: ruff check .
      - name: Format check
        run: ruff format --check .
      - name: Test
        run: pytest
```

### Step 5: Generate AGENTS.md

Create `AGENTS.md` with these sections (adapt content to the language):

1. **Header** — "This file provides guidance to AI agents working with code in this repository."
2. **Prerequisites** — language runtime, build tools, versions
3. **Development Workflow** — Plane issue management + two-tier branch strategy (use the "Workflow Rules" section of `~/Source/Receipts/AGENTS.md` as the reference, adapting only project-specific parts like solution names and project paths)
4. **Build and Test Commands** — language-specific build/test/run commands
5. **Pre-commit Hooks** — if applicable (lint, format, build, test)
6. **Architecture** — project structure and key patterns
7. **Coding Standards** — language-specific conventions
8. **Commit Message Convention** — Conventional Commits (same as Receipts)

Key: The branch strategy, Plane workflow, worktree usage, and commit convention sections should be nearly identical across all projects. Only build commands, architecture, and coding standards change per language. Keep it concise and repo-specific; commands must be exact and match CI. Don't create empty placeholder sections.

### Step 6: Generate docs/plane.md

If a Plane project exists or was specified, create `docs/plane.md` with:

1. Workspace structure (project identifier, modules)
2. Labels relevant to the project
3. Priority semantics (same across all projects — copy from Receipts)
4. "How to determine what's next" decision rules (same across all projects)
5. CLI Quick Reference section:

```markdown
## CLI Quick Reference

```bash
# Fetch an issue
plane issue get-by-sequence-id --identifier <ISSUE-ID> --expand state,labels,assignees -o json

# Update issue state
plane issue update -p <PROJECT> --work-item-id <UUID> --state <state-id>

# Create a new issue
plane issue create -p <PROJECT> --name "<title>" --description-html "<description>" --priority medium

# Add a comment to an issue
plane comment add -p <PROJECT> --work-item-id <UUID> --comment-html "<html>"

# List states (to find state IDs)
plane state list -p <PROJECT> -o json
```
```

### Step 7: Generate CLAUDE.md

Create a minimal redirect:
```markdown
# CLAUDE.md

See [AGENTS.md](AGENTS.md) for all development guidance.
```

### Step 8: Initial commit and push

Before the first push: review the full diff, validate workflow YAML (e.g. `actionlint` if installed, otherwise parse it), and run the local equivalents of every CI command so the first CI run isn't the first test.

```bash
git add .gitignore .gitattributes .editorconfig .github/ AGENTS.md docs/plane.md CLAUDE.md
git commit -m "chore: initial repo setup with CI, guidance, and config"
git push -u origin main
```

### Step 9: Branch protection ruleset

Do this AFTER the initial push, so `main` exists and the CI job names are known.

Use a **ruleset**, not legacy branch protection. Rulesets target `~DEFAULT_BRANCH` (so they survive a rename), stack cleanly, and are what every existing mggarofalo repo uses.

#### The standard ruleset

Four rule blocks. This is the `main protection` ruleset from Receipts, which is the reference implementation:

| Rule | Why |
|---|---|
| `deletion` | Can't delete the default branch |
| `non_fast_forward` | Can't force-push / rewrite history |
| `pull_request` | No direct commits to `main`; dismiss stale reviews on push |
| `required_status_checks` | Every CI job must pass before merge |

`required_approving_review_count` is **0**. These are solo repos — requiring an approval you'd give yourself is theater, and it blocks agent-driven merges. The PR requirement alone is what gates direct pushes.

Create it with:

```bash
gh api repos/mggarofalo/<repo-name>/rulesets --method POST --input - <<'JSON'
{
  "name": "main protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "allowed_merge_methods": ["merge", "squash", "rebase"],
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "do_not_enforce_on_create": false,
        "strict_required_status_checks_policy": false,
        "required_status_checks": [
          { "context": "Build & Test" }
        ]
      }
    }
  ]
}
JSON
```

#### Status check contexts

The `context` string must match the job's `name:` field in the workflow **exactly** — not the job key. Read it from the workflow you actually wrote; never guess a status-check context — a nonexistent required check blocks every merge. From the Step 4 CI templates:

| Language | Contexts |
|---|---|
| Swift/iOS | `Build & Test` |
| .NET/C# | `Build & Test`, `Code Formatting` |
| React/TypeScript | `Build & Test` |
| Python | `Build & Test` |

If you add jobs later (vulnerability scan, conventional-commit lint, API breaking-change check, test shards), add matching contexts to the ruleset in the same change. A required check that never reports blocks merges forever; a CI job that isn't required silently stops gating.

Keep `strict_required_status_checks_policy: false` — `true` forces every PR to be rebased onto the tip of `main` before merge, which thrashes on solo repos.

#### If status checks are rejected

Status-check rules inside rulesets may require a paid plan on personal repos. If the API rejects that block, fall back to the **hybrid** setup: create the ruleset with the first three rules only, then set required checks through the legacy branch protection API.

```bash
gh api repos/mggarofalo/<repo-name>/branches/main/protection --method PUT --input - <<'JSON'
{
  "required_status_checks": { "strict": false, "contexts": ["Build & Test"] },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

This is what gh-plane-sync runs. Note it in the Step 10 summary so the split configuration isn't a surprise later.

#### Verify

```bash
gh api repos/mggarofalo/<repo-name>/rulesets/<id> --jq '{name, conditions, rules}'
```

Confirm the rule types and every status-check context are present.

### Step 10: Summary

Report what was created:
- GitHub repo URL
- Files created (list)
- CI pipeline (what it does)
- Branch protection (ruleset name + ID, which rules, which required checks, and whether checks came via ruleset or the legacy fallback)
- Next steps (what the user should do next)

## Important Notes

- Do NOT create a README if one already exists
- Do NOT overwrite existing files without asking
- If the repo already has commits, work incrementally (don't `git init` over existing history)
- Always verify `gh auth status` before creating repos
- Never weaken branch protection to make a push succeed
- **`non_fast_forward` has no API bypass.** Once the ruleset is active, a force-push to `main` — including resetting after a bad merge — requires manually unchecking "Block force pushes" in **Settings → Rules → Rulesets**, then re-enabling it. Tell the user this rather than trying to work around it, and remind them to turn it back on.
- **Merge method matters for release-please.** Squash-merging a `develop`-style integration PR collapses its `feat`/`fix` commits into one `chore:` commit, and release-please then skips the release entirely. For integration PRs, use a merge commit; squash is fine for ordinary feature PRs.
