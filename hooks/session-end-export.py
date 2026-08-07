#!/usr/bin/env python3
"""SessionEnd hook: export the current session to Obsidian markdown and update QMD.

The QMD refresh is spawned detached so it doesn't block terminal exit or trip the
hook timeout — embedding a batch of sessions takes longer than the 30s budget.
Its output lands in LOG_FILE rather than being swallowed.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

EXPORT_SCRIPT = Path.home() / "Source" / "agent-skills" / "skills" / "recall" / "export_sessions.py"
LOG_FILE = Path.home() / ".claude" / "logs" / "session-end-export.log"


def resolve_qmd():
    """Return a runnable qmd command, or None if QMD isn't installed.

    Prefers `node <entry>.js` over the PATH shim: the shim is a .cmd/.ps1 wrapper
    whose location moves whenever the Node install changes.
    """
    shim = shutil.which("qmd")
    if not shim:
        return None

    node = shutil.which("node")
    if node:
        entry = Path(shim).parent / "node_modules" / "@tobilu" / "qmd" / "dist" / "cli" / "qmd.js"
        if entry.exists():
            return [node, str(entry)]

    return [shim]


def refresh_qmd():
    """Re-index and re-embed. Runs in the detached child."""
    qmd = resolve_qmd()
    if not qmd:
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log:
        for command in ("update", "embed"):
            result = subprocess.run([*qmd, command], stdout=log, stderr=subprocess.STDOUT)
            if result.returncode != 0:
                log.write(f"qmd {command} exited {result.returncode}\n")
                return


def main():
    if "--refresh" in sys.argv:
        refresh_qmd()
        return

    # 1. Export sessions (incremental — skips already-exported)
    subprocess.run([sys.executable, str(EXPORT_SCRIPT)], capture_output=True)

    # 2. Hand the QMD refresh to a detached child and return immediately
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--refresh"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )


if __name__ == "__main__":
    main()
