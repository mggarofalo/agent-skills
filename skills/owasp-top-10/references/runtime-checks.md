# Runtime Security Checks

Exact agent-browser commands for each runtime check, evaluation criteria, and finding categorization. Every command MUST be a separate Bash tool call (hook compliance — no `&&`, `||`, or `;` chaining).

## Prerequisites

- agent-browser must be available on PATH
- Screenshots always go to `$TEMP` (never the working directory)
- Each command below is a **separate** Bash tool call

## RT-01: Page Load & Baseline

**Open the target page:**
```
agent-browser open <url>
```

**Wait for load:**
```
sleep 3
```

**Take baseline screenshot:**
```
agent-browser screenshot "$TEMP/owasp-baseline.png"
```

Read the screenshot to verify the page loaded correctly before proceeding.

## RT-02: Security Headers

**Fetch headers via JavaScript:**
```
agent-browser eval "fetch(window.location.href, {method: 'HEAD'}).then(r => JSON.stringify(Object.fromEntries(r.headers)))"
```

**Note:** The `fetch()` approach only sees headers the browser exposes to JS. Some headers (like `Set-Cookie`) are filtered. This covers the most important security headers.

### Evaluation Criteria

| Header | Expected | Missing/Bad = | OWASP | Notes |
|--------|----------|---------------|-------|-------|
| `strict-transport-security` | Present with `max-age >= 31536000` | HIGH (A05-08) | A05 | Should include `includeSubDomains` |
| `content-security-policy` | Present, not empty | HIGH (A05-04) | A05 | Check for `unsafe-inline`, `unsafe-eval` (degrades to MEDIUM if present) |
| `x-content-type-options` | `nosniff` | MEDIUM (A05-04) | A05 | Prevents MIME-type sniffing |
| `x-frame-options` | `DENY` or `SAMEORIGIN` | MEDIUM (A05-04) | A05 | Or CSP `frame-ancestors` directive |
| `referrer-policy` | Present (any non-empty value) | LOW (A05-04) | A05 | `no-referrer` or `strict-origin-when-cross-origin` preferred |
| `permissions-policy` | Present | LOW (A05-04) | A05 | Controls browser feature access |
| `x-powered-by` | Absent | LOW (A05-12) | A05 | Reveals server technology |
| `server` | Absent or generic | LOW (A05-12) | A05 | Should not reveal version info |

### CSP Deep Check

If CSP header is present, evaluate its directives:

| Directive Issue | Severity | Detail |
|----------------|----------|--------|
| `unsafe-inline` in `script-src` | MEDIUM | Allows inline scripts, weakens XSS protection |
| `unsafe-eval` in `script-src` | MEDIUM | Allows `eval()`, weakens XSS protection |
| `*` in `default-src` or `script-src` | HIGH | Wildcard allows scripts from any origin |
| `data:` in `script-src` | MEDIUM | Allows data URI scripts |
| Missing `default-src` | MEDIUM | No fallback policy for unlisted resource types |

## RT-03: Cookie Security

**Check cookies visible to JavaScript:**
```
agent-browser eval "document.cookie"
```

### Evaluation Criteria

- Cookies returned by `document.cookie` are **NOT** HttpOnly (the HttpOnly flag prevents JS access)
- If any cookie name contains `session`, `auth`, `token`, `jwt`, `sid`, or `identity` and IS visible → **HIGH (A07-08)** — auth cookie missing HttpOnly
- For all cookies, we can only check what's visible to JS. Server-set HttpOnly cookies are invisible here (which is good).

**Check cookie attributes via network (if possible):**
```
agent-browser eval "document.cookie.split(';').map(c => c.trim()).filter(c => c.length > 0).map(c => ({name: c.split('=')[0], value: c.split('=').slice(1).join('=')}))"
```

### Cookie Findings

| Condition | Severity | OWASP | Check ID |
|-----------|----------|-------|----------|
| Auth/session cookie visible to JS (not HttpOnly) | HIGH | A07 | A07-08 |
| Cookie on HTTPS page without `Secure` flag (inferred if site is HTTPS but cookie lacks `Secure`) | MEDIUM | A02 | A02-04 |
| No `SameSite` attribute on auth cookies | MEDIUM | A01 | A01-06 |

