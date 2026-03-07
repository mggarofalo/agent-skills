#!/usr/bin/env python3
"""CLI entry point for the PR bug-finder agent."""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    query,
)

from prompts import (
    build_challenger_prompt,
    build_hunter_prompt,
    build_synthesizer_prompt,
)

MAX_DIFF_CHARS = 100_000


def fetch_pr_diff(pr_url: str, cwd: str) -> str:
    """Fetch a PR diff using the gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "diff", pr_url],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error fetching PR diff: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Install it: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)


def checkout_pr_branch(pr_url: str, cwd: str) -> str | None:
    """Checkout the PR branch, returning the previous branch name for cleanup."""
    stderr = sys.stderr

    # Remember current branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True, cwd=cwd,
        )
        previous_branch = result.stdout.strip()
    except subprocess.CalledProcessError:
        previous_branch = None

    # Checkout the PR branch
    print(f"Checking out PR branch for {pr_url}...", file=stderr)
    try:
        subprocess.run(
            ["gh", "pr", "checkout", pr_url],
            capture_output=True, text=True, check=True, cwd=cwd,
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: could not checkout PR branch: {e.stderr}", file=stderr)
        print("Proceeding with current branch — file reads may not match the diff.", file=stderr)
        return None

    # Report what we checked out
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True, cwd=cwd,
        )
        print(f"On branch: {result.stdout.strip()}", file=stderr)
    except subprocess.CalledProcessError:
        pass

    return previous_branch


def restore_branch(branch: str, cwd: str) -> None:
    """Restore the previous branch after analysis."""
    try:
        subprocess.run(
            ["git", "checkout", branch],
            capture_output=True, text=True, check=True, cwd=cwd,
        )
        print(f"Restored branch: {branch}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Warning: could not restore branch {branch}: {e.stderr}", file=sys.stderr)


def read_diff_input(path: str) -> str:
    """Read diff from a file path or stdin (if path is '-')."""
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path) as f:
            return f.read()
    except OSError as e:
        print(f"Error reading diff file: {e}", file=sys.stderr)
        sys.exit(1)


def validate_diff(diff: str) -> None:
    """Check that the input looks like a diff."""
    diff_markers = ("diff --git", "---", "+++", "@@")
    if not any(marker in diff for marker in diff_markers):
        print("Warning: input does not look like a diff (no diff markers found).", file=sys.stderr)


def truncate_diff_if_needed(diff: str) -> str:
    """Truncate diff to MAX_DIFF_CHARS at a line boundary."""
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    truncated = diff[:MAX_DIFF_CHARS]
    last_newline = truncated.rfind("\n")
    if last_newline > 0:
        truncated = truncated[:last_newline]
    original_lines = diff.count("\n")
    truncated_lines = truncated.count("\n")
    print(
        f"Warning: diff truncated from {len(diff)} to {len(truncated)} chars "
        f"({original_lines} to {truncated_lines} lines).",
        file=sys.stderr,
    )
    return truncated


class Timer:
    def __init__(self):
        self.start = time.monotonic()

    def elapsed(self) -> str:
        s = int(time.monotonic() - self.start)
        return f"[{s // 60}:{s % 60:02d}]"

    def seconds(self) -> float:
        return time.monotonic() - self.start

    @staticmethod
    def fmt(secs: float) -> str:
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"


async def run_agent(
    label: str,
    prompt: str,
    options: ClaudeAgentOptions,
    timer: Timer,
) -> str:
    """Run a single agent, stream progress to stderr, return all text output."""
    stderr = sys.stderr
    print(f"\n{timer.elapsed()} ▶ {label}", file=stderr)
    agent_start = time.monotonic()
    tool_calls = 0
    text_parts: list[str] = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if message.is_error:
                print(f"{timer.elapsed()} ERROR: {message.result}", file=stderr)
                return ""
            if message.result:
                text_parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
                    print(f"{timer.elapsed()} {block.text}", file=stderr)
                elif isinstance(block, ThinkingBlock):
                    print(f"{timer.elapsed()} [thinking] {block.thinking}", file=stderr)
                elif isinstance(block, ToolUseBlock):
                    tool_calls += 1
                    print(f"{timer.elapsed()} 🔧 {block.name}({block.input})", file=stderr)
        elif isinstance(message, SystemMessage):
            subtype = getattr(message, "subtype", None)
            if subtype:
                print(f"{timer.elapsed()} ⚙ {subtype}", file=stderr)

    duration = time.monotonic() - agent_start
    print(f"{timer.elapsed()} ✓ {label} done ({Timer.fmt(duration)}, {tool_calls} tool calls)", file=stderr)
    return "\n".join(text_parts)


async def run_analysis(diff: str, cwd: str, max_budget: float, out_dir: str) -> None:
    """Run the 3-step adversarial bug-finding pipeline."""
    timer = Timer()
    stderr = sys.stderr
    base_opts = dict(
        permission_mode="bypassPermissions",
        model="sonnet",
        cwd=cwd,
    )

    os.makedirs(out_dir, exist_ok=True)
    print(f"{timer.elapsed()} Output dir: {out_dir}", file=stderr)

    # Step 1: Bug Hunter
    hunter_output = await run_agent(
        label="Bug Hunter",
        prompt=f"Analyze this diff for bugs.\n\n```diff\n{diff}\n```",
        options=ClaudeAgentOptions(
            system_prompt=build_hunter_prompt(),
            allowed_tools=["Read", "Glob", "Grep"],
            max_turns=100,
            max_budget_usd=max_budget * 0.4,
            **base_opts,
        ),
        timer=timer,
    )

    if not hunter_output.strip():
        print("Error: Bug Hunter produced no output.", file=stderr)
        sys.exit(1)

    hunter_path = os.path.join(out_dir, "hunter.md")
    with open(hunter_path, "w") as f:
        f.write(hunter_output)
    print(f"{timer.elapsed()} Hunter output → {hunter_path}", file=stderr)

    # Step 2: Bug Challenger
    challenger_output = await run_agent(
        label="Bug Challenger",
        prompt=(
            f"Verify these bug reports against the codebase.\n\n"
            f"## Diff\n```diff\n{diff}\n```\n\n"
            f"## Hunter's Bug Report\n{hunter_output}"
        ),
        options=ClaudeAgentOptions(
            system_prompt=build_challenger_prompt(),
            allowed_tools=["Read", "Glob", "Grep"],
            max_turns=100,
            max_budget_usd=max_budget * 0.4,
            **base_opts,
        ),
        timer=timer,
    )

    if not challenger_output.strip():
        print("Error: Bug Challenger produced no output.", file=stderr)
        sys.exit(1)

    challenger_path = os.path.join(out_dir, "challenger.md")
    with open(challenger_path, "w") as f:
        f.write(challenger_output)
    print(f"{timer.elapsed()} Challenger output → {challenger_path}", file=stderr)

    # Step 3: Synthesizer
    report = await run_agent(
        label="Synthesizer",
        prompt=(
            f"Synthesize the final bug analysis report.\n\n"
            f"## Hunter Output\n{hunter_output}\n\n"
            f"## Challenger Output\n{challenger_output}"
        ),
        options=ClaudeAgentOptions(
            system_prompt=build_synthesizer_prompt(),
            allowed_tools=[],
            max_turns=5,
            max_budget_usd=max_budget * 0.2,
            **base_opts,
        ),
        timer=timer,
    )

    # Write report to file
    if not report.strip():
        print("WARNING: Synthesizer produced no output. Using raw outputs.", file=stderr)
        report = (
            f"# PR Bug Analysis Report\n\n"
            f"## Raw Hunter Output\n{hunter_output}\n\n"
            f"## Raw Challenger Output\n{challenger_output}"
        )

    report_path = os.path.join(out_dir, "report.md")
    with open(report_path, "w") as f:
        f.write(report)

    # Stats
    print(f"\n{'─' * 40}", file=stderr)
    print(f"Total duration:  {Timer.fmt(timer.seconds())}", file=stderr)
    print(f"Report:          {report_path}", file=stderr)

    # Print the report path to stdout — this is the only stdout output
    print(report_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adversarial PR bug-finding agent using competing Sonnet subagents.",
    )
    parser.add_argument(
        "pr_url",
        nargs="?",
        help="GitHub PR URL to analyze",
    )
    parser.add_argument(
        "--diff",
        metavar="FILE",
        help="Path to a diff file, or '-' for stdin",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Working directory for codebase context (default: current directory)",
    )
    parser.add_argument(
        "--max-budget",
        type=float,
        default=2.00,
        help="Maximum budget in USD (default: $2.00)",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Directory for output files (default: auto-created in /tmp)",
    )

    args = parser.parse_args()

    if not args.pr_url and not args.diff:
        parser.print_help()
        print("\nError: provide a PR URL or --diff FILE.", file=sys.stderr)
        sys.exit(1)

    if args.pr_url and args.diff:
        print("Error: provide either a PR URL or --diff, not both.", file=sys.stderr)
        sys.exit(1)

    cwd = os.path.abspath(args.cwd)
    previous_branch = None

    if args.pr_url:
        previous_branch = checkout_pr_branch(args.pr_url, cwd)
        diff = fetch_pr_diff(args.pr_url, cwd)
    else:
        diff = read_diff_input(args.diff)

    if not diff.strip():
        print("Error: diff is empty.", file=sys.stderr)
        sys.exit(1)

    validate_diff(diff)
    diff = truncate_diff_if_needed(diff)

    out_dir = args.output_dir or tempfile.mkdtemp(prefix="pr-bug-finder-")
    try:
        asyncio.run(run_analysis(diff, cwd, args.max_budget, out_dir))
    finally:
        if previous_branch:
            restore_branch(previous_branch, cwd)


if __name__ == "__main__":
    main()
