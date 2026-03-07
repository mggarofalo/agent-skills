#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Resolve ~/.claude cross-platform.
# - macOS / Linux: $HOME/.claude
# - Git Bash / MSYS2: cygpath $USERPROFILE, or /c/Users/$USER
# - WSL: /mnt/c/Users/$USER
CLAUDE_DIR="$HOME/.claude"
if [[ ! -d "$CLAUDE_DIR" ]] && [[ -n "${USERPROFILE:-}" ]] && command -v cygpath &>/dev/null; then
    CLAUDE_DIR="$(cygpath "$USERPROFILE")/.claude"
fi
if [[ ! -d "$CLAUDE_DIR" ]] && [[ -d "/c/Users/$(whoami)/.claude" ]]; then
    CLAUDE_DIR="/c/Users/$(whoami)/.claude"
fi
if [[ ! -d "$CLAUDE_DIR" ]] && [[ -d "/mnt/c/Users/$(whoami)/.claude" ]]; then
    CLAUDE_DIR="/mnt/c/Users/$(whoami)/.claude"
fi
if [[ ! -d "$CLAUDE_DIR" ]]; then
    echo "Error: Cannot find ~/.claude directory. Install Claude Code first."
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

# Hooks: use per-file symlinks (not directory symlink) because settings.json
# hooks must resolve at all times — a directory swap would break Bash mid-session.
mkdir -p "$CLAUDE_DIR/hooks"
for hook in "$REPO_DIR/hooks"/*.py; do
    link_file "$hook" "$CLAUDE_DIR/hooks/$(basename "$hook")"
done

# Symlink individual files
link_file "$REPO_DIR/config/statusline.py"    "$CLAUDE_DIR/statusline-command.py"
link_file "$REPO_DIR/config/keybindings.json" "$CLAUDE_DIR/keybindings.json"

# Copy settings.json.example if settings.json doesn't exist
if [[ ! -f "$CLAUDE_DIR/settings.json" ]]; then
    cp "$REPO_DIR/config/settings.json.example" "$CLAUDE_DIR/settings.json"
    echo "  [created] $CLAUDE_DIR/settings.json from template"
else
    echo "  [skip] $CLAUDE_DIR/settings.json already exists"
fi

# Install Python agent packages (any agents/<name>/pyproject.toml)
for toml in "$REPO_DIR/agents"/*/pyproject.toml; do
    [[ -f "$toml" ]] || continue
    agent_dir="$(dirname "$toml")"
    agent_name="$(basename "$agent_dir")"
    echo "  [install] $agent_name"
    if command -v uv &>/dev/null; then
        uv pip install --system -e "$agent_dir"
    else
        echo "    uv not found — falling back to pip"
        pip install -e "$agent_dir"
    fi
done

echo ""
echo "Done."
if $made_backup; then
    echo "Backups saved to: $BACKUP_DIR"
fi
