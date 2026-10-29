#!/usr/bin/env python3
"""PreToolUse guard that redirects unbounded reads larger than 350 lines."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path

THRESHOLD = int(os.environ.get("AGENT_ROUTER_LINE_THRESHOLD", "350"))
READ_COMMANDS = {"cat", "head", "tail", "less", "more"}


def line_count_over(path: Path, threshold: int = THRESHOLD) -> bool:
    """Stop counting as soon as the threshold is exceeded."""
    count = 0
    last = b""
    with path.open("rb") as handle:
        while count <= threshold:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            count += chunk.count(b"\n")
            last = chunk[-1:]
    if last and last != b"\n":
        count += 1
    return count > threshold


def deny(host: str, paths: list[Path]) -> None:
    rendered = " ".join(shlex.quote(str(path)) for path in paths)
    home = "~/.claude" if host == "claude" else "~/.codex"
    command = (
        f"python3 {home}/agent-router/bulk_read.py --host {host} "
        f"--question 'state the exact information you need' -- {rendered}"
    )
    reason = (
        f"BLOCKED: this read can place more than {THRESHOLD} lines in the frontier model context. "
        f"Delegate the mechanical read and use only its bullets: {command}. "
        "For editing or reasoning, use a targeted read with both offset and limit instead."
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


def resolve_file(raw: str, cwd: Path) -> Path | None:
    if not raw or raw == "-" or any(char in raw for char in "*$?[]{}"):
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = cwd / path
    try:
        path = path.resolve()
        return path if path.is_file() else None
    except OSError:
        return None


def command_segments(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token and all(char in "|&;" for char in token):
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def bounded_count(name: str, args: list[str]) -> int | None:
    """Return a maximum output line count, or None when the command is unbounded."""
    if name not in {"head", "tail"}:
        return None
    if any(arg == "-c" or arg == "--bytes" or arg.startswith("--bytes=") for arg in args):
        return None
    count = 10
    for index, arg in enumerate(args):
        value = None
        if arg in {"-n", "--lines"} and index + 1 < len(args):
            value = args[index + 1]
        elif arg.startswith("--lines="):
            value = arg.split("=", 1)[1]
        elif re.fullmatch(r"-\d+", arg):
            value = arg[1:]
        if value is not None:
            if not value.isdigit() or value.startswith("+"):
                return None
            count = int(value)
    return count


def file_args(args: list[str], cwd: Path) -> list[Path]:
    """Extract literal file arguments while skipping common option values."""
    result: list[Path] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in {"-n", "--lines", "-c", "--bytes"}:
            skip_next = True
            continue
        if arg.startswith("-") or re.fullmatch(r"\d+", arg):
            continue
        path = resolve_file(arg, cwd)
        if path is not None and path not in result:
            result.append(path)
    return result


def bash_paths(command: str, cwd: Path) -> tuple[list[Path], list[Path]]:
    """Return unbounded files and bounded files whose requested output is too large."""
    unbounded: list[Path] = []
    oversized_bounded: list[Path] = []
    for segment in command_segments(command):
        name = Path(segment[0]).name
        if name not in READ_COMMANDS:
            continue
        args = segment[1:]
        bound = bounded_count(name, args)
        if bound is not None:
            if bound > THRESHOLD:
                oversized_bounded.extend(path for path in file_args(args, cwd) if path not in oversized_bounded)
            continue
        unbounded.extend(path for path in file_args(args, cwd) if path not in unbounded)
    return unbounded, oversized_bounded


def main() -> int:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--host", choices=("claude", "codex"), required=True)
    arg_parser.add_argument("--kind", choices=("read", "bash"), required=True)
    args = arg_parser.parse_args()
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return 0  # Cost optimization fails open; safety hooks remain authoritative.
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()

    paths: list[Path] = []
    if args.kind == "read":
        limit = tool_input.get("limit")
        if tool_input.get("offset") is not None and isinstance(limit, int) and 0 < limit <= THRESHOLD:
            return 0
        path = resolve_file(str(tool_input.get("file_path", "")), cwd)
        if path is not None and line_count_over(path):
            paths = [path]
    else:
        candidates, oversized_bounded = bash_paths(str(tool_input.get("command", "")), cwd)
        paths = [path for path in candidates if line_count_over(path)]
        paths.extend(path for path in oversized_bounded if path not in paths and line_count_over(path))
    if paths:
        deny(args.host, paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
