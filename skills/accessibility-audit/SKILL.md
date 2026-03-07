---
name: accessibility-audit
description: >
  Audit web pages for WCAG 2.1 AA compliance and ADA accessibility concerns.
  Uses agent-browser for runtime inspection and source analysis for static checks.
  Reports findings by severity with WCAG criterion references.
allowed-tools: Bash, Read, Grep, Glob, mcp__aspire__list_resources, mcp__aspire__list_console_logs
user_invocable: true
argument: "<url...> | --app — Audit page URLs, or discover and audit all app routes"
---

# Accessibility Audit

Audit web pages for WCAG 2.1 AA compliance using agent-browser runtime inspection and static source analysis. Reports findings by severity (CRITICAL/HIGH/MEDIUM/LOW) with WCAG criterion references.

## Usage

- `/accessibility-audit <url>` — Audit a single page
- `/accessibility-audit <url1> <url2> ...` — Audit multiple pages
- `/accessibility-audit --app` — Discover all routes in the current project and audit them

## Phase 1: Setup & URL Resolution

### Parse Arguments

Parse the argument string to determine the audit target(s):

1. **Single URL** (starts with `http`): Audit that one page
2. **Multiple URLs** (space-separated, each starts with `http`): Audit each page
3. **`--app` flag**: Discover routes from the project source and build URL list

### Route Discovery (`--app` mode)

1. **Find the running app URL:**
   - Use `mcp__aspire__list_resources` to check for running Aspire resources
   - If Aspire is running, use `mcp__aspire__list_console_logs` to find the actual frontend port (Aspire assigns random ports — never assume defaults)
   - If no Aspire: look for `package.json` with a dev script, or ask the user for the base URL via AskUserQuestion

2. **Discover routes:**
   - Glob for router configuration files: `**/router.tsx`, `**/router.ts`, `**/App.tsx`, `**/routes.ts`, `**/routes.tsx`
   - Read each file and extract `path="..."` or `path: "..."` patterns
   - Skip dynamic segments (`:id`, `*`) — these need real data and should be audited manually
   - Build full URLs by combining base URL + discovered paths

3. **Read the WCAG checklist** from `~/.claude/skills/accessibility-audit/references/wcag-checklist.md` for criterion reference during the audit.

### Initialize Tracking

Create an in-memory findings list to collect results across all pages:
```
findings = [] // { page, severity, wcag, check, detail }
```

## Phase 2: Runtime Audit (Per Page)

For **each URL** in the target list, perform the following checks. Each agent-browser command MUST be a separate Bash tool call (no `&&` chaining — hooks will reject it). All screenshots go to `$TEMP`.

### 2.1: Open the Page

```
agent-browser open <url>
```

Wait for the page to load:
```
sleep 3
```

Take a baseline screenshot:
```
agent-browser screenshot "$TEMP/a11y-{page-slug}-baseline.png"
```

Read the screenshot to visually verify the page loaded correctly.

### 2.2: Capture Full Accessibility Tree

```
agent-browser snapshot
```

**IMPORTANT:** Do NOT use the `-i` flag. We need the FULL accessibility tree including non-interactive elements (landmarks, headings, static text) — not just interactive elements.

### 2.3: Accessibility Tree Checks

Analyze the snapshot output for each of these checks:

| # | Check | WCAG | Severity | What to look for |
|---|-------|------|----------|------------------|
| 1 | Main landmark | 1.3.1 | CRITICAL | A `main` node exists in the tree |
| 2 | Navigation landmark | 1.3.1 | HIGH | A `navigation` node exists |
| 3 | Banner landmark | 1.3.1 | MEDIUM | A `banner` node exists |
| 4 | Exactly one h1 | 1.3.1, 2.4.6 | HIGH | Count `heading` nodes with `[level=1]` — should be exactly 1 |
| 5 | Heading hierarchy | 1.3.1 | HIGH | No skipped levels (e.g., h1 → h3 with no h2) |
| 6 | Form field labels | 1.3.1, 3.3.2 | CRITICAL | Every `textbox`, `combobox`, `checkbox`, `radio`, `spinbutton` has a non-empty accessible name |
| 7 | Button labels | 4.1.2 | CRITICAL | Every `button` node has text content (not empty string) |
| 8 | Link text quality | 2.4.4 | MEDIUM | Links don't use generic text ("click here", "here", "read more", "link") |
| 9 | Table headers | 1.3.1 | HIGH | Tables have `columnheader` or `rowheader` nodes |
| 10 | Dialog labels | 4.1.2 | HIGH | Any `dialog` or `alertdialog` nodes have accessible names |
| 11 | ARIA live regions | 4.1.3 | MEDIUM | Dynamic content areas have `region` with name, or `status`/`alert` role |

### 2.4: Page-Level Checks

Run these commands to check page-level properties:

**Page title (WCAG 2.4.2, CRITICAL):**
```
agent-browser get title
```
Fail if the title is empty, generic ("React App", "Vite App", "Vite + React", "Untitled"), or matches the framework boilerplate.

