#!/usr/bin/env bash
set -euo pipefail

# Sync agent-skills repo content and push to remote.
# Usage:
#   ./sync.sh                    # commit and push all changes
#   ./sync.sh skills             # only skills/
#   ./sync.sh commands agents    # only commands/ and agents/
#   ./sync.sh -m "custom msg"    # custom commit message
#
# Valid folder targets: skills, commands, agents, config

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

VALID_FOLDERS=(skills commands agents config)
FOLDERS=()
MESSAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--message)
            MESSAGE="$2"
            shift 2
            ;;
        *)
            # Validate folder name
            found=false
            for valid in "${VALID_FOLDERS[@]}"; do
                if [[ "$1" == "$valid" ]]; then
                    found=true
                    break
                fi
            done
            if $found; then
                FOLDERS+=("$1")
            else
                echo "Error: unknown folder '$1'. Valid: ${VALID_FOLDERS[*]}"
                exit 1
            fi
            shift
            ;;
    esac
done

# If no folders specified, add everything
if [[ ${#FOLDERS[@]} -eq 0 ]]; then
    git add -A
else
    for folder in "${FOLDERS[@]}"; do
        git add "$folder/"
    done
fi

# Check if there's anything to commit
if git diff --cached --quiet; then
    echo "Nothing to commit."
    exit 0
fi

# Build commit message
if [[ -z "$MESSAGE" ]]; then
    if [[ ${#FOLDERS[@]} -eq 0 ]]; then
        MESSAGE="update agent-skills"
    else
        MESSAGE="update ${FOLDERS[*]}"
    fi
fi

git commit -m "$MESSAGE"
git push

echo "Synced and pushed."