## RT-04: Web Storage Inspection

**Check localStorage:**
```
agent-browser eval "JSON.stringify(localStorage)"
```

**Check sessionStorage:**
```
agent-browser eval "JSON.stringify(sessionStorage)"
```

### Evaluation Criteria

Scan the JSON output for sensitive data patterns:

| Pattern | What It Indicates | Severity | OWASP |
|---------|------------------|----------|-------|
| `token`, `jwt`, `access_token`, `refresh_token`, `id_token` | Auth tokens in web storage | HIGH (A02-03) | A02 |
| `password`, `passwd`, `pwd`, `secret` | Credentials in web storage | CRITICAL (A02-03) | A02 |
| `ssn`, `social_security`, `credit_card`, `cc_number` | PII in web storage | HIGH (A02-03) | A02 |
| `api_key`, `apikey`, `secret_key` | API keys in web storage | HIGH (A02-03) | A02 |
| Base64-encoded JWT (starts with `eyJ`) | JWT token in web storage | HIGH (A02-03) | A02 |

**Note:** Some frameworks intentionally store auth tokens in localStorage (e.g., SPAs with JWT). This is still a finding because it exposes tokens to XSS. Note this nuance in the finding detail.

## RT-05: XSS Testing

**Step 1 — Find form inputs:**
```
agent-browser snapshot -i
```

Identify text input fields (`textbox`, `combobox`, `searchbox`) from the snapshot.

**Step 2 — Inject test payload into each input:**
```
agent-browser fill @<element-ref> "<img src=x onerror=alert(1)>"
```

**Step 3 — Submit the form (if a submit button exists):**
```
agent-browser click @<submit-button-ref>
```

**Step 4 — Wait and take snapshot:**
```
sleep 2
```
```
agent-browser snapshot
```

**Step 5 — Check if payload rendered unescaped:**
```
agent-browser eval "document.body.innerHTML.includes('<img src=x onerror')"
```

### Additional XSS Payloads

If the first payload doesn't trigger, try these alternatives (one per input field):

| Payload | Purpose |
|---------|---------|
| `<svg onload=alert(1)>` | SVG-based XSS |
| `javascript:alert(1)` | Protocol-based (for link/redirect fields) |
| `"><script>alert(1)</script>` | Attribute breakout |
| `{{constructor.constructor('alert(1)')()}}` | Template injection (Angular/Vue) |

### Evaluation Criteria

| Condition | Severity | OWASP | Check ID |
|-----------|----------|-------|----------|
| Payload appears unescaped in DOM | CRITICAL | A03 | A03-08 |
| Payload appears in page source but not executed | MEDIUM | A03 | A03-08 |
| All payloads properly escaped/sanitized | No finding | — | — |

## RT-06: Open Redirect Testing

**Only test if the URL has redirect-like parameters.** Check the current URL for parameters:
```
agent-browser get url
```

Look for query parameters named: `redirect`, `return`, `returnUrl`, `next`, `url`, `goto`, `dest`, `destination`, `continue`, `redir`, `target`.

**If found, test with external URL:**
```
agent-browser open "<base-url>?<param>=https://evil.example.com"
```

**Wait and check resulting URL:**
```
sleep 3
```
```
agent-browser get url
```

### Evaluation Criteria

| Condition | Severity | OWASP | Check ID |
|-----------|----------|-------|----------|
| Browser navigated to `evil.example.com` | HIGH | A01 | A01-04 |
| Browser stayed on original domain | No finding | — | — |
| Redirect parameter ignored | No finding | — | — |

Also test protocol-relative redirect:
```
agent-browser open "<base-url>?<param>=//evil.example.com"
```

## RT-07: Console and Error Inspection

**Check for errors:**
```
agent-browser errors
```

**Check console output:**
```
agent-browser console
```

### Evaluation Criteria

