#!/usr/bin/env python3
import json, sys, subprocess, os

data = json.load(sys.stdin)

# Line 1: git/worktree info
parts = []
cwd = data.get("cwd", "")
worktree = data.get("worktree")

# Check if we're in a git repo
try:
    subprocess.run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"],
                   capture_output=True, timeout=2, check=True)
    is_git = True
except Exception:
    is_git = False

if is_git:
    parts.append("")  # git icon

if worktree:
    parts.append("")  # worktree icon

if is_git:
    try:
        result = subprocess.run(["git", "-C", cwd, "branch", "--show-current"],
                                capture_output=True, text=True, timeout=2)
        branch = result.stdout.strip()
        if branch:
            parts.append(f" {branch}")
    except Exception:
        pass

if parts:
    print(" ".join(parts))

# Line 2: model (effort) | ctx N%
model = data.get("model", {}).get("display_name", "")
used = data.get("context_window", {}).get("used_percentage")

line2 = model
if used is not None:
    line2 += f"  ctx {int(used)}%"

print(line2)
