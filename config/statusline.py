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

# ── Line 3: cost + duration + tokens ──────────────────────────────────────────
cost        = data.get("cost", {}).get("total_cost_usd", 0) or 0
duration_ms = data.get("cost", {}).get("total_duration_ms", 0) or 0
total_in    = data.get("context_window", {}).get("total_input_tokens", 0) or 0
total_out   = data.get("context_window", {}).get("total_output_tokens", 0) or 0

total_sec = int(duration_ms) // 1000
if total_sec >= 3600:
    hrs, rem = total_sec // 3600, total_sec % 3600
    duration_str = f"{hrs}h{rem // 60:02d}m"
else:
    duration_str = f"{total_sec // 60}m{total_sec % 60:02d}s"

total_tokens = int(total_in) + int(total_out)
if total_tokens >= 1_000_000:
    tok_str = f"{total_tokens / 1_000_000:.1f}M"
elif total_tokens >= 1_000:
    tok_str = f"{total_tokens / 1_000:.0f}k"
else:
    tok_str = str(total_tokens)

line3 = (
    f"{GREEN}💰 ${cost:.2f}{RESET}"
    f"  {CYAN}⏱️  {duration_str}{RESET}"
    f"  {BLUE}📊 {tok_str} tok{RESET}"
)

# ── Line 4: literary vibes — deterministic by context % ───────────────────────
# Mood escalates with context usage across five worlds.
try:
    pct = int(round(float(used_str))) if used_str else 0
except ValueError:
    pct = 0

VIBES = [
    # (max_pct, emoji, quote)
    ( 5, "🧁", "Friar Hugo is laying out scones and meadowcream in Cavern Hole"),
    (10, "🦁", "Further up and further in!"),
    (15, "🧙", "Not all those who wander are lost"),
    (20, "🏜️", "A beginning is the time for taking the most delicate care"),
    (25, "📜", "The Consul listened to the roses singing in the ship-tree forest"),
    (30, "🐿️", "The Dibbuns are splashing in the Abbey pond"),
    (35, "🚪", "One day you'll be old enough to start reading fairy tales again"),
    (40, "🌿", "The world is indeed full of peril, and in it there are many dark places"),
    (45, "🪱", "Deep in the human unconscious is the need for a logical universe"),
    (50, "📖", "Between the pain and its absence, there is a universe of meaning"),
    (55, "🍺", "October Ale is flowing freely in Great Hall"),
    (58, "⛵", "To live in a world where Aslan is on the move — anything can happen"),
    (62, "🗡️", "Even the smallest person can change the course of the future"),
    (66, "⏳", "The spice must flow"),
    (70, "🌀", "The Time Tombs are opening"),
    (74, "🔭", "Watchers on the walltop scan the horizon"),
    (78, "❄️", "Always winter and never Christmas"),
    (82, "🔥", "The beacons of Minas Tirith! The beacons are lit!"),
    (86, "⚔️", "Fear is the mind-killer — face it and let it pass through you"),
    (90, "🐀", "The Shrike stirs in the Valley of the Time Tombs"),
    (93, "🔔", "Ring the bells! Man the ramparts! Redwaaaall!"),
    (96, "🦅", "The eagles are coming!"),
    (98, "🐛", "The sleeper has awakened"),
    (100,"🗡️", "Martin's sword has been drawn from the tapestry"),
]

for max_pct, emoji, msg in VIBES:
    if pct <= max_pct:
        line4 = f"{emoji} {DIM}{msg}{RESET}"
        break
else:
    line4 = f"{VIBES[-1][1]} {DIM}{VIBES[-1][2]}{RESET}"

# ── Output ────────────────────────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
print(line1)
print(line2)
print(line3)
print(line4)