| Console Content | Severity | OWASP | Check ID |
|----------------|----------|-------|----------|
| CSP violation reports | Informational (positive — CSP is working) | — | — |
| Mixed content warnings | MEDIUM | A05 | A05-10 |
| CORS errors suggesting misconfiguration | MEDIUM | A05 | A05-05 |
| Stack traces with file paths or internal details | HIGH | A09 | A09-04 |
| Logged tokens, keys, or credentials | HIGH | A09 | A09-04 |
| `403`/`401` errors (normal auth flow) | No finding | — | — |
| Generic JS errors | No finding | — | — |

## RT-08: Inline Script Detection

**Count inline scripts without nonces:**
```
agent-browser eval "document.querySelectorAll('script:not([src]):not([nonce])').length"
```

**Get inline script details if count > 0:**
```
agent-browser eval "Array.from(document.querySelectorAll('script:not([src]):not([nonce])')).map(s => s.textContent.substring(0, 100))"
```

### Evaluation Criteria

| Condition | Severity | OWASP | Check ID |
|-----------|----------|-------|----------|
| Inline scripts present AND no CSP header | MEDIUM | A05 | A05-09 |
| Inline scripts present AND CSP has `unsafe-inline` | MEDIUM | A05 | A05-09 |
| Inline scripts present AND CSP uses nonce-based allowlist | No finding (properly configured) | — | — |
| No inline scripts | No finding | — | — |

## RT-09: CSRF Token Presence

**Check forms for CSRF tokens:**
```
agent-browser eval "Array.from(document.forms).map(f => ({action: f.action, method: f.method, hasToken: !!f.querySelector('input[name*=\"token\"],input[name*=\"csrf\"],input[name*=\"__RequestVerificationToken\"],input[name*=\"_token\"],input[name*=\"authenticity_token\"]')}))"
```

### Evaluation Criteria

| Condition | Severity | OWASP | Check ID |
|-----------|----------|-------|----------|
| POST/PUT/DELETE form without CSRF token | HIGH | A01 | A01-06 |
| GET form without CSRF token | No finding (GET should be idempotent) | — | — |
| Form with CSRF token present | No finding | — | — |
| No forms on page | No finding | — | — |

**Note:** SPAs using `fetch()` with auth headers (Bearer tokens) are inherently CSRF-resistant. If the app appears to be a SPA with no traditional forms, note this in the report rather than flagging as a finding.

## RT-10: Mixed Content Check

**Check for mixed content resources:**
```
agent-browser eval "performance.getEntriesByType('resource').filter(r => r.name.startsWith('http://')).map(r => r.name)"
```

### Evaluation Criteria

| Condition | Severity | OWASP | Check ID |
|-----------|----------|-------|----------|
| HTTP resources loaded on HTTPS page | MEDIUM | A05 | A05-10 |
| All resources use HTTPS | No finding | — | — |
| Page itself is HTTP | Note in report (no HTTPS) | A02 | A02-04 |

## Cleanup

After all runtime checks are complete:
```
agent-browser close
```

## Runtime Check Summary Template

Use this template for the runtime section of the report:

```markdown
## Runtime Testing Results

**Target:** {url}
**Checks Run:** {count of RT-01 through RT-10}

### Security Headers
| Header | Status | Finding |
|--------|--------|---------|
| Strict-Transport-Security | {Present/Missing} | {detail or "OK"} |
| Content-Security-Policy | {Present/Missing} | {detail or "OK"} |
| X-Content-Type-Options | {Present/Missing} | {detail or "OK"} |
| X-Frame-Options | {Present/Missing} | {detail or "OK"} |
| Referrer-Policy | {Present/Missing} | {detail or "OK"} |
| Permissions-Policy | {Present/Missing} | {detail or "OK"} |

### Cookie Security
{findings table or "No insecure cookies detected."}

### Web Storage
{findings or "No sensitive data found in web storage."}

### XSS Testing
{findings or "No XSS vulnerabilities detected in {N} form fields tested."}

### Open Redirects
{findings or "No open redirect vulnerabilities detected." or "No redirect parameters found — skipped."}

### CSRF Protection
{findings or "All POST forms include CSRF tokens." or "SPA architecture — CSRF via auth headers."}

### Console Output
{findings or "No security-relevant console output detected."}

### Inline Scripts
{findings or "No inline scripts without CSP nonces detected."}
```
