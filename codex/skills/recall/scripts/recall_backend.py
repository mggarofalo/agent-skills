#!/usr/bin/env python3
"""Codex entry point for the shared recall backend helper.

Runs skills/recall/recall_backend.py from the repository root, so Codex and
Claude Code read the same config file and build the same `memoria query`.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

SHARED = Path(
    os.environ.get(
        "RECALL_BACKEND_SHARED",
        Path(__file__).resolve().parents[4] / "skills" / "recall" / "recall_backend.py",
    )
)


def load_shared():
    spec = importlib.util.spec_from_file_location("recall_backend_shared", SHARED)
    if spec is None or spec.loader is None or not SHARED.is_file():
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    shared = load_shared()
    if shared is None:
        print(f"recall: the shared backend helper is missing at {SHARED}; local QMD and rg still work",
              file=sys.stderr)
        return 2
    return shared.main(argv)


if __name__ == "__main__":
    sys.exit(main())
