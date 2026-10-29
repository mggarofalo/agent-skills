---
name: owasp-top-10
description: >
  Audit a codebase against the OWASP Top 10 (2021) using static code analysis
  and dependency scanning. Scopes to a path or to the current diff. Reports
  findings by severity with OWASP category references.
---

# OWASP Top 10 Security Audit

Audit a codebase against the OWASP Top 10 (2021) using static code analysis and dependency scanning. Reports findings by severity (CRITICAL/HIGH/MEDIUM/LOW) with OWASP category references.

This skill is **static only** — it reads code and dependency manifests. It does not drive a browser and does not need a running app.

## Usage

- `$owasp-top-10 <path>` — Static scan of specific files or directories
- `$owasp-top-10 --diff` — Scan only git-changed files (staged + unstaged)
- `$owasp-top-10 --deps` — Dependency audit only

For a quick per-PR judgment call rather than a full scan, `work-issue` Step 8b carries a short OWASP checklist to apply directly to a diff. Escalate here when a diff looks broadly security-sensitive.

## Phase 1: Setup & Target Resolution

### Parse Arguments

Parse the argument string to determine audit mode:

1. **Path** (does not start with `--`): Static scan of that path. Can be a file or directory.
2. **`--diff`**: Run `git diff --name-only HEAD` and `git diff --name-only --cached` to get changed files. Filter to code files only (exclude images, binaries, lock files). Static scan those files.
3. **`--deps`**: Skip static pattern scanning; run Phase 3 (dependency audit) only.

With no argument, scan the repository root.

### Detect Tech Stack

Detect which technology stacks are present by checking for marker files:

| Stack | Marker Files |
|-------|-------------|
| .NET | `*.csproj`, `*.sln`, `Directory.Build.props` |
| Node/JS/TS | `package.json`, `tsconfig.json` |
| Python | `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` |
| Go | `go.mod` |
| Rust | `Cargo.toml` |
| Ruby | `Gemfile` |

Use Glob to check for these files at the project root. Record all detected stacks — multiple may be present (e.g., .NET backend + Node frontend).

### Read Reference Files

Load both reference files for use throughout the audit:

1. [references/owasp-checklist.md](references/owasp-checklist.md) — category-to-check mapping
2. [references/static-patterns.md](references/static-patterns.md) — search patterns per stack

### Determine Scan Targets

Based on the mode:

