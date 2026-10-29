#!/usr/bin/env python3
"""Install the Codex-native layer without changing the Claude Code setup."""

from __future__ import annotations

import os
import shutil
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
SOURCE = REPO / "codex"
HOME = Path.home()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", HOME / ".codex"))
AGENTS_HOME = HOME / ".agents"
BACKUP = CODEX_HOME / "backups" / f"agent-skills-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
made_backup = False


def backup(target: Path) -> None:
    global made_backup
    if not target.exists() and not target.is_symlink():
        return
    if target.is_symlink():
        target.unlink()
        return
    BACKUP.mkdir(parents=True, exist_ok=True)
    made_backup = True
    destination = BACKUP / target.name
    shutil.move(str(target), str(destination))
    print(f"  [backup] {target} -> {destination}")


def link(source: Path, target: Path, *, directory: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() and target.resolve() == source.resolve():
        print(f"  [ok] {target} -> {source}")
        return
    backup(target)
    target.symlink_to(source, target_is_directory=directory)
    print(f"  [linked] {target} -> {source}")


def insert_setting(text: str, section: str, key: str, value: str) -> str:
    header = f"[{section}]"
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == header), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([header, f"{key} = {value}"])
        return "\n".join(lines) + "\n"

    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].lstrip().startswith("[")),
        len(lines),
    )
    if any(line.split("=", 1)[0].strip() == key for line in lines[start + 1 : end] if "=" in line):
        return text
    lines.insert(start + 1, f"{key} = {value}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def configure() -> None:
    config = CODEX_HOME / "config.toml"
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("", encoding="utf-8")
    original = config.read_text(encoding="utf-8")
    updated = insert_setting(original, "features", "hooks", "true")
    tui_source = tomllib.loads((SOURCE / "config" / "tui.toml").read_text(encoding="utf-8"))
    status_line = tui_source["tui"]["status_line"]
    status_line_toml = "[" + ", ".join(f'"{item}"' for item in status_line) + "]"
    updated = insert_setting(updated, "tui", "status_line", status_line_toml)
    if updated != original:
        snapshot = config.with_name(f"config.toml.bak-agent-skills-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}")
        shutil.copy2(config, snapshot)
        config.write_text(updated, encoding="utf-8")
        print(f"  [updated] {config} (backup: {snapshot.name})")
    else:
        print(f"  [ok] {config} already enables hooks and configures the status line")


def main() -> None:
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    AGENTS_HOME.mkdir(parents=True, exist_ok=True)
    print(f"Installing Codex layer from {SOURCE}")
    link(SOURCE / "skills", AGENTS_HOME / "skills", directory=True)
    link(SOURCE / "hooks", CODEX_HOME / "hooks", directory=True)
    link(REPO / "router", CODEX_HOME / "agent-router", directory=True)
    link(SOURCE / "agents", CODEX_HOME / "agents", directory=True)
    link(SOURCE / "config" / "hooks.json", CODEX_HOME / "hooks.json", directory=False)
    configure()
    print("Done. Review changed hook definitions with /hooks in a new Codex session.")
    if made_backup:
        print(f"Previous Codex files were preserved under {BACKUP}.")


if __name__ == "__main__":
    main()
