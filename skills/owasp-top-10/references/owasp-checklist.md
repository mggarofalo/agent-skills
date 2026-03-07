# OWASP Top 10 (2021) Audit Checklist

Checks organized by OWASP category. Each check indicates the audit method (Static, Dependency, Runtime, Manual) and applicable tech stacks.

## A01: Broken Access Control

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A01-01 | Missing auth on controllers | HIGH | Static | .NET | Controller class without `[Authorize]` or `[AllowAnonymous]` attribute |
| A01-02 | Missing auth on API routes | HIGH | Static | Node | Express/Fastify route handlers without auth middleware |
| A01-03 | IDOR via direct object reference | HIGH | Static | Universal | Database queries using user-supplied ID without ownership check |
| A01-04 | Open redirect | HIGH | Runtime | Universal | Redirect parameters that accept external URLs |
| A01-05 | CORS wildcard | MEDIUM | Static | Universal | `Access-Control-Allow-Origin: *` with credentials |
| A01-06 | Missing CSRF tokens | HIGH | Runtime | Universal | POST forms without anti-forgery tokens |
| A01-07 | Directory traversal | CRITICAL | Static | Universal | File path constructed from user input without sanitization |
| A01-08 | Privilege escalation paths | HIGH | Static | Universal | Role checks that can be bypassed (client-side only checks) |
| A01-09 | Missing rate limiting | MEDIUM | Static | Universal | Auth endpoints without rate limiting middleware |
| A01-10 | Insecure direct file access | HIGH | Static | Universal | Static files served from user-controllable paths |

## A02: Cryptographic Failures

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A02-01 | Hardcoded secrets | CRITICAL | Static | Universal | API keys, passwords, tokens, PEM keys in source code |
| A02-02 | Weak password hashing | CRITICAL | Static | Universal | MD5/SHA1/SHA256 used for password hashing (not bcrypt/scrypt/argon2) |
| A02-03 | Sensitive data in web storage | HIGH | Runtime | Universal | Tokens, passwords, PII in localStorage/sessionStorage |
| A02-04 | Missing HTTPS enforcement | HIGH | Runtime | Universal | No HSTS header or `Secure` flag on cookies |
| A02-05 | Weak TLS configuration | MEDIUM | Static | Universal | TLS 1.0/1.1 enabled, weak cipher suites |
| A02-06 | Sensitive data in URLs | MEDIUM | Static | Universal | Tokens or credentials passed as query parameters |
| A02-07 | Unencrypted sensitive storage | HIGH | Static | Universal | PII or credentials stored in plaintext in database/config |
| A02-08 | Weak random number generation | HIGH | Static | Universal | `Math.random()`, `Random()` used for security tokens |
| A02-09 | Missing encryption at rest | MEDIUM | Static | .NET | Connection strings without `Encrypt=true` |
| A02-10 | Exposed .env files | CRITICAL | Static | Universal | `.env` files committed to git or accessible via web |

## A03: Injection

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A03-01 | SQL injection (concatenation) | CRITICAL | Static | Universal | String concatenation/interpolation in SQL queries |
| A03-02 | SQL injection (raw queries) | HIGH | Static | Universal | Raw SQL with user input not using parameterized queries |
| A03-03 | NoSQL injection | HIGH | Static | Node | Unsanitized user input in MongoDB/NoSQL queries |
| A03-04 | OS command injection | CRITICAL | Static | Universal | User input in `Process.Start`, `exec()`, `system()`, backticks |
| A03-05 | XSS (DOM sinks) | CRITICAL | Static | JS/TS | `innerHTML`, `outerHTML`, `document.write`, `eval()` with user data |
| A03-06 | XSS (React unsafe) | CRITICAL | Static | JS/TS | `dangerouslySetInnerHTML` with user-controlled content |
| A03-07 | XSS (.NET Html.Raw) | CRITICAL | Static | .NET | `Html.Raw()` with user-controlled content |
| A03-08 | XSS (reflected) | CRITICAL | Runtime | Universal | Injected payload rendered unescaped in page |
| A03-09 | LDAP injection | HIGH | Static | Universal | User input in LDAP queries without escaping |
| A03-10 | Template injection | CRITICAL | Static | Universal | User input in template rendering (`eval`, template literals with user data) |
| A03-11 | Header injection | HIGH | Static | Universal | User input in HTTP response headers (CRLF injection) |
| A03-12 | Log injection | MEDIUM | Static | Universal | Unsanitized user input written to logs |

## A04: Insecure Design

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A04-01 | Missing input validation | MEDIUM | Static | Universal | API endpoints accepting user input without validation/schema |
| A04-02 | Missing output encoding | MEDIUM | Static | Universal | User data rendered without context-appropriate encoding |
| A04-03 | Client-side auth checks only | HIGH | Static | JS/TS | Authorization decisions made only in frontend code |
| A04-04 | Excessive data exposure | MEDIUM | Static | Universal | API responses returning more fields than the client needs |
| A04-05 | Missing account lockout | MEDIUM | Manual | Universal | No lockout after N failed authentication attempts |

