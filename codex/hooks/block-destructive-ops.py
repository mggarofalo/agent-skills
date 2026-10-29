#!/usr/bin/env python3
"""Codex PreToolUse guard for destructive commands and protected files."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

HOME = Path.home().resolve()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", HOME / ".codex")).resolve()


def deny(reason: str) -> None:
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
    raise SystemExit(0)


def fail_closed(reason: str) -> None:
    sys.stderr.write(f"BLOCKED (guard error, failing closed): {reason}\n")
    raise SystemExit(2)


def normalized(path: str, cwd: Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(path))
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return candidate.resolve(strict=False)


def inside(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def is_sensitive(path: Path) -> bool:
    protected_dirs = [HOME / ".ssh", HOME / ".aws", HOME / ".gnupg", HOME / ".config" / "gh"]
    if any(inside(path, directory.resolve()) for directory in protected_dirs):
        return True
    if path == (HOME / ".netrc").resolve():
        return True
    name = path.name.lower()
    if name == ".env" or (name.startswith(".env.") and name not in {".env.example", ".env.template", ".env.sample"}):
        return True
    if name in {".npmrc", ".pypirc", "credentials.json"}:
        return True
    if name.startswith(("id_rsa", "id_ed25519", "id_ecdsa", "service-account")):
        return True
    return path.suffix.lower() in {".pem", ".key", ".pfx", ".p12"}


def is_guardrail(path: Path) -> bool:
    protected_dirs = [CODEX_HOME / "hooks", CODEX_HOME / "agents", HOME / ".agents" / "skills"]
    protected_files = [CODEX_HOME / "hooks.json", CODEX_HOME / "config.toml", CODEX_HOME / "AGENTS.md"]
    return any(inside(path, directory.resolve()) for directory in protected_dirs) or any(
        path == item.resolve() for item in protected_files
    )


def patch_paths(command: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"^\*\*\* (?:Add|Update|Delete|Move to) File: (.+)$", command, re.MULTILINE)
    ]


def strip_quoted_content(command: str) -> str:
    command = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\s*\n.*?\n\s*\1", "", command, flags=re.DOTALL)
    command = re.sub(r'"(?:[^"\\]|\\.)*"', '""', command)
    return re.sub(r"'[^']*'", "''", command)


def check_destructive(command: str) -> None:
    stripped = strip_quoted_content(command)
    checks = [
        (r"\bgit\s+reset\s+--hard\b", "`git reset --hard` destroys uncommitted work. Stash it or use a non-destructive reset."),
        (r"\bgit\s+clean\s+(?:\S+\s+)*-[A-Za-z]*f", "`git clean -f` permanently deletes untracked files. Preview with `git clean -dn`."),
        (r"\bgit\s+(?:checkout\s+--\s+\.|restore\s+\.)", "This command discards all unstaged changes. Restore only explicit reviewed paths."),
        (r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:ba)?sh\b", "Do not pipe downloaded code into a shell. Download, inspect, then run it explicitly."),
        (r"\bcurl\b.*(?:-d\s*@|--data(?:-\w+)?\s+@)", "Uploading a file with curl can exfiltrate sensitive data. Review the exact payload and destination outside the agent."),
    ]
    for pattern, reason in checks:
        if re.search(pattern, stripped):
            deny(f"BLOCKED: {reason}")

    force_push = re.search(r"\bgit\s+push\b", stripped) and re.search(r"(?:--force\b|-f\b)", stripped)
    if force_push and not re.search(r"--force-with-lease\b", stripped) and re.search(r"\b(?:main|master)\b", stripped):
        deny("BLOCKED: bare force-push to main or master rewrites shared history. Use a PR, or `--force-with-lease` on an authorized feature branch.")

    if (
        re.search(r"\brm\b", stripped)
        and re.search(r"(?:-[A-Za-z]*[rR][A-Za-z]*f|-[A-Za-z]*f[A-Za-z]*[rR]|--recursive.*--force|--force.*--recursive)", stripped)
        and re.search(r"(?:^|\s)(?:\.|\.\.|~|/|/\*|\*)(?:\s|$)", stripped)
    ):
        deny("BLOCKED: recursive forced deletion targets a broad path. Resolve and delete a specific narrow directory instead.")


def check_shell_paths(command: str, cwd: Path) -> None:
    try:
        tokens = shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return
    for token in tokens:
        candidate = token.strip(";,()")
        if not candidate or candidate.startswith("-") or candidate in {"|", "&&", "||"}:
            continue
        looks_like_path = "/" in candidate or "\\" in candidate or candidate.startswith((".", "~", "$"))
        if not looks_like_path:
            continue
        path = normalized(candidate, cwd)
        if is_sensitive(path):
            deny(f"BLOCKED: shell access to protected credential path `{candidate}`. Handle secrets manually outside Codex.")


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001 - safety guard must fail closed
        fail_closed(f"invalid JSON payload: {exc}")
    if not isinstance(payload, dict):
        fail_closed("payload must be an object")

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        fail_closed("tool_input must be an object")
    cwd = normalized(str(payload.get("cwd") or os.getcwd()), Path.cwd())
    permission_mode = str(payload.get("permission_mode") or "default")

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not isinstance(command, str):
            fail_closed("Bash.command must be a string")
        check_destructive(command)
        check_shell_paths(command, cwd)
        return

    if tool_name == "apply_patch":
        command = tool_input.get("command", "")
        if not isinstance(command, str):
            fail_closed("apply_patch.command must be a string")
        for value in patch_paths(command):
            path = normalized(value, cwd)
            if is_sensitive(path):
                deny(f"BLOCKED: patch targets protected credential path `{value}`.")
            if is_guardrail(path) and permission_mode in {"bypassPermissions", "dontAsk"}:
                deny(f"BLOCKED: patch targets Codex guardrail `{value}`. Edit trusted agent configuration manually and review it with `/hooks`.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - safety guard must fail closed
        fail_closed(f"{type(exc).__name__}: {exc}")
