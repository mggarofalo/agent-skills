#!/usr/bin/env python3
"""Run a stateless, low-cost text worker through Claude Code or Codex."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 30
DEFAULT_MODELS = {
    "claude": "haiku",
    "codex": "gpt-5.6-luna",
}


class WorkerError(RuntimeError):
    """Raised when the delegated worker cannot return a usable result."""


def worker_command(host: str, system_prompt: str) -> list[str]:
    """Build a host-native, non-persistent worker command."""
    model = os.environ.get(f"AGENT_ROUTER_{host.upper()}_MODEL", DEFAULT_MODELS[host])
    if host == "claude":
        return [
            "claude",
            "--print",
            "--model",
            model,
            "--effort",
            "low",
            "--tools",
            "",
            "--no-session-persistence",
            "--disable-slash-commands",
            "--no-chrome",
            "--output-format",
            "text",
            "--system-prompt",
            system_prompt,
        ]
    if host == "codex":
        return [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--model",
            model,
            "--config",
            'model_reasoning_effort="low"',
            "--color",
            "never",
            "-",
        ]
    raise ValueError(f"unsupported host: {host}")


def run_worker(host: str, system_prompt: str, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run one worker request without creating a resumable local session."""
    if host not in DEFAULT_MODELS:
        raise WorkerError(f"unsupported host: {host}")
    worker_input = prompt
    if host == "codex":
        # codex exec has no system-prompt flag; place trusted mode instructions
        # before the tagged, untrusted payload in the one-shot prompt.
        worker_input = f"<worker-mode>\n{system_prompt}\n</worker-mode>\n{prompt}"
    try:
        with tempfile.TemporaryDirectory(prefix="agent-router-") as workdir:
            result = subprocess.run(
                worker_command(host, system_prompt),
                input=worker_input,
                text=True,
                capture_output=True,
                cwd=Path(workdir),
                timeout=timeout,
                check=False,
            )
    except FileNotFoundError as exc:
        raise WorkerError(f"{host} CLI is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise WorkerError(f"{host} worker exceeded the {timeout}-second cap") from exc

    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        detail = result.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise WorkerError(f"{host} worker failed with exit {result.returncode}{suffix}")
    return output