## A05: Security Misconfiguration

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A05-01 | Debug mode in production | HIGH | Static | Universal | Debug/development mode flags not disabled for production |
| A05-02 | Developer exception page | CRITICAL | Static | .NET | `UseDeveloperExceptionPage()` without environment check |
| A05-03 | Detailed error messages | MEDIUM | Static | Universal | Stack traces or internal details in error responses |
| A05-04 | Missing security headers | MEDIUM | Runtime | Universal | Missing CSP, X-Content-Type-Options, X-Frame-Options |
| A05-05 | CORS misconfiguration | HIGH | Static | Universal | Overly permissive CORS (wildcard origin with credentials) |
| A05-06 | Default credentials | CRITICAL | Static | Universal | Default passwords, admin/admin, test credentials in config |
| A05-07 | Unnecessary features enabled | MEDIUM | Static | Universal | Swagger/debug endpoints accessible in production |
| A05-08 | Missing HSTS | HIGH | Runtime | Universal | No `Strict-Transport-Security` header |
| A05-09 | Inline scripts without CSP | MEDIUM | Runtime | Universal | Inline `<script>` tags without CSP nonces |
| A05-10 | Mixed content | MEDIUM | Runtime | Universal | HTTP resources loaded on HTTPS pages |
| A05-11 | Directory listing enabled | MEDIUM | Static | Universal | Static file serving configured to allow directory browsing |
| A05-12 | Verbose server header | LOW | Runtime | Universal | Server header revealing technology and version |

## A06: Vulnerable and Outdated Components

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A06-01 | Vulnerable NuGet packages | varies | Dependency | .NET | `dotnet list package --vulnerable` reports findings |
| A06-02 | Vulnerable npm packages | varies | Dependency | Node | `npm audit` reports findings |
| A06-03 | Vulnerable Python packages | varies | Dependency | Python | `pip-audit` or `safety check` reports findings |
| A06-04 | Outdated framework version | MEDIUM | Static | Universal | Framework version past end-of-support |
| A06-05 | Pinned vulnerable version | HIGH | Static | Universal | Package version pinned to a known-vulnerable version |

## A07: Identification and Authentication Failures

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A07-01 | Plaintext password storage | CRITICAL | Static | Universal | Passwords stored without hashing |
| A07-02 | Weak password policy | MEDIUM | Static | Universal | No minimum length/complexity requirements enforced |
| A07-03 | Missing session timeout | MEDIUM | Static | Universal | Sessions without expiration or sliding expiration too long |
| A07-04 | Session fixation | HIGH | Static | Universal | Session ID not regenerated after authentication |
| A07-05 | Credential stuffing exposure | MEDIUM | Static | Universal | Login endpoint without rate limiting or CAPTCHA |
| A07-06 | Insecure password reset | HIGH | Static | Universal | Password reset tokens that don't expire or are predictable |
| A07-07 | JWT validation gaps | HIGH | Static | Universal | JWT tokens accepted without signature verification or with `none` algorithm |
| A07-08 | Missing cookie security | HIGH | Runtime | Universal | Auth cookies without `HttpOnly`, `Secure`, `SameSite` flags |

## A08: Software and Data Integrity Failures

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A08-01 | Insecure deserialization (.NET) | CRITICAL | Static | .NET | `BinaryFormatter`, `NetDataContractSerializer`, `ObjectStateFormatter` usage |
| A08-02 | Insecure deserialization (Python) | CRITICAL | Static | Python | `pickle.loads()`, `yaml.load()` without `SafeLoader` |
| A08-03 | Insecure deserialization (Node) | HIGH | Static | Node | `node-serialize`, `funcster` usage |
| A08-04 | Missing integrity checks | MEDIUM | Static | Universal | CDN resources loaded without `integrity` attribute (SRI) |
| A08-05 | Unsigned updates | HIGH | Static | Universal | Auto-update mechanisms without signature verification |
| A08-06 | CI/CD pipeline vulnerabilities | MEDIUM | Static | Universal | Pipeline configs with hardcoded secrets or insecure steps |

## A09: Security Logging and Monitoring Failures

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A09-01 | Missing auth event logging | MEDIUM | Static | Universal | Login/logout/failure events not logged |
| A09-02 | Missing access control logging | MEDIUM | Static | Universal | Authorization failures not logged |
| A09-03 | Sensitive data in logs | HIGH | Static | Universal | Passwords, tokens, PII written to logs |
| A09-04 | Console secrets in browser | HIGH | Runtime | Universal | Secrets, tokens, or stack traces in browser console output |
| A09-05 | Missing audit trail | LOW | Static | Universal | Data modification operations without audit logging |
| A09-06 | Log injection vulnerability | MEDIUM | Static | Universal | User input written to logs without sanitization |

## A10: Server-Side Request Forgery (SSRF)

| Check ID | Check Name | Severity | Method | Stack | What Triggers a Finding |
|----------|-----------|----------|--------|-------|------------------------|
| A10-01 | URL from user input | HIGH | Static | Universal | User-supplied URLs passed to HTTP client without allowlist |
| A10-02 | Internal network access | CRITICAL | Static | Universal | User input that could reach internal IPs (127.0.0.1, 10.x, 192.168.x) |
| A10-03 | Cloud metadata access | CRITICAL | Static | Universal | Potential access to cloud metadata endpoints (169.254.169.254) |
| A10-04 | File URL schemes | HIGH | Static | Universal | `file://`, `gopher://`, `dict://` schemes not blocked |
| A10-05 | DNS rebinding exposure | MEDIUM | Static | Universal | URL validation only at request time, not at connection time |

## Method Legend

| Method | Description |
|--------|-------------|
| **Static** | Grep/read patterns in source code |
| **Dependency** | Package vulnerability scanning tools |
| **Runtime** | agent-browser inspection of running application |
| **Manual** | Requires human judgment — noted in report but not auto-checked |
