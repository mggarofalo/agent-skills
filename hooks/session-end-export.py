#!/usr/bin/env python3
"""Stop / SubagentStop / PostCompact / SessionEnd hook: refresh Claude session recall.

The hook itself only touches a PENDING marker and spawns a detached worker, so it
returns in milliseconds and never blocks the session (it always exits 0; exit 2
on Stop would prevent Claude from stopping).

The worker holds a non-blocking file lock (flock, or msvcrt on Windows). Any
request arriving while it runs just re-touches PENDING, and the worker loops
until no request is pending, so bursts of hook events coalesce into at most one
extra refresh. Each refresh runs the
incremental exporter and calls `qmd update` + `qmd embed -c Claude-sessions` only
when an export actually changed. Output goes to LOG.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "skills" / "recall" / "export_sessions.py"
LOG_DIR = Path(os.environ.get("CLAUDE_RECALL_LOG_DIR", Path.home() / ".claude" / "logs"))
LOG = LOG_DIR / "session-end-export.log"
LOCK = LOG_DIR / "session-recall.lock"
PENDING = LOG_DIR / "session-recall.pending"
COLLECTION = "Claude-sessions"
LOG_MAX_BYTES = 1_000_000
EXPORT_TIMEOUT = 300
QMD_TIMEOUTS = {"update": 300, "embed": 1800}
# Hooks may run with a minimal PATH; qmd is a `#!/usr/bin/env node` script.
EXTRA_PATH = ("/opt/homebrew/bin", "/usr/local/bin")
# Windows ignores start_new_session. Its own process group keeps the worker
# out of the session's Ctrl+C, and a hidden console is inherited by the
# exporter and qmd children instead of each flashing a window. Both are 0 on POSIX.
DETACH_FLAGS = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)


def resolve_qmd():
    """Return a runnable qmd command, or None if QMD isn't installed.

    CLAUDE_RECALL_QMD overrides discovery (empty string disables QMD).
    Prefers `node <entry>.js` over the PATH shim: the shim is a .cmd/.ps1 wrapper
    whose location moves whenever the Node install changes.
    """
    override = os.environ.get("CLAUDE_RECALL_QMD")
    if override is not None:
        return [override] if override else None

    search = os.pathsep.join([os.environ.get("PATH", ""), *EXTRA_PATH])
    shim = shutil.which("qmd", path=search)
    if not shim:
        return None

    node = shutil.which("node", path=search)
    if node:
        entry = Path(shim).parent / "node_modules" / "@tobilu" / "qmd" / "dist" / "cli" / "qmd.js"
        if entry.exists():
            return [node, str(entry)]

    return [shim]


def log_line(log, message: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    log.write(f"[{stamp}] {message}\n")
    log.flush()


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([env.get("PATH", ""), *EXTRA_PATH])
    return env


def run_refresh(log) -> bool:
    """Export once; refresh QMD only if an export changed. Returns success."""
    try:
        result = subprocess.run(
            [sys.executable, str(EXPORTER), "--json"],
            text=True, capture_output=True, check=False, timeout=EXPORT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log_line(log, f"export timed out after {EXPORT_TIMEOUT}s")
        return False
    if result.stderr:
        log.write(result.stderr)
    if result.returncode != 0:
        log_line(log, f"export failed with exit {result.returncode}: {result.stdout.strip()[:500]}")
        return False
    try:
        stats = json.loads(result.stdout)
        changed = stats["exported"]
        log_line(log, "export " + json.dumps({k: v for k, v in stats.items() if v and k != "errors"}))
        for error in stats.get("errors") or []:
            log_line(log, f"export error: {error}")
    except (json.JSONDecodeError, KeyError, TypeError):
        log_line(log, f"unreadable exporter output; assuming changes: {result.stdout.strip()[:500]}")
        changed = 1
    if not changed:
        log_line(log, "no session changes; skipped QMD refresh")
        return True

    qmd = resolve_qmd()
    if not qmd:
        log_line(log, "qmd is unavailable; exports remain ready for a later refresh")
        return True
    for command in (["update"], ["embed", "-c", COLLECTION]):
        timeout = QMD_TIMEOUTS[command[0]]
        try:
            completed = subprocess.run(
                [*qmd, *command], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                env=child_env(), check=False, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            log_line(log, f"qmd {' '.join(command)} timed out after {timeout}s")
            return False
        if completed.returncode != 0:
            log_line(log, f"qmd {' '.join(command)} failed with exit {completed.returncode}")
            return False
    return True


def rotate_log() -> None:
    try:
        if LOG.stat().st_size > LOG_MAX_BYTES:
            LOG.replace(LOG.with_name(LOG.name + ".1"))
    except FileNotFoundError:
        pass


def drain_pending(log) -> None:
    while PENDING.exists():
        PENDING.unlink(missing_ok=True)
        log_line(log, "refresh started")
        try:
            ok = run_refresh(log)
        except Exception:  # keep the worker alive; the next request retries
            log.write(traceback.format_exc())
            ok = False
        log_line(log, f"refresh {'finished' if ok else 'failed'}")


def try_lock(handle) -> bool:
    """Take an exclusive lock on an open file without waiting; False if it is held."""
    if fcntl is not None:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def unlock(handle) -> None:
    # Windows may release a lock some time after close; the PENDING re-check
    # below must not race a stale lock, so release it explicitly.
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_UN)
    else:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def worker() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        with LOCK.open("a+") as lock:
            if not try_lock(lock):
                PENDING.touch()  # the lock holder re-checks PENDING after releasing
                return
            try:
                rotate_log()
                with LOG.open("a", encoding="utf-8") as log:
                    drain_pending(log)
            finally:
                unlock(lock)
        # A request may have landed between the last check and the unlock, and
        # its worker would have lost the lock race; pick it up here.
        if not PENDING.exists():
            return


def spawn_worker() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PENDING.touch()
    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--worker"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        creationflags=DETACH_FLAGS,
        close_fds=True,
    )


def main() -> int:
    try:
        if "--worker" in sys.argv:
            worker()
        else:
            spawn_worker()
    except Exception as error:  # never block or fail the session over recall
        try:
            with LOG.open("a", encoding="utf-8") as log:
                log_line(log, f"hook error: {error!r}")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
