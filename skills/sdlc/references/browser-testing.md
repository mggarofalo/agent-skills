# Browser Testing with agent-browser

## Overview

`agent-browser` is a CLI-based headless browser automation tool for AI agents. It is available via Bash — not an MCP server. All commands are invoked as `agent-browser <command> [args]`.

The browser persists between commands via a daemon process, so you can chain commands with `&&` in a single shell call.

## When to Use Browser Testing

Use browser automation when the feature involves **user-facing behavior** that can only be verified by rendering the application in a browser:

- UI components, pages, or layouts
- Form interactions and validation
- Navigation flows and routing
- Client-side state management visible in the DOM
- API responses rendered in the UI
- Accessibility (ARIA roles, keyboard navigation)
- Client-side security (XSS, open redirects, exposed data in DOM)

**Do NOT use browser testing for:**
- Pure backend/API changes with no UI
- Library or utility code
- Database migrations
- CLI tools
- Infrastructure or config changes

## Prerequisites

Before running browser tests, determine if the application can be served locally:

1. Check the state file for tech stack and build/serve commands
2. Look for dev server commands in AGENTS.md, package.json scripts, or project config
3. Common dev servers:
   - Node/React/Next.js: `npm run dev` or `yarn dev`
   - .NET: `dotnet run`
   - Python/Django: `python manage.py runserver`
   - Python/Flask: `flask run`
   - Swift/Vapor: `swift run`
4. Start the dev server in the background using Bash with `run_in_background: true`
5. Wait for the server to be ready before browser commands

If the project has no local dev server (e.g., a library, CLI tool, or backend-only service), skip browser testing entirely.

## Core Command Patterns

### Navigation and Page Loading

```bash
# Open a URL and wait for it to fully load
agent-browser open http://localhost:3000 && agent-browser wait --load networkidle

# Navigate to a specific route
agent-browser open http://localhost:3000/dashboard && agent-browser wait --load networkidle
```

### Getting Page State (Preferred for AI)

```bash
# Accessibility snapshot — returns semantic tree with @refs for interaction
# This is the PRIMARY way to understand page state
agent-browser snapshot -i          # Interactive elements only (forms, buttons, links)
agent-browser snapshot -c          # Compact (remove empty structural elements)
agent-browser snapshot -i -c       # Both: interactive + compact (recommended)

# Get specific content
agent-browser get text @e1         # Text content of element by ref
agent-browser get title            # Page title
agent-browser get url              # Current URL
agent-browser get count "button"   # Count elements matching selector
```

### Interacting with Elements

```bash
# Click by ref (from snapshot) or CSS selector
agent-browser click @e3
agent-browser click "#submit-btn"

# Fill forms
agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"

# Semantic find + action (no snapshot needed)
agent-browser find role button click --name "Submit"
agent-browser find label "Email" fill "user@example.com"
agent-browser find placeholder "Search..." fill "query"

# Keyboard
agent-browser press Enter
agent-browser press Tab
```

### Screenshots (for Visual Evidence)

```bash
# Standard screenshot
agent-browser screenshot .sdlc/evidence/page.png

# Full-page screenshot
agent-browser screenshot --full .sdlc/evidence/full-page.png

# Annotated screenshot (numbered labels on interactive elements)
agent-browser screenshot --annotate .sdlc/evidence/annotated.png
```

### Waiting

```bash
# Wait for element to appear
agent-browser wait "#loading-spinner"    # Wait for visibility
agent-browser wait --text "Welcome"      # Wait for text to appear
agent-browser wait --url "/dashboard"    # Wait for URL change
agent-browser wait 2000                  # Wait 2 seconds
```

### Checking State

```bash
# Element state checks
agent-browser is visible "#error-message"
agent-browser is enabled "#submit-btn"
agent-browser is checked "#agree-checkbox"
```

### Diffing (for Before/After Comparison)

```bash
# Take a snapshot, make changes, then diff
agent-browser snapshot         # baseline
# ... make changes ...
agent-browser diff snapshot    # compare current vs baseline
```

## Session Management

```bash
# Use named sessions to isolate browser state
agent-browser --session "qa-test" open http://localhost:3000

# Close when done
agent-browser close
```

## Typical Test Flow

```bash
# 1. Start dev server (in background)
# 2. Open the page
agent-browser open http://localhost:3000/feature-page && agent-browser wait --load networkidle

# 3. Get interactive snapshot to understand the page
agent-browser snapshot -i -c

# 4. Interact (using @refs from snapshot)
agent-browser fill @e1 "test input" && agent-browser click @e3

# 5. Verify result
agent-browser wait --text "Success"
agent-browser snapshot -i -c    # Check new state

# 6. Screenshot for evidence
agent-browser screenshot .sdlc/evidence/result.png

# 7. Clean up
agent-browser close
```

## Error Handling

- If `agent-browser` commands fail, check:
  - Is the dev server running? (`agent-browser get url` to verify)
  - Is the selector/ref valid? (Re-run `snapshot -i -c` to get fresh refs)
  - Is the page loaded? (Add `wait --load networkidle` after navigation)
- Refs (`@e1`, `@e2`) change between snapshots — always use refs from the most recent snapshot
- If the browser session is stale, run `agent-browser close` and start fresh
