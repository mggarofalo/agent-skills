# pr-bug-finder

Adversarial bug-finding agent that analyzes PRs using three competing Claude subagents via the Claude Agent SDK.

## Pipeline

1. **Bug Hunter** — Reads the PR diff and codebase, finds potential bugs (40% of budget)
2. **Bug Challenger** — Reviews the Hunter's findings, filters out false positives (40% of budget)
3. **Synthesizer** — Produces a final ranked report from the surviving findings (20% of budget)

All subagents use Sonnet with `max_turns=100` (Hunter/Challenger) or `max_turns=5` (Synthesizer).

## Usage

Invoked via the `/find-bugs` command in Claude Code, which calls `main.py` directly:

```
/find-bugs [pr-url-or-diff-path]
```

Or run standalone. Exactly one input source is required:

```bash
python main.py <pr-url-or-number> --cwd <repo> --output-dir <path>
python main.py --local          --cwd <repo> --output-dir <path>   # uncommitted changes vs HEAD
python main.py --diff <file|->  --cwd <repo> --output-dir <path>   # a diff file, or - for stdin
```

The final report path is the only thing written to stdout; all progress goes to stderr.

### Resuming a failed run

Each stage's output is written to `--output-dir` the moment it completes (`hunter.md`, `challenger.md`, `report.md`), and streamed to disk incrementally while it runs. Since a stage costs 5-15 minutes, re-run with the same output directory rather than starting over:

```bash
python main.py <same args> --output-dir <same path> --resume
```

`--resume` skips any stage whose output file already exists and is non-empty, and requires `--output-dir`. A stage that errored deletes its own partial output, so a truncated analysis is never resumed as though it were complete.

### Encoding

All file I/O is explicitly UTF-8. Agent output regularly contains characters outside Latin-1 (arrows, em dashes, box drawing, emoji), which the Windows default locale encoding (cp1252) cannot represent. Do not remove the explicit `encoding=` arguments, and do not rely on `PYTHONUTF8=1` being set in the environment — the script must work when invoked plainly.

## Setup

```bash
pip install -e .
cp .env.example .env  # add your ANTHROPIC_API_KEY
```

## Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point and agent orchestration |
| `prompts.py` | System/user prompt builders for each subagent |
| `schemas.py` | Pydantic schemas for structured output |
