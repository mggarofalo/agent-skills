#!/usr/bin/env python3
"""SessionEnd hook: export the current session to Obsidian markdown and update QMD.

Runs asynchronously so it doesn't block terminal exit.
"""

import subprocess
import sys
from pathlib import Path

EXPORT_SCRIPT = Path.home() / "Source" / "agent-skills" / "skills" / "recall" / "export_sessions.py"
QMD_NODE = Path.home() / "AppData" / "Roaming" / "fnm" / "node-versions" / "v22.22.1" / "installation" / "node.exe"
QMD_SCRIPT = QMD_NODE.parent / "node_modules" / "@tobilu" / "qmd" / "dist" / "qmd.js"


def main():
    # 1. Export sessions (incremental — skips already-exported)
    subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT)],
        capture_output=True,
    )

    # 2. Update QMD index and embeddings (if QMD is installed)
    if QMD_NODE.exists() and QMD_SCRIPT.exists():
        subprocess.run(
            [str(QMD_NODE), str(QMD_SCRIPT), "update"],
            capture_output=True,
        )
        subprocess.run(
            [str(QMD_NODE), str(QMD_SCRIPT), "embed"],
            capture_output=True,
        )


if __name__ == "__main__":
    main()
