#!/usr/bin/env python3
"""Coalesce Codex transcript refresh requests into one detached worker.

Hosted mode (hooks/memoria_push.py at the repository root) is off unless its
config file turns it on. When on, a SessionEnd also touches PUSH_PENDING, and the
worker sends changed rollouts to Memoria after the export and before QMD. When
off, none of this reads stdin, opens a socket or writes a file.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "skills" / "recall" / "scripts" / "export_sessions.py"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
LOG = CODEX_HOME / "logs" / "session-end-export.log"
LOCK = CODEX_HOME / "logs" / "session-recall.lock"
PENDING = CODEX_HOME / "logs" / "session-recall.pending"
PUSH_PENDING = CODEX_HOME / "logs" / "memoria-push.pending"
PUSH_MODULE = Path(__file__).resolve().parents[2] / "hooks" / "memoria_push.py"
PUSH_STATE = Path(os.environ.get("CODEX_RECALL_PUSH_STATE", CODEX_HOME / "memoria-push"))


def log_line(log, message: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log.write(f"[{stamp}] {message}\n")
    log.flush()


def load_push():
    spec = importlib.util.spec_from_file_location("memoria_push", PUSH_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["memoria_push"] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


def request_push() -> None:
    """In the hook process: mark a push for the worker on SessionEnd, if hosted mode is on."""
    if not PUSH_MODULE.is_file():  # a copied install has no hosted mode, and says nothing
        return
    push = load_push()
    if not push.push_enabled():
        return
    if push.read_hook_input().get("hook_event_name") == "SessionEnd":
        PUSH_PENDING.touch()


def push_if_requested(log) -> None:
    """In the worker: send to Memoria if a SessionEnd asked. Never raises."""
    if not PUSH_MODULE.is_file():
        return
    try:
        push = load_push()
        try:
            settings = push.load_settings()
        except push.ConfigError as error:
            if PUSH_PENDING.exists():
                PUSH_PENDING.unlink()
                log_line(log, f"memoria: push is not configured correctly: {error}")
            return
        if settings is None or not PUSH_PENDING.exists():
            return
        PUSH_PENDING.unlink()
        push.run(settings, push.codex_sources(CODEX_HOME), PUSH_STATE, lambda message: log_line(log, message))
    except Exception:
        log.write(traceback.format_exc())


def run_refresh(log) -> bool:
    result = subprocess.run(
        [sys.executable, str(EXPORTER), "--skip-claude"],
        text=True,
        capture_output=True,
        check=False,
    )
    # Rollouts, not exports, are what is pushed, so a failed export does not stop it.
    push_if_requested(log)
    if result.stdout:
        log.write(result.stdout)
    if result.stderr:
        log.write(result.stderr)
    if result.returncode != 0:
        log_line(log, f"export failed with exit {result.returncode}")
        return False
    try:
        payload = json.loads(result.stdout)
        changed = payload["codex"]["exported"]
    except (json.JSONDecodeError, KeyError, TypeError):
        changed = 1
    if not changed:
        log_line(log, "no transcript changes; skipped QMD refresh")
        return True
    qmd = shutil.which("qmd")
    if not qmd:
        log_line(log, "qmd is unavailable; exports remain ready for a later refresh")
        return True
    for command in ([qmd, "update"], [qmd, "embed", "-c", "Codex-sessions"]):
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        if completed.returncode != 0:
            log_line(log, f"{' '.join(command)} failed with exit {completed.returncode}")
            return False
    return True


def worker() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as lock, LOG.open("a", encoding="utf-8") as log:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            PENDING.touch()
            return
        while True:
            try:
                PENDING.unlink()
            except FileNotFoundError:
                pass
            log_line(log, "refresh started")
            run_refresh(log)
            log_line(log, "refresh finished")
            if not PENDING.exists():
                break


def main() -> None:
    if "--worker" in sys.argv:
        worker()
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        request_push()
    except Exception as error:  # a broken push must not stop the local refresh
        with LOG.open("a", encoding="utf-8") as log:
            log_line(log, f"memoria: push request failed: {error!r}")
    PENDING.touch()
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--worker"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )


if __name__ == "__main__":
    main()
