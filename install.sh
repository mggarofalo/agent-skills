#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

if [[ ! -d "$CLAUDE_DIR" ]]; then
    echo "Error: $CLAUDE_DIR does not exist. Install Claude Code first."
    exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_DIR/backups/agent-skills-$TIMESTAMP"
made_backup=false

backup() {
    local target="$1"
    if [[ ! -e "$target" ]]; then
        return
    fi
    if [[ -L "$target" ]]; then
        # Already a symlink — remove it, no backup needed
        rm "$target"
        return
    fi
    if ! $made_backup; then
        mkdir -p "$BACKUP_DIR"
        made_backup=true
    fi
    local name
    name="$(basename "$target")"
    echo "  Backing up $target -> $BACKUP_DIR/$name"
    mv "$target" "$BACKUP_DIR/$name"
}

link_dir() {
    local src="$1"
    local dest="$2"
    local current
    if [[ -L "$dest" ]]; then
        current="$(readlink -f "$dest")"
        if [[ "$current" == "$(readlink -f "$src")" ]]; then
            echo "  [ok] $dest -> $src (already linked)"
            return
        fi
    fi
    backup "$dest"
    ln -s "$src" "$dest"
    echo "  [linked] $dest -> $src"
}

link_file() {
    local src="$1"
    local dest="$2"
    if [[ ! -f "$src" ]]; then
        echo "  [skip] $src does not exist"
        return
    fi
    local current
    if [[ -L "$dest" ]]; then
        current="$(readlink -f "$dest")"
        if [[ "$current" == "$(readlink -f "$src")" ]]; then
            echo "  [ok] $dest -> $src (already linked)"
            return
        fi
    fi
    backup "$dest"
    ln -s "$src" "$dest"
    echo "  [linked] $dest -> $src"
}

echo "Installing agent-skills from $REPO_DIR"
echo ""

# Symlink directories
link_dir "$REPO_DIR/skills"   "$CLAUDE_DIR/skills"
link_dir "$REPO_DIR/commands" "$CLAUDE_DIR/commands"
link_dir "$REPO_DIR/agents"   "$CLAUDE_DIR/agents"

# Symlink individual files
link_file "$REPO_DIR/config/statusline.py"    "$CLAUDE_DIR/statusline.py"
link_file "$REPO_DIR/config/keybindings.json" "$CLAUDE_DIR/keybindings.json"

# Copy settings.json.example if settings.json doesn't exist
if [[ ! -f "$CLAUDE_DIR/settings.json" ]]; then
    cp "$REPO_DIR/config/settings.json.example" "$CLAUDE_DIR/settings.json"
    echo "  [created] $CLAUDE_DIR/settings.json from template"
else
    echo "  [skip] $CLAUDE_DIR/settings.json already exists"
fi

echo ""
echo "Done."
if $made_backup; then
    echo "Backups saved to: $BACKUP_DIR"
fi
echo ""
echo "Optional next steps:"
echo "  cd $REPO_DIR/agents/pr-bug-finder && pip install -e ."
echo "  Create .env files for agents that need API keys"
