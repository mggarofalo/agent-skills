---
name: owasp-top-10
description: >
  Audit codebases and running applications against the OWASP Top 10 (2021).
  Static code analysis, dependency scanning, and runtime browser testing.
  Reports findings by severity with OWASP category references.
allowed-tools: Bash, Read, Grep, Glob, mcp__aspire__list_resources, mcp__aspire__list_console_logs
user_invocable: true
argument: "<path|--diff|--app <url>|--full>"
---

# OWASP Top 10 Security Audit

Audit codebases and running applications against the OWASP Top 10 (2021) using static code analysis, dependency scanning, and agent-browser runtime testing. Reports findings by severity (CRITICAL/HIGH/MEDIUM/LOW) with OWASP category references.

## Usage

- `/owasp-top-10 <path>` — Static scan of specific files or directories
- `/owasp-top-10 --diff` — Scan only git-changed files (staged + unstaged)
- `/owasp-top-10 --app <url>` — Runtime testing only against a running application
- `/owasp-top-10 --full` — Static + dependency + runtime (full audit)

## Phase 1: Setup & Target Resolution

### Parse Arguments

Parse the argument string to determine audit mode:

1. **Path** (does not start with `--`): Static scan of that path. Can be a file or directory.
2. **`--diff`**: Run `git diff --name-only HEAD` and `git diff --name-only --cached` to get changed files. Filter to code files only (exclude images, binaries, lock files). Static scan those files.
3. **`--app <url>`**: Skip static analysis, run runtime checks against the given URL.
4. **`--full`**: Run all three phases — static, dependency, and runtime. For runtime, discover the app URL via Aspire or ask the user.

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

Load the three reference files for use throughout the audit:

1. `~/.claude/skills/owasp-top-10/references/owasp-checklist.md` — Category-to-check mapping
2. `~/.claude/skills/owasp-top-10/references/static-patterns.md` — Grep patterns per stack
3. `~/.claude/skills/owasp-top-10/references/runtime-checks.md` — agent-browser commands

### Determine Scan Targets

Based on the mode:

