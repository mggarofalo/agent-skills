---
name: init-repo
description: Initialize a new GitHub repository with CI, guidance files, and config tailored to the project's language/framework. Creates the repo under mggarofalo, sets up GitHub Actions, AGENTS.md, docs/plane.md, CLAUDE.md, .gitignore, .gitattributes, .editorconfig, and pre-commit hooks.
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
- **Commit style:** [Conventional Commits](https://www.conventionalcommits.org/)
- **Branch strategy:** Two-tier (milestone branches → issue branches, squash-merge, worktrees)
- **Plane workspace:** mggarofalo
- **Agent guidance:** AGENTS.md (primary), CLAUDE.md (redirect to AGENTS.md)

## Execution Steps

### Step 1: Gather inputs

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

If the directory already exists with a git repo, add the remote instead:
```bash
gh repo create mggarofalo/<repo-name> --<visibility> --description "<description>" --source=. --remote=origin --push
```

### Step 3: Generate config files

Create all config files based on the language. Use the templates below.

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

**.NET/C#:** Use the Receipts project's .editorconfig as a starting point (comprehensive C# code style). Read it from `C:\Users\mggar\Source\Receipts\.editorconfig` and adapt.

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

Create `.github/workflows/ci.yml` tailored to the language.

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
      - uses: actions/checkout@v4
      - name: Build
        run: xcodebuild build -scheme <repo-name> -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -quiet
      - name: Test
        run: xcodebuild test -scheme <repo-name> -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -quiet
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
      - uses: actions/checkout@v4
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
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
      - uses: actions/checkout@v4
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"
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
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
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
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
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
3. **Development Workflow** — Plane issue management + two-tier branch strategy (copy the branch strategy section verbatim from the Receipts AGENTS.md at `C:\Users\mggar\Source\Receipts\AGENTS.md` lines 20-113, adapting only the project-specific parts like solution names and project paths)
4. **Build and Test Commands** — language-specific build/test/run commands
5. **Pre-commit Hooks** — if applicable (lint, format, build, test)
6. **Architecture** — project structure and key patterns
7. **Coding Standards** — language-specific conventions
8. **Commit Message Convention** — Conventional Commits (same as Receipts)

Key: The branch strategy, Plane workflow, worktree usage, and commit convention sections should be nearly identical across all projects. Only build commands, architecture, and coding standards change per language.

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

# Update issue state (get state IDs via: plane state list -p <PROJECT> -o json)
plane issue update -p <PROJECT> --work-item-id <UUID> --state <state-id>

# Create a new issue
plane issue create -p <PROJECT> --name "<title>" --description-html "<html>" --priority medium

# Add a comment
plane comment add -p <PROJECT> --work-item-id <UUID> --comment-html "<html>"
```
```

### Step 7: Generate CLAUDE.md

Create a minimal redirect:
```markdown
# CLAUDE.md

See [AGENTS.md](AGENTS.md) for all development guidance.
```

### Step 8: Initial commit and push

```bash
git add .gitignore .gitattributes .editorconfig .github/ AGENTS.md docs/plane.md CLAUDE.md
git commit -m "chore: initial repo setup with CI, guidance, and config"
git push -u origin main
```

### Step 9: Summary

Report what was created:
- GitHub repo URL
- Files created (list)
- CI pipeline (what it does)
- Next steps (what the user should do next)

## Important Notes

- Do NOT create a README if one already exists
- Do NOT overwrite existing files without asking
- If the repo already has commits, work incrementally (don't `git init` over existing history)
- Always verify `gh auth status` before creating repos
- The branch strategy section in AGENTS.md is project-agnostic — copy it from Receipts and only change project-specific references (solution name, project paths)
