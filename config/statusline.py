#!/usr/bin/env python3
"""Claude Code status line — Python port."""

import json
import math
import subprocess
import sys

# ── ANSI helpers ──────────────────────────────────────────────────────────────
def e(code):
    return f"\033[{code}m"

RESET   = e("0")
BOLD    = e("1")
DIM     = e("2")
CYAN    = e("36")
YELLOW  = e("33")
GREEN   = e("32")
RED     = e("31")
BLUE    = e("34")
MAGENTA = e("35")
WHITE   = e("37")
ORANGE  = e("38;5;214")

# ── Read + parse stdin ────────────────────────────────────────────────────────
raw = sys.stdin.read()
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    print("statusline: invalid JSON", file=sys.stderr)
    sys.exit(1)

def field(obj, *path, default=""):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return str(cur) if cur is not None else default

# ── Extract fields ────────────────────────────────────────────────────────────
cwd = field(data, "workspace", "current_dir") or field(data, "cwd") or "?"
model        = field(data, "model", "display_name") or "unknown model"
used_str     = field(data, "context_window", "used_percentage")
version      = field(data, "version")
output_style = field(data, "output_style", "name")
vim_mode     = field(data, "vim", "mode")
agent_name   = field(data, "agent", "name")
session_name = field(data, "session_name")

# ── Line 1: directory + git ───────────────────────────────────────────────────
import os
home = os.path.expanduser("~").replace("\\", "/")
display_dir = cwd.replace("\\", "/")
if display_dir.startswith(home):
    display_dir = "~" + display_dir[len(home):]

line1 = f"{BOLD}{CYAN}📁 {display_dir}{RESET}"

def git(*args):
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "-c", "gc.auto=0"] + list(args),
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None

if git("rev-parse", "--git-dir") is not None:
    branch = git("symbolic-ref", "--short", "HEAD") or git("rev-parse", "--short", "HEAD") or "?"

    # ── Worktree detection ────────────────────────────────────────────────────
    # Parse `git worktree list --porcelain` to find the main worktree path.
    # The first "worktree" entry is always the main worktree.
    # If our current toplevel differs from it, we are in a linked worktree.
    # Strip everything up to and including `.worktrees/` from the display name.
    worktree_name = None
    wt_list_raw = git("worktree", "list", "--porcelain") or ""
    current_toplevel = git("rev-parse", "--show-toplevel")
    if wt_list_raw and current_toplevel:
        entries = wt_list_raw.strip().split("\n\n")
        main_path = None
        for line in entries[0].splitlines():
            if line.startswith("worktree "):
                main_path = line[len("worktree "):].strip().replace("\\", "/")
                break
        current_toplevel_norm = current_toplevel.replace("\\", "/")
        if main_path and current_toplevel_norm != main_path:
            WORKTREES_MARKER = ".worktrees/"
            idx = current_toplevel_norm.find(WORKTREES_MARKER)
            if idx != -1:
                worktree_name = current_toplevel_norm[idx + len(WORKTREES_MARKER):]
            else:
                worktree_name = os.path.basename(current_toplevel_norm)

    status_out = git("status", "--porcelain") or ""
    added = modified = deleted = untracked = 0
    for gl in status_out.splitlines():
        if not gl:
            continue
        X, Y = gl[0], gl[1]
        if gl.startswith("??"):
            untracked += 1
        else:
            if X == 'A': added += 1
            if X == 'M' or Y == 'M': modified += 1
            if X == 'D' or Y == 'D': deleted += 1
            if X == 'R' or Y == 'R': added += 1  # renamed = added

    line1 += f"  {BOLD}{YELLOW}⎇  {branch}{RESET}"

    if worktree_name:
        line1 += f"  {DIM}{MAGENTA}⛓  worktree{RESET}"

    stats = ""
    if added:     stats += f"  {GREEN}+{added}{RESET}"
    if modified:  stats += f"  {ORANGE}~{modified}{RESET}"
    if deleted:   stats += f"  {RED}-{deleted}{RESET}"
    if untracked: stats += f"  {DIM}?{untracked}{RESET}"

    if stats:
        line1 += f"  [{stats} ]"
    else:
        line1 += f"  {GREEN}✔ clean{RESET}"

# ── Line 2: model + context + extras ─────────────────────────────────────────
line2 = f"{BOLD}{MAGENTA}🤖 {model}{RESET}"

if used_str:
    try:
        used = float(used_str)
        if used > 80:
            ctx_color = RED
        elif used > 50:
            ctx_color = ORANGE
        else:
            ctx_color = GREEN

        filled = round(used / 10)
        bar = "█" * filled + "░" * (10 - filled)
        line2 += f"  {ctx_color}📊 {bar} {round(used)}%{RESET}"
    except ValueError:
        pass

if version:
    line2 += f"  {DIM}{WHITE}v{version}{RESET}"

if output_style and output_style != "default":
    line2 += f"  {BLUE}✏️  {output_style}{RESET}"

if vim_mode:
    if vim_mode == "INSERT":
        vim_icon, vim_col = "✍️ ", GREEN
    elif vim_mode == "NORMAL":
        vim_icon, vim_col = "🔷", CYAN
    else:
        vim_icon, vim_col = "⌨️ ", WHITE
    line2 += f"  {vim_col}{vim_icon} {vim_mode}{RESET}"

if agent_name:
    line2 += f"  {YELLOW}🕵️  {agent_name}{RESET}"

if session_name:
    line2 += f"  {DIM}💬 {session_name}{RESET}"

# ── Output ────────────────────────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
print(line1)
print(line2)
