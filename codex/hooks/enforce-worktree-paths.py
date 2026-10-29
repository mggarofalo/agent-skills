#!/usr/bin/env python3
"""Codex PreToolUse guard that keeps apply_patch inside the active worktree."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def deny(reason: str) -> None:
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}},
        sys.stdout,
    )
    raise SystemExit(0)


def fail_closed(reason: str) -> None:
    sys.stderr.write(f"BLOCKED (worktree guard error, failing closed): {reason}\n")
    raise SystemExit(2)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=5, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def patch_paths(command: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"^\*\*\* (?:Add|Update|Delete|Move to) File: (.+)$", command, re.MULTILINE)
    ]


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001 - safety guard must fail closed
        fail_closed(f"invalid JSON payload: {exc}")
    if not isinstance(payload, dict) or payload.get("tool_name") != "apply_patch":
        return

    cwd = Path(str(payload.get("cwd") or os.getcwd())).resolve()
    active_root_text = git(cwd, "rev-parse", "--show-toplevel")
    if not active_root_text:
        return
    active_root = Path(active_root_text).resolve()

    listing = git(cwd, "worktree", "list", "--porcelain")
    roots = [Path(line.removeprefix("worktree ")).resolve() for line in listing.splitlines() if line.startswith("worktree ")]
    if len(roots) < 2 or active_root not in roots:
        return
    primary_root = roots[0]
    if active_root == primary_root:
        return

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str):
        fail_closed("apply_patch.command must be a string")

    for value in patch_paths(command):
        candidate = Path(os.path.expanduser(value))
        if not candidate.is_absolute():
            candidate = active_root / candidate
        candidate = candidate.resolve(strict=False)
        if candidate == primary_root or primary_root in candidate.parents:
            relative = candidate.relative_to(primary_root)
            deny(f"BLOCKED: patch escapes the active worktree and targets the primary checkout. Use `{active_root / relative}` instead.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - safety guard must fail closed
        fail_closed(f"{type(exc).__name__}: {exc}")
