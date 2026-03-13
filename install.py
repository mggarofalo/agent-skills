#!/usr/bin/env python3
"""Install agent-skills by symlinking into ~/.claude/.

Creates directory symlinks for skills, commands, agents, and hooks;
and file symlinks for statusline and keybindings.
Backs up any existing non-symlink targets before replacing them.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
CLAUDE_DIR: Path | None = None

# Resolve ~/.claude cross-platform
for candidate in [
    Path.home() / ".claude",
    Path(os.environ.get("USERPROFILE", "")) / ".claude",
]:
    if candidate.is_dir():
        CLAUDE_DIR = candidate
        break

if CLAUDE_DIR is None:
    print("Error: Cannot find ~/.claude directory. Install Claude Code first.")
    sys.exit(1)

TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP_DIR = CLAUDE_DIR / "backups" / f"agent-skills-{TIMESTAMP}"
made_backup = False


def backup(target: Path) -> None:
    """Back up a target path, or remove it if it's already a symlink."""
    global made_backup
    if not target.exists() and not target.is_symlink():
        return
    if target.is_symlink():
        target.unlink()
        return
    if not made_backup:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        made_backup = True
    dest = BACKUP_DIR / target.name
    print(f"  Backing up {target} -> {dest}")
    shutil.move(str(target), str(dest))


def link_dir(src: Path, dest: Path) -> None:
    """Create a directory symlink, backing up any existing target."""
    if dest.is_symlink() and dest.resolve() == src.resolve():
        print(f"  [ok] {dest} -> {src} (already linked)")
        return
    backup(dest)
    dest.symlink_to(src, target_is_directory=True)
    print(f"  [linked] {dest} -> {src}")


def link_file(src: Path, dest: Path) -> None:
    """Create a file symlink, backing up any existing target."""
    if not src.is_file():
        print(f"  [skip] {src} does not exist")
        return
    if dest.is_symlink() and dest.resolve() == src.resolve():
        print(f"  [ok] {dest} -> {src} (already linked)")
        return
    backup(dest)
    dest.symlink_to(src)
    print(f"  [linked] {dest} -> {src}")


print(f"Installing agent-skills from {REPO_DIR}")
print()

# Symlink directories
link_dir(REPO_DIR / "skills", CLAUDE_DIR / "skills")
link_dir(REPO_DIR / "commands", CLAUDE_DIR / "commands")
link_dir(REPO_DIR / "agents", CLAUDE_DIR / "agents")

link_dir(REPO_DIR / "hooks", CLAUDE_DIR / "hooks")
link_dir(REPO_DIR / "scripts", CLAUDE_DIR / "scripts")

# Symlink individual config files
link_file(REPO_DIR / "config" / "statusline.py", CLAUDE_DIR / "statusline-command.py")
link_file(REPO_DIR / "config" / "keybindings.json", CLAUDE_DIR / "keybindings.json")

# Copy settings.json template if settings.json doesn't exist
settings_path = CLAUDE_DIR / "settings.json"
if not settings_path.exists():
    shutil.copy2(REPO_DIR / "config" / "settings.json.example", settings_path)
    print(f"  [created] {settings_path} from template")
else:
    print(f"  [skip] {settings_path} already exists")

# Install Python agent packages (any agents/<name>/pyproject.toml)
for toml in sorted((REPO_DIR / "agents").glob("*/pyproject.toml")):
    agent_dir = toml.parent
    print(f"  [install] {agent_dir.name}")
    if shutil.which("uv"):
        subprocess.run(["uv", "pip", "install", "--system", "-e", str(agent_dir)], check=True)
    else:
        print("    uv not found — falling back to pip")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(agent_dir)], check=True)

print()
print("Done.")
if made_backup:
    print(f"Backups saved to: {BACKUP_DIR}")