- **Path mode**: Glob for code files under the given path. Exclude: `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `Generated/`, `*.g.cs`, `*.Designer.cs`, `vendor/`, `.git/`, `__pycache__/`, `*.min.js`, `*.bundle.js`.
- **Diff mode**: Use the git-changed file list, applying the same exclusions.
- **Deps mode**: No file targets needed.
- **No argument**: Glob from repository root with the same exclusions.

### Initialize Tracking

Create an in-memory findings list:
```
findings = [] // { category, severity, check_id, check_name, detail, file, line }
```

## Phase 2: Static Code Analysis

**Skip this phase if mode is `--deps`.**

For each detected tech stack, run the patterns from `static-patterns.md`. Only run patterns that match detected stacks. Universal patterns run for all stacks.

### 2.1: Run Pattern Scans

For each pattern in the reference:

1. Run `rg` with the specified regex and glob filter against the scan targets.
2. If the pattern is marked `context: true`, read 5–10 surrounding lines for each match to determine if it's a true positive.
3. Record confirmed findings with file path, line number, OWASP category, severity, and detail.

### 2.2: Context-Aware Confirmation

Many patterns produce false positives without context. For patterns marked `context: true`:

- **SQL injection**: Check if the string concatenation is actually in a query context, not a log message or display string. Look for `SqlCommand`, `ExecuteSql`, `query(`, `execute(` nearby.
- **Hardcoded secrets**: Verify the value isn't a placeholder (`"changeme"`, `"TODO"`, example values). Check if it's in a test file (lower severity).
- **Weak crypto (MD5/SHA1)**: Check if used for password hashing (CRITICAL) vs. checksums/cache keys (not a finding).
- **Missing auth attributes**: Check if the controller/action is intentionally public (e.g., `[AllowAnonymous]`, health checks, login endpoints).
- **Eval/exec**: Check if the argument is a hardcoded string (lower risk) vs. user-controlled input (CRITICAL).

### 2.3: Exclude Patterns

Skip findings in:
- Test files (`*Test*.cs`, `*.test.ts`, `*.spec.ts`, `*_test.go`, `test_*.py`) — lower severity, note separately
- Generated code (`*.g.cs`, `*.Designer.cs`, `Generated/`)
- Configuration examples (`*.example`, `*.sample`, `appsettings.Development.json`)
- Comments and documentation

## Phase 3: Dependency Audit

**Skip this phase if mode is `--diff`** — a diff scan is about the changed lines, not the whole dependency tree. Run it in path mode, `--deps` mode, and no-argument mode.

Run available dependency audit tools. Only use tools already installed — do not install new tools.

### 3.1: .NET Dependencies

If .NET detected:
```
dotnet list package --vulnerable --include-transitive
```
Parse output for any vulnerable packages. Map to **A06: Vulnerable and Outdated Components**.

### 3.2: Node Dependencies

If Node detected:
```
npm audit --json
```
Parse the JSON output. Map to **A06**. Record severity from npm's own classification.

### 3.3: Python Dependencies

If Python detected, try in order:
```
pip-audit --format json
```
or:
```
safety check --json
```
Use whichever is available. Map to **A06**.

### 3.4: Record Gaps

If a tool is not installed, note it in the report as a gap:
> "Dependency audit for {stack} skipped — `{tool}` not installed."

## Phase 5: Report Generation

After all applicable phases complete, compile findings into a markdown report. Display the report directly to the user (no file output).

### Report Format

```markdown
# OWASP Top 10 Security Audit Report

**Date:** {YYYY-MM-DD}  |  **Mode:** {path/diff/app/full}  |  **Result:** {PASS or FAIL}

## Summary

| OWASP Category | CRITICAL | HIGH | MEDIUM | LOW |
|----------------|----------|------|--------|-----|
| A01: Broken Access Control | {n} | {n} | {n} | {n} |
| A02: Cryptographic Failures | {n} | {n} | {n} | {n} |
| A03: Injection | {n} | {n} | {n} | {n} |
| A04: Insecure Design | {n} | {n} | {n} | {n} |
| A05: Security Misconfiguration | {n} | {n} | {n} | {n} |
| A06: Vulnerable Components | {n} | {n} | {n} | {n} |
| A07: Auth Failures | {n} | {n} | {n} | {n} |
| A08: Data Integrity Failures | {n} | {n} | {n} | {n} |
| A09: Logging & Monitoring | {n} | {n} | {n} | {n} |
| A10: SSRF | {n} | {n} | {n} | {n} |
| **Total** | **{n}** | **{n}** | **{n}** | **{n}** |

---

## Static Analysis Findings

### CRITICAL
- **[A{XX}]** {check name} — {detail} (`{file}:{line}`)

### HIGH
- **[A{XX}]** {check name} — {detail} (`{file}:{line}`)

### MEDIUM
- **[A{XX}]** {check name} — {detail} (`{file}:{line}`)

### LOW
- **[A{XX}]** {check name} — {detail} (`{file}:{line}`)

---

## Dependency Audit

| Package | Current Version | Vulnerability | Severity | Advisory |
|---------|----------------|---------------|----------|----------|
| {name} | {version} | {CVE/description} | {severity} | {link} |

{Or "No vulnerable dependencies found." or "Skipped — tool not installed."}

---

## Recommendations

{3-5 prioritized recommendations for the most impactful security improvements}

---

## Scope & Limitations

This audit covers automated checks against the OWASP Top 10 (2021). The following require manual review:
- Business logic flaws (A04: Insecure Design)
- Complex authentication/authorization flows
- Race conditions and timing attacks
- Server-side configuration beyond what's observable from headers
- Third-party integrations and API security
- Penetration testing and fuzzing
```

### Severity Definitions

- **CRITICAL**: Actively exploitable vulnerability. Injection, auth bypass, exposed secrets. (Determines PASS/FAIL)
- **HIGH**: Significant security risk requiring remediation. Missing auth, weak crypto, SSRF potential.
- **MEDIUM**: Security concern with mitigating factors. Missing headers, verbose errors, weak validation.
- **LOW**: Best practice deviation with minimal risk. Informational logging gaps, missing optional headers.

### Pass/Fail Determination

- **PASS** = Zero CRITICAL findings across all phases
- **FAIL** = One or more CRITICAL findings

## Phase 6: Cleanup

Print a summary line:
```
Audited {N} files, {M} dependencies. Found {C} critical, {H} high, {M} medium, {L} low. Result: {PASS/FAIL}
```

## Important Notes

- **No false positives**: Use context-aware analysis. If unsure, note it as an observation in Recommendations rather than counting it as a finding.
- **Generated code**: Skip `*.g.cs`, `Generated/`, `node_modules/`, etc. Findings in generated code are not actionable.
- **Test files**: Findings in test files are noted separately at lower severity — test code is not production attack surface.
- **Dependency tools**: Only run what's already installed. Note gaps for tools that aren't available.
- **Scope**: This audit covers automatable OWASP Top 10 checks. Note in the report footer that manual review is still needed for business logic, complex auth flows, and other checks requiring human judgment.