**Language attribute (WCAG 3.1.1, CRITICAL):**
```
agent-browser eval "document.documentElement.lang"
```
Fail if empty string or not set.

### 2.5: Keyboard Navigation Check

Tab through 5–8 interactive elements to verify keyboard accessibility:

1. Press Tab and take a snapshot after each press:
   ```
   agent-browser press Tab
   ```
   ```
   agent-browser snapshot -i
   ```
2. Repeat 5–8 times
3. After each tab, verify:
   - Focus moved to a new interactive element (not stuck)
   - Focus order is logical (generally left-to-right, top-to-bottom)
4. Take a screenshot after every 2–3 tabs to verify focus indicators are visible:
   ```
   agent-browser screenshot "$TEMP/a11y-{page-slug}-tab-{n}.png"
   ```
5. Read the screenshots and check that the focused element has a visible focus ring/outline

**Record findings:**
- No visible focus indicator → CRITICAL (WCAG 2.4.7)
- Focus trapped or stuck → CRITICAL (WCAG 2.1.2)
- Illogical focus order → MEDIUM (WCAG 2.4.3)

## Phase 3: Static Source Analysis

If source files can be identified (via route → component mapping from Phase 1), grep for common static violations.

### 3.1: Identify Source Files

From the router config, map each audited route's `path` to its `element` or `component` import. Read those component files to get their paths.

### 3.2: Static Checks

For each identified source file, run these grep checks:

| # | Check | WCAG | Severity | Pattern |
|---|-------|------|----------|---------|
| 1 | Missing alt text | 1.1.1 | HIGH | `<img` tags without `alt` attribute nearby (within 2 lines) |
| 2 | Positive tabIndex | 2.4.3 | HIGH | `tabIndex` with value > 0 (e.g., `tabIndex={2}`, `tabindex="3"`) |
| 3 | Autofocus usage | 2.4.3 | MEDIUM | `autoFocus` or `autofocus` attribute |
| 4 | onClick on non-interactive | 2.1.1 | MEDIUM | `onClick` on `<div` or `<span` without corresponding `onKeyDown`/`onKeyUp`/`onKeyPress` |
| 5 | Missing aria-required | 3.3.2 | LOW | `required` attribute without `aria-required="true"` (React usually handles this, so only flag if both are absent) |

For check #1 (missing alt), use a multiline grep or read the file and scan for `<img` tags. Decorative images with `alt=""` are acceptable — only flag completely missing `alt`.

For check #4 (onClick on non-interactive), read the component file and look for patterns like:
```
<div onClick=
<span onClick=
```
without a keyboard handler on the same element.

## Phase 4: Report Generation

After all pages are audited, compile findings into a markdown report. Display the report directly to the user (no file output).

### Report Format

```markdown
# Accessibility Audit Report

**Date:** {YYYY-MM-DD}  |  **Pages:** {N}  |  **Result:** {PASS or FAIL}

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | {n} |
| HIGH     | {n} |
| MEDIUM   | {n} |
| LOW      | {n} |

---

## Page: {url}

### CRITICAL
- **[WCAG {criterion}]** {check name} — {detail}

### HIGH
- **[WCAG {criterion}]** {check name} — {detail}

### MEDIUM
- **[WCAG {criterion}]** {check name} — {detail}

### LOW
- **[WCAG {criterion}]** {check name} — {detail}

---

## Static Analysis

### {file path}

- **[WCAG {criterion}]** {severity}: {check name} — {detail} (line {N})

---

## Recommendations

{2-5 prioritized recommendations for the most impactful fixes}
```

### Severity Definitions

- **CRITICAL**: Blocks access entirely for some users. Must fix. (Determines PASS/FAIL)
- **HIGH**: Significant barrier but workaround may exist. Should fix soon.
- **MEDIUM**: Degrades experience but doesn't block access. Fix when possible.
- **LOW**: Best practice violation. Nice to have.

### Pass/Fail Determination

- **PASS** = Zero CRITICAL findings across all pages
- **FAIL** = One or more CRITICAL findings

## Phase 5: Cleanup

1. Close agent-browser:
   ```
   agent-browser close
   ```

2. Print a summary line:
   ```
   Audited {N} pages. Found {C} critical, {H} high, {M} medium, {L} low. Result: {PASS/FAIL}
   ```

## Important Notes

- **Hook compliance**: Every `agent-browser` command MUST be a separate Bash tool call. Never chain with `&&`, `||`, or `;`.
- **Screenshots**: Always save to `$TEMP`, never to the working directory.
- **Aspire ports**: Never assume port numbers. Always check `list_console_logs` for the actual port.
- **Full accessibility tree**: Use `agent-browser snapshot` (no `-i`) for audit checks. Use `agent-browser snapshot -i` only during keyboard navigation to see which interactive element has focus.
- **No false positives**: If you're unsure whether something is a violation, note it as an observation in the Recommendations section rather than counting it as a finding.
- **Scope**: This audit covers automatable WCAG 2.1 AA checks. Note in the report footer that manual review is still needed for checks that require human judgment (color contrast perception, meaningful content order, cognitive load).
