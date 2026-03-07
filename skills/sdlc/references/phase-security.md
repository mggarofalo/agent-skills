# Phase 4: Security Analyst

## Purpose

Perform threat modeling and security analysis of the implementation. This phase identifies security vulnerabilities, attack surfaces, and compliance gaps before code reaches production.

## Inputs

- The plan from Phase 1 (what the feature does and why)
- Implementation details from Phase 2 (what changed)
- Review results from Phase 3 (any security-adjacent findings)
- Project context (tech stack, dependencies)

## Steps

### 1. Build a Threat Model

Based on the changes, identify:

#### Attack Surfaces
- New API endpoints or modified request handlers
- New user inputs (forms, query params, headers, file uploads)
- New data storage (database tables, files, cache entries)
- New external integrations (third-party APIs, services)
- Modified authentication/authorization paths

#### Data Flows
- Trace data from entry point through processing to storage/output
- Identify where data crosses trust boundaries
- Map where sensitive data (PII, credentials, tokens) flows

#### Trust Boundaries
- Client ↔ Server
- Server ↔ Database
- Server ↔ External Service
- User-supplied data ↔ Internal processing

### 2. Security Review

For each attack surface, check against:

#### OWASP Top 10
- **Injection:** SQL, NoSQL, OS command, LDAP injection in any user input handling
- **Broken Authentication:** Weak session management, credential handling, token validation
- **Sensitive Data Exposure:** Logging PII, unencrypted storage, data in URLs, verbose error messages
- **XML External Entities:** XXE in XML parsing
- **Broken Access Control:** Missing authorization checks, IDOR, privilege escalation
- **Security Misconfiguration:** Debug modes, default credentials, unnecessary features enabled
- **XSS:** Reflected, stored, or DOM-based cross-site scripting
- **Insecure Deserialization:** Untrusted data deserialization
- **Known Vulnerabilities:** Dependencies with known CVEs
- **Insufficient Logging:** Missing audit trails for security-relevant actions

#### Code-Level Checks
- **Secrets in code:** API keys, passwords, tokens, connection strings hardcoded or in config files committed to git
- **Input validation:** All user input validated at system boundaries, parameterized queries used
- **Output encoding:** Proper encoding for the output context (HTML, JSON, SQL, URL)
- **Authentication:** Proper password hashing, secure session handling, MFA considerations
- **Authorization:** Principle of least privilege, role-based access control
- **Cryptography:** Strong algorithms, proper key management, no custom crypto
- **Error handling:** No stack traces or internal details leaked to users
- **Dependencies:** No known vulnerable versions

### 3. Client-Side Security Testing (If Applicable)

Read `~/.claude/skills/sdlc/references/browser-testing.md` for full `agent-browser` usage.

**Determine applicability:** If the changes involve user-facing UI, client-side JavaScript, form handling, URL routing, or any code that renders user-controlled data in the browser — client-side security testing applies.

**When applicable:**
1. Start the project's dev server in the background
2. Navigate to pages affected by the changes
3. Test for client-side vulnerabilities:

   **XSS Testing:**
   - If the feature renders user input, attempt to inject common XSS payloads via form fields:
     `agent-browser fill @e1 "<script>alert(1)</script>"` then submit and check if the script tag appears unescaped in the DOM via `agent-browser snapshot`
   - Check for reflected XSS by navigating with payloads in query params
   - Verify output encoding by inspecting rendered HTML: `agent-browser get html "<selector>"`

   **Open Redirect Testing:**
   - If the feature handles redirects (login, OAuth, return URLs), test with external URLs in redirect parameters
   - `agent-browser open "http://localhost:3000/login?redirect=https://evil.com"` then check `agent-browser get url` after the flow

   **Sensitive Data Exposure in DOM:**
   - After authenticating or loading a page with sensitive data, inspect the DOM for tokens, keys, or PII that shouldn't be client-visible
   - `agent-browser snapshot` and search the output for sensitive patterns
   - Check `agent-browser eval "JSON.stringify(localStorage)"` and `agent-browser eval "JSON.stringify(sessionStorage)"` for sensitive data in web storage

   **Console Errors:**
   - `agent-browser errors` — check for security-relevant errors (CORS, CSP violations, mixed content)
   - `agent-browser console` — check for logged secrets or sensitive data

4. Record findings under a `### Client-Side Security` subsection
5. Close the browser: `agent-browser close`
6. Stop the dev server

### 4. Run Available Security Tooling

Check for and run any available security tools:
- `dotnet format` — for .NET projects
- `npm audit` — for Node projects
- `pip audit` or `safety check` — for Python projects
- `snyk test` — if Snyk is configured
- Custom security scripts defined in AGENTS.md

Only run tools that are already installed/configured. Don't install new tools.

### 5. Categorize Findings

- **CRITICAL:** Actively exploitable vulnerability. Injection, authentication bypass, privilege escalation, exposed secrets.
- **HIGH:** Significant security risk requiring remediation. Missing authorization, weak crypto, SSRF potential.
- **MEDIUM:** Security concern with mitigating factors. Missing rate limiting, verbose errors, weak input validation on internal APIs.
- **LOW:** Best practice deviation with minimal risk. Missing security headers on internal endpoints, informational logging gaps.

### 6. Write Security Assessment

Append to state file:

```markdown
## Phase 4: Security
**Status:** pass (or fail)

### Threat Model
**Attack Surfaces:** <N identified>
<brief list of surfaces>

**Data Flows:**
<key data flows through changed code>

**Trust Boundaries Crossed:**
<list of boundary crossings>

### Findings

#### CRITICAL
- [<file>:<line>] <vulnerability description, attack scenario, and remediation>

#### HIGH
- [<file>:<line>] <description and remediation>

#### MEDIUM
- [<file>:<line>] <description>

#### LOW
- [<file>:<line>] <description>

### Client-Side Security
**Applicable:** yes/no
**Pages Tested:** <list>
**Findings:** <any client-side vulnerabilities found>

### Security Tooling
- <tool>: <result summary>

**Summary:** <overall security assessment in 1-2 sentences>
```

## Pass/Fail Criteria

- **Pass:** No CRITICAL or HIGH findings
- **Fail:** One or more CRITICAL or HIGH findings exist

## On Failure

When this phase fails, the orchestrator will:
1. Extract the CRITICAL and HIGH findings with full context (threat model + code locations)
2. Route them to the Implementer phase for remediation
3. The Implementer will apply security fixes
4. This Security phase will re-run to verify the fixes

The re-run should:
- Re-evaluate the full threat model (fixes may have changed attack surfaces)
- Verify each previous CRITICAL/HIGH finding is resolved
- Check that fixes didn't introduce new security issues
- Append re-assessment results to the state file
