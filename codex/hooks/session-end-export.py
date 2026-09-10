#!/usr/bin/env python3
"""Coalesce Codex transcript refresh requests into one detached worker."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "skills" / "recall" / "scripts" / "export_sessions.py"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
LOG = CODEX_HOME / "logs" / "session-end-export.log"
LOCK = CODEX_HOME / "logs" / "session-recall.lock"
PENDING = CODEX_HOME / "logs" / "session-recall.pending"


def log_line(log, message: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log.write(f"[{stamp}] {message}\n")
    log.flush()


def run_refresh(log) -> bool:
    result = subprocess.run(
        [sys.executable, str(EXPORTER), "--skip-claude"],
        text=True,
        capture_output=True,
        check=False,
    )
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