- **Path mode**: Glob for code files under the given path. Exclude: `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `Generated/`, `*.g.cs`, `*.Designer.cs`, `vendor/`, `.git/`, `__pycache__/`, `*.min.js`, `*.bundle.js`.
- **Diff mode**: Use the git-changed file list, applying the same exclusions.
- **App mode**: No file targets needed.
- **Full mode**: Glob from repository root with exclusions, plus runtime targets.

### Discover App URL (for `--app` and `--full` modes)

1. Use `mcp__aspire__list_resources` to check for running Aspire resources.
2. If Aspire is running, use `mcp__aspire__list_console_logs` to find the actual frontend port (Aspire assigns random ports — never assume defaults).
3. If no Aspire: check for common dev server configs, or ask the user for the URL.

### Initialize Tracking

Create an in-memory findings list:
```
findings = [] // { category, severity, check_id, check_name, detail, file, line }
```

## Phase 2: Static Code Analysis

**Skip this phase if mode is `--app`.**

For each detected tech stack, run the patterns from `static-patterns.md`. Only run patterns that match detected stacks. Universal patterns run for all stacks.

### 2.1: Run Pattern Scans

For each pattern in the reference:

1. Run the Grep tool with the specified regex and glob filter against the scan targets.
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

**Skip this phase if mode is `--app`.**

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

## Phase 4: Runtime Testing

**Skip this phase if mode is `<path>` or `--diff`.**

For the target URL, perform runtime security checks using agent-browser. Each command MUST be a separate Bash tool call (no `&&` chaining — hooks will reject it). All screenshots go to `$TEMP`.

### 4.1: Open the Target

```
agent-browser open <url>
```

Wait for the page to load:
```
sleep 3
```

Take a baseline screenshot:
```
agent-browser screenshot "$TEMP/owasp-baseline.png"
```

Read the screenshot to verify the page loaded.

### 4.2: Security Headers Check

Fetch the page headers using JavaScript:
```
agent-browser eval "fetch(window.location.href).then(r => Object.fromEntries(r.headers)).then(h => JSON.stringify(h))"
```

Check for the presence and values of security headers. Refer to `runtime-checks.md` for the full header list and evaluation criteria. Key headers:

| Header | Missing = | OWASP Category |
|--------|-----------|----------------|
| `Strict-Transport-Security` | HIGH | A05 |
| `Content-Security-Policy` | HIGH | A05 |
| `X-Content-Type-Options` | MEDIUM | A05 |
| `X-Frame-Options` or CSP `frame-ancestors` | MEDIUM | A05 |
| `Referrer-Policy` | LOW | A05 |
| `Permissions-Policy` | LOW | A05 |

### 4.3: Cookie Security Check

Inspect cookie attributes:
```
agent-browser eval "document.cookie"
```

Check each cookie for:
- `HttpOnly` flag (if sensitive) — not visible via `document.cookie` means it IS HttpOnly
- `Secure` flag — MEDIUM if missing on auth cookies
- `SameSite` attribute — MEDIUM if missing

Note: Cookies visible to `document.cookie` are NOT HttpOnly. Auth/session cookies that are visible = HIGH finding.

### 4.4: Web Storage Inspection

Check for sensitive data in localStorage and sessionStorage:
```
agent-browser eval "JSON.stringify(localStorage)"
```
```
agent-browser eval "JSON.stringify(sessionStorage)"
```

Flag as HIGH if tokens, passwords, PII, or API keys are found in web storage. Map to **A02: Cryptographic Failures** (sensitive data exposure).

### 4.5: XSS Testing

If the page has form inputs, test common XSS payloads:

1. Take a snapshot to find form fields:
   ```
   agent-browser snapshot -i
   ```

2. For each text input field, try injecting a test payload:
   ```
   agent-browser fill @<element-ref> "<img src=x onerror=alert(1)>"
   ```

3. Submit the form if possible, then check if the payload appears unescaped:
   ```
   agent-browser snapshot
   ```

4. Check for the payload in the DOM:
   ```
   agent-browser eval "document.body.innerHTML.includes('<img src=x onerror')"
   ```

Flag unescaped payloads as CRITICAL (A03: Injection / XSS).

### 4.6: Open Redirect Testing

If the URL has redirect-like parameters (`redirect`, `return`, `next`, `url`, `goto`, `dest`):

```
agent-browser open "<base-url>?redirect=https://evil.example.com"
```

After navigation, check the resulting URL:
```
agent-browser get url
```

If the browser navigated to `evil.example.com`, flag as HIGH (A01: Broken Access Control).

### 4.7: Console and Error Inspection

Check for security-relevant console output:
```
agent-browser errors
```
```
agent-browser console
```

Look for:
- CSP violations → informational (confirms CSP is working)
- Mixed content warnings → MEDIUM (A05)
- CORS errors that indicate misconfiguration → MEDIUM (A05)
- Logged secrets, tokens, or stack traces → HIGH (A09)

### 4.8: Inline Script Detection

Check for inline scripts without CSP nonces:
```
agent-browser eval "document.querySelectorAll('script:not([src]):not([nonce])').length"
```

If count > 0 and no CSP header is set, flag as MEDIUM (A05: Security Misconfiguration).

### 4.9: CSRF Token Presence

For each form on the page:
```
agent-browser eval "Array.from(document.forms).map(f => ({action: f.action, method: f.method, hasToken: !!f.querySelector('input[name*=token],input[name*=csrf],input[name*=__RequestVerificationToken]')}))"
```

Flag POST forms without CSRF tokens as HIGH (A01: Broken Access Control), unless the form uses a non-standard CSRF mechanism (check for custom headers in fetch interceptors).

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

## Runtime Testing Results

**Target:** {url}

### Security Headers
| Header | Status | Finding |
|--------|--------|---------|
| {name} | Present/Missing | {detail} |

### Cookie Security
{findings or "No insecure cookies detected."}

### XSS Testing
{findings or "No XSS vulnerabilities detected."}

### Additional Runtime Checks
{CSRF, open redirect, console errors, web storage findings}

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

1. If runtime testing was performed, close agent-browser:
   ```
   agent-browser close
   ```

2. Print a summary line:
   ```
   Audited {N} files, {M} dependencies, {P} runtime checks. Found {C} critical, {H} high, {M} medium, {L} low. Result: {PASS/FAIL}
   ```

## Important Notes

- **Hook compliance**: Every `agent-browser` command MUST be a separate Bash tool call. Never chain with `&&`, `||`, or `;`.
- **Screenshots**: Always save to `$TEMP`, never to the working directory.
- **Aspire ports**: Never assume port numbers. Always check `list_console_logs` for the actual port.
- **No false positives**: Use context-aware analysis. If unsure, note it as an observation in Recommendations rather than counting it as a finding.
- **Generated code**: Skip `*.g.cs`, `Generated/`, `node_modules/`, etc. Findings in generated code are not actionable.
- **Test files**: Findings in test files are noted separately at lower severity — test code is not production attack surface.
- **Dependency tools**: Only run what's already installed. Note gaps for tools that aren't available.
- **Scope**: This audit covers automatable OWASP Top 10 checks. Note in the report footer that manual review is still needed for business logic, complex auth flows, and other checks requiring human judgment.
