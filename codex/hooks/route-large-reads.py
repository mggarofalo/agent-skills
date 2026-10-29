#!/usr/bin/env python3
"""Codex PreToolUse entry point for the shared large-file read router."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    router = Path.home() / ".codex" / "agent-router" / "read_guard.py"
    sys.argv = [str(router), "--host", "codex", "--kind", "bash"]
    runpy.run_path(str(router), run_name="__main__")


if __name__ == "__main__":
    main()
