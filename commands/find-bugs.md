---
description: Run adversarial bug analysis on a PR
argument-hint: [pr-number-or-url-or-diff-path]
allowed-tools: Bash, Read
---

Run the adversarial PR bug-finder agent. This takes 5-15 minutes.

CRITICAL: The argument is a **GitHub PR number** (e.g., `125`), a GitHub PR URL, or a diff file path. It is NEVER a Plane issue ID. Do NOT interpret bare numbers as Plane issues (e.g., do NOT look up MGG-125). Always pass the argument directly to the Python pipeline below — do NOT attempt manual bug analysis yourself.

IMPORTANT execution rules:
- You MUST run the Python pipeline below. Do NOT skip it and do your own analysis.
- Run the command in the FOREGROUND, not the background. This is a long-running command — set a timeout of 600000 (10 minutes).
- Do NOT append `2>&1`. Stderr streams live progress to the terminal; stdout contains only the report file path.
- Do NOT run it in the background or try to poll it.

First, create an output directory:
```
OUTPUT_DIR=/tmp/pr-bug-finder-$(date +%s)
mkdir -p "$OUTPUT_DIR"
```

If an argument was provided (`$ARGUMENTS`), determine what it is:

- If it looks like a URL (contains `github.com` or starts with `http`) or a bare number (GitHub PR number), run:
  ```
  env -u CLAUDECODE python ~/.claude/agents/pr-bug-finder/main.py $ARGUMENTS --cwd $(pwd) --output-dir "$OUTPUT_DIR"
  ```
- If it looks like a file path, run:
  ```
  env -u CLAUDECODE python ~/.claude/agents/pr-bug-finder/main.py --diff $ARGUMENTS --cwd $(pwd) --output-dir "$OUTPUT_DIR"
  ```

If NO argument was provided, try to detect the current PR:
```
PR_URL=$(gh pr view --json url -q .url 2>/dev/null)
```
If that succeeds, use that URL. If it fails, tell the user to provide a PR URL or diff path.

## Reading the results

The command prints the report file path to stdout (e.g. `/tmp/pr-bug-finder-1234567890/report.md`). Use the `Read` tool to read that file and present the markdown report to the user.

The output directory also contains intermediate files:
- `hunter.md` — Raw Bug Hunter output (written after step 1 completes)
- `challenger.md` — Raw Bug Challenger output (written after step 2 completes)
- `report.md` — Final synthesized report (written after step 3 completes)

If the command fails, show the error from stderr.
