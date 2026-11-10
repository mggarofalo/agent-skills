#!/usr/bin/env python3
"""Say which search backend /recall uses, and run a Memoria search through the memoria CLI.

    recall_backend.py                 print {"backend": "qmd"} or {"backend": "memoria", ...}
    recall_backend.py query TEXT ...  run `memoria query` over the session collections

Local QMD is the default. Memoria is used only when the config file (the same one
the session-end hook reads, ~/.config/agent-skills/memoria.json) sets
`"search": "memoria"`.

Searches go through the memoria CLI rather than over HTTP from here, so the key
is found, bound to its server and kept off the command line exactly as the CLI
does it (`MEMORIA_API_KEY`, or the keyring login from `memoria auth login`), and
its markdown output is already sanitized. This script never reads a key.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

CONFIG_ENV = "AGENT_SKILLS_MEMORIA_CONFIG"
DEFAULT_COLLECTIONS = {"claude": "claude-sessions", "codex": "codex-sessions"}
QMD_COLLECTIONS = {"claude": "Claude-sessions", "codex": "Codex-sessions"}


class ConfigError(Exception):
    pass


def config_path() -> Path:
    """Kept the same as hooks/memoria_push.py's config_path."""
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME", "")
    root = Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    return root / "agent-skills" / "memoria.json"


def read_config() -> dict:
    path = config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        raise ConfigError(f"cannot read {path}: {error}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must hold a JSON object")
    return data


def describe(data: dict) -> dict:
    if data.get("search") != "memoria":
        return {"backend": "qmd", "collections": QMD_COLLECTIONS}
    collections = dict(DEFAULT_COLLECTIONS)
    if isinstance(data.get("collections"), dict):
        collections.update({k: v for k, v in data["collections"].items() if isinstance(v, str) and v})
    cli = data.get("cli") or shutil.which("memoria")
    return {
        "backend": "memoria",
        "collections": collections,
        "profile": data.get("profile"),
        "url": data.get("url"),
        "cli": cli,
    }


def query_command(info: dict, args: argparse.Namespace) -> list:
    command = [info["cli"]]
    if info.get("profile"):
        command += ["--profile", info["profile"]]
    if info.get("url"):
        command += ["--api-url", info["url"]]
    command += ["query", "--format", args.format]
    harnesses = ["claude", "codex"] if args.harness == "both" else [args.harness]
    for harness in harnesses:
        command += ["--collection", info["collections"][harness]]
    for flag in ("intent", "limit", "since", "until", "min_score"):
        value = getattr(args, flag)
        if value is not None:
            command += [f"--{flag.replace('_', '-')}", str(value)]
    for project in args.project or []:
        command += ["--project", project]
    if args.no_rerank:
        command.append("--no-rerank")
    return [*command, "--", args.text]  # "--" keeps a query that starts with "-" a query


def parse(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")
    query = sub.add_parser("query", help="search Memoria through the memoria CLI")
    query.add_argument("text")
    query.add_argument("--harness", choices=["claude", "codex", "both"], default="both")
    query.add_argument("--intent")
    query.add_argument("--limit", type=int)
    query.add_argument("--min-score", type=float)
    query.add_argument("--since")
    query.add_argument("--until")
    query.add_argument("--project", action="append")
    query.add_argument("--no-rerank", action="store_true")
    query.add_argument("--format", choices=["markdown", "json", "table"], default="markdown")
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse(sys.argv[1:] if argv is None else argv)
    try:
        info = describe(read_config())
    except ConfigError as error:
        print(f"recall: {error}", file=sys.stderr)
        return 2
    if args.command is None:
        print(json.dumps(info))
        return 0
    if info["backend"] != "memoria":
        print("recall: search is set to local QMD; use the qmd tools", file=sys.stderr)
        return 2
    if not info["cli"]:
        print("recall: the memoria CLI is not on PATH; install it, or set \"cli\" in "
              f"{config_path()}", file=sys.stderr)
        return 127
    return subprocess.run(query_command(info, args), stdin=subprocess.DEVNULL, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
