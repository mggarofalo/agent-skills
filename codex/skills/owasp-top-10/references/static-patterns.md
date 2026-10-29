# Static Analysis Patterns

Regex patterns for the Grep tool, organized by tech stack. Each pattern includes:
- **Check ID**: Reference to `owasp-checklist.md`
- **Regex**: Pattern for the Grep tool
- **Glob**: File filter for the Grep tool
- **Severity**: Finding severity if confirmed
- **Context**: Whether surrounding lines must be read to confirm (true/false)

## Excluded Paths

Always add these to exclusion when scanning:
- `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `vendor/`
- `*.g.cs`, `*.Designer.cs`, `Generated/`
- `__pycache__/`, `.git/`, `target/`
- `*.min.js`, `*.bundle.js`, `*.chunk.js`
- `*.lock`, `package-lock.json`, `yarn.lock`

## Universal Patterns

These apply to all tech stacks.

### A02: Cryptographic Failures — Hardcoded Secrets

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A02-01a | `(?i)(api[_-]?key\|apikey\|secret[_-]?key\|access[_-]?token\|auth[_-]?token)\s*[:=]\s*["'][A-Za-z0-9+/=_-]{16,}["']` | `*.{cs,ts,tsx,js,jsx,py,go,rs,rb,json,yaml,yml,toml}` | CRITICAL | true |
| A02-01b | `(?i)(password\|passwd\|pwd)\s*[:=]\s*["'][^"']{4,}["']` | `*.{cs,ts,tsx,js,jsx,py,go,rs,rb,json,yaml,yml,toml,xml,config}` | CRITICAL | true |
| A02-01c | `-----BEGIN (RSA\|EC\|DSA\|OPENSSH)? ?PRIVATE KEY-----` | `*` | CRITICAL | false |
| A02-01d | `(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}` | `*.{cs,ts,tsx,js,jsx,py,go,rs,rb}` | CRITICAL | true |
| A02-01e | `(?i)(aws_secret_access_key\|github_token\|gh[ps]_[A-Za-z0-9]{36,})\s*[:=]` | `*` | CRITICAL | false |

### A02: Weak Random Numbers

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A02-08a | `Math\.random\(\)` | `*.{ts,tsx,js,jsx}` | HIGH | true |
| A02-08b | `new Random\(\)` | `*.cs` | HIGH | true |
| A02-08c | `random\.random\(\)\|random\.randint\(` | `*.py` | HIGH | true |

### A02: Sensitive Data in URLs

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A02-06a | `(?i)(token\|key\|password\|secret\|api_key)=[^&\s]+` | `*.{cs,ts,tsx,js,jsx,py}` | MEDIUM | true |

### A03: SQL Injection

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-01a | `["']\s*\+\s*\w+.*(?i)(SELECT\|INSERT\|UPDATE\|DELETE\|FROM\|WHERE)` | `*.{cs,ts,tsx,js,jsx,py,go,rs,rb}` | CRITICAL | true |
| A03-01b | `(?i)(SELECT\|INSERT\|UPDATE\|DELETE\|FROM\|WHERE).*["']\s*\+\s*\w+` | `*.{cs,ts,tsx,js,jsx,py,go,rs,rb}` | CRITICAL | true |
| A03-01c | `` \$".*(?i)(SELECT\|INSERT\|UPDATE\|DELETE\|WHERE).*\{`` | `*.cs` | CRITICAL | true |
| A03-01d | `` `.*(?i)(SELECT\|INSERT\|UPDATE\|DELETE\|WHERE).*\$\{`` | `*.{ts,tsx,js,jsx}` | CRITICAL | true |
| A03-01e | `f["'].*(?i)(SELECT\|INSERT\|UPDATE\|DELETE\|WHERE).*\{` | `*.py` | CRITICAL | true |

### A03: OS Command Injection

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-04a | `Process\.Start\(` | `*.cs` | CRITICAL | true |
| A03-04b | `(?:child_process\|exec\|execSync\|spawn)\(` | `*.{ts,tsx,js,jsx}` | CRITICAL | true |
| A03-04c | `(?:os\.system\|os\.popen\|subprocess\.call\|subprocess\.run\|subprocess\.Popen)\(` | `*.py` | CRITICAL | true |
| A03-04d | `exec\.Command\(` | `*.go` | CRITICAL | true |

### A03: Log Injection

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-12a | `(?i)(logger?\.(info\|warn\|error\|debug\|log)\|console\.(log\|warn\|error))\(.*\+\s*(?:req\|request\|user)` | `*.{cs,ts,tsx,js,jsx,py}` | MEDIUM | true |

### A05: Debug/Development Mode

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A05-01a | `(?i)("debug"\s*:\s*true\|DEBUG\s*=\s*True\|debug:\s*true)` | `*.{json,yaml,yml,py,toml,config}` | HIGH | true |
| A05-06a | `(?i)(admin\|root\|test)[:/]+(admin\|root\|password\|test\|123)` | `*.{json,yaml,yml,xml,config,toml,cs,ts,py}` | CRITICAL | true |

### A05: CORS Misconfiguration

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A05-05a | `(?i)(Access-Control-Allow-Origin|AllowAnyOrigin|origin:\s*["']\*["']|cors\(\{[^}]*origin:\s*true)` | `*.{cs,ts,tsx,js,jsx,py,go,rb}` | HIGH | true |

### A10: SSRF

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A10-01a | `(?i)(HttpClient\|fetch\|axios\|requests?\.(get\|post\|put\|delete\|patch))\(.*(?:req\|request\|params\|query\|body\|args)` | `*.{cs,ts,tsx,js,jsx,py,go}` | HIGH | true |
| A10-02a | `(?i)(127\.0\.0\.1\|localhost\|0\.0\.0\.0\|10\.\d+\.\d+\.\d+\|192\.168\.\d+\.\d+\|169\.254\.169\.254)` | `*.{cs,ts,tsx,js,jsx,py,go,rb,yaml,yml,json,config}` | MEDIUM | true |

## .NET Patterns

### A01: Missing Authorization

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A01-01a | `\[ApiController\]` | `*.cs` | HIGH | true |

**Context check for A01-01a**: After finding `[ApiController]`, read the file and check for `[Authorize]` at class or all action levels. Also check for `[AllowAnonymous]` on intentionally public actions. Skip if controller name suggests public access (e.g., `HealthController`, `StatusController`).

### A02: Weak Crypto

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A02-02a | `(?i)(MD5\|SHA1)\.Create\(\)\|new (?:MD5\|SHA1)CryptoServiceProvider\(\)` | `*.cs` | CRITICAL | true |

**Context check for A02-02a**: If used for password hashing → CRITICAL. If used for checksums, cache keys, or non-security purposes → skip.

### A03: XSS (.NET)

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-07a | `Html\.Raw\(` | `*.{cshtml,razor}` | CRITICAL | true |

### A05: Developer Exception Page

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A05-02a | `UseDeveloperExceptionPage\(\)` | `*.cs` | CRITICAL | true |

**Context check for A05-02a**: Check if wrapped in `if (env.IsDevelopment())`. If not environment-guarded → CRITICAL.

### A05: Swagger in Production

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A05-07a | `UseSwagger\(\)\|UseSwaggerUI\(\)` | `*.cs` | MEDIUM | true |

**Context check**: Check if guarded by environment check. Unguarded = MEDIUM.

### A07: Identity/Auth Config

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A07-02a | `RequiredLength\s*=\s*[0-5]\b` | `*.cs` | MEDIUM | false |
| A07-07a | `ValidateIssuer\s*=\s*false\|ValidateAudience\s*=\s*false\|ValidateLifetime\s*=\s*false\|ValidateIssuerSigningKey\s*=\s*false` | `*.cs` | HIGH | true |

### A08: Insecure Deserialization

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A08-01a | `BinaryFormatter\|NetDataContractSerializer\|SoapFormatter\|ObjectStateFormatter\|LosFormatter` | `*.cs` | CRITICAL | true |
| A08-01b | `JsonConvert\.DeserializeObject\(.*TypeNameHandling` | `*.cs` | HIGH | true |

## JavaScript/TypeScript Patterns

### A03: XSS Sinks

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-05a | `\.innerHTML\s*=` | `*.{ts,tsx,js,jsx}` | CRITICAL | true |
| A03-05b | `\.outerHTML\s*=` | `*.{ts,tsx,js,jsx}` | CRITICAL | true |
| A03-05c | `document\.write\(` | `*.{ts,tsx,js,jsx}` | CRITICAL | true |
| A03-05d | `\beval\(` | `*.{ts,tsx,js,jsx}` | CRITICAL | true |
| A03-05e | `new Function\(` | `*.{ts,tsx,js,jsx}` | HIGH | true |
| A03-06a | `dangerouslySetInnerHTML` | `*.{tsx,jsx}` | CRITICAL | true |

**Context check for A03-05d/A03-05e**: If the argument is a string literal → LOW. If it contains user input or dynamic values → CRITICAL.

### A03: NoSQL Injection

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-03a | `\$where\|\.find\(\{.*\$` | `*.{ts,tsx,js,jsx}` | HIGH | true |

### A04: Client-Side Auth

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A04-03a | `(?i)(isAdmin\|isAuthenticated\|hasRole\|canAccess\|isAuthorized)\s*[=:]\s*` | `*.{ts,tsx,js,jsx}` | HIGH | true |

**Context check**: If this is a UI-only flag controlling component visibility (with server-side enforcement), lower to MEDIUM. If it gates access to data or functionality without server check → HIGH.

### A05: Misconfiguration

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A05-01b | `(?:NODE_ENV\|REACT_APP_ENV\|VITE_\w*ENV)\s*[!=]=.*development` | `*.{ts,tsx,js,jsx}` | MEDIUM | true |

### A08: Insecure Deserialization (Node)

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A08-03a | `require\(['"](?:node-serialize\|funcster)['"]\)` | `*.{ts,tsx,js,jsx}` | HIGH | false |

### A08: Missing SRI

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A08-04a | `<script\s+src=["']https?://` | `*.{html,htm,cshtml,razor,tsx,jsx}` | MEDIUM | true |

**Context check**: Check if the `<script>` tag has an `integrity` attribute. If CDN resource without `integrity` → MEDIUM.

## Python Patterns

### A03: Injection

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A03-01f | `(?:cursor\.execute\|\.raw\()\s*\(?.*%s.*%\s` | `*.py` | CRITICAL | true |
| A03-01g | `(?:cursor\.execute\|\.raw\()\s*\(?.*f["']` | `*.py` | CRITICAL | true |

### A05: Debug Mode

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A05-01c | `DEBUG\s*=\s*True` | `*.py` | HIGH | true |
| A05-01d | `app\.run\(.*debug\s*=\s*True` | `*.py` | HIGH | false |

### A07: Plaintext Passwords

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A07-01a | `(?i)password\s*==\s*["']` | `*.py` | CRITICAL | true |

### A08: Insecure Deserialization

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A08-02a | `pickle\.loads?\(` | `*.py` | CRITICAL | true |
| A08-02b | `yaml\.load\(` | `*.py` | CRITICAL | true |

**Context check for A08-02b**: Check if using `Loader=SafeLoader` or `yaml.safe_load()`. If not → CRITICAL. If SafeLoader → skip.

### A08: Insecure Deserialization (shelve/marshal)

| Check ID | Regex | Glob | Severity | Context |
|----------|-------|------|----------|---------|
| A08-02c | `(?:shelve\.open\|marshal\.loads?)\(` | `*.py` | HIGH | true |

## Context Verification Guide

When a pattern is marked `context: true`, follow these rules before recording a finding:

### Hardcoded Secrets (A02-01*)
1. Check if the value is a placeholder: `"changeme"`, `"TODO"`, `"REPLACE_ME"`, `"your-key-here"`, `"xxx"`, `"***"`, empty string
2. Check if the file is a test/example: `*Test*`, `*Example*`, `*.example`, `*.sample`
3. Check if the value is loaded from environment: `process.env`, `Environment.GetEnvironmentVariable`, `os.environ`
4. If in an example/template file → LOW. If in production code with real-looking value → CRITICAL.

### SQL Injection (A03-01*)
1. Read 5 lines above and below the match
2. Look for parameterized query indicators: `@param`, `?`, `:param`, `$1`
3. Check if the concatenated value is user-controlled vs. internal constant
4. If parameterized → skip. If concatenation with user input → CRITICAL.

### Weak Crypto (A02-02*)
1. Read the surrounding method/function
2. Check what the hash output is used for: password storage → CRITICAL, checksum/cache → skip
3. Look for bcrypt/scrypt/argon2/PBKDF2 as alternatives being used elsewhere

### Missing Auth (A01-01*)
1. Read the controller/handler file
2. Check for class-level `[Authorize]` attribute
3. Check for `[AllowAnonymous]` on specific actions that should be public
4. Check if the endpoint is health check, status, or login — these are intentionally public

### Eval/Exec (A03-04*, A03-05d)
1. Check if the argument is a hardcoded string literal (LOW risk)
2. Check if the argument includes any user-controlled data (CRITICAL)
3. For `eval()` in JS, check if it's in bundler/build code vs. runtime application code
