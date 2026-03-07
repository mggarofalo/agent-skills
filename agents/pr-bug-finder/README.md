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

Or run standalone:

```bash
python main.py --pr-url <url> --output-dir <path> [--budget 2.00]
```

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
