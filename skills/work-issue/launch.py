#!/usr/bin/env python3
"""Launcher for the work-issue skill.

Builds a deterministic branch name from issue metadata, ensures the local
repo is up-to-date, and starts Claude Code in a worktree for that branch.

Usage:
    python launch.py --type feat --issue MGG-54 --title "Docker Compose Configuration"
    python launch.py --type feat --issue MGG-54 --title "Docker Compose Configuration" --dry-run
    python launch.py --type feat --issue MGG-54 --title "Docker Compose Configuration" --prompt "/work-issue MGG-54"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


VALID_TYPES = ("feat", "fix", "refactor", "chore", "docs", "test", "perf", "ci")


def slugify(text: str, max_words: int = 5) -> str:
    """Lowercase, replace non-alphanumeric with hyphens, collapse, truncate."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    words = slug.split("-")
    return "-".join(words[:max_words])


def build_branch_name(type_: str, issue: str, title: str) -> str:
    """Return '{type}/{issue-lower}-{slugified-title}'."""
    return f"{type_}/{issue.lower()}-{slugify(title)}"


def find_existing_branch(issue_id: str) -> str | None:
    """Search local + remote branches for the issue ID; return match or None."""
    issue_lower = issue_id.lower()
    try:
        result = subprocess.run(
            ["git", "branch", "-a", "--list", f"*{issue_lower}*"],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        return None

    for line in result.stdout.splitlines():
        branch = line.strip().lstrip("* ")
        # Strip remotes/origin/ prefix for remote-tracking branches
        if branch.startswith("remotes/origin/"):
            branch = branch[len("remotes/origin/"):]
        if issue_lower in branch.lower():
            return branch
    return None


def is_git_repo() -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
    ).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Claude Code for a Plane issue")
    parser.add_argument("--type", required=True, choices=VALID_TYPES, dest="type_",
                        help="Branch prefix (conventional commit style)")
    parser.add_argument("--issue", required=True, help="Issue ID, e.g. MGG-54")
    parser.add_argument("--title", required=True, help="Issue title")
    parser.add_argument("--prompt", default=None, help="Prompt for autonomous mode")
    parser.add_argument("--base", default="main", help="Base branch to branch from (default: main)")
    parser.add_argument("--dry-run", action="store_true", help="Print branch name and exit")
    args = parser.parse_args()

    branch = build_branch_name(args.type_, args.issue, args.title)

    if args.dry_run:
        print(branch)
        return 0

    if not is_git_repo():
        print("Error: not inside a git repository.", file=sys.stderr)
        return 1

    # Update base branch
    subprocess.run(["git", "checkout", args.base], check=True)
    pull = subprocess.run(["git", "pull", "--ff-only"], capture_output=True, text=True)
    if pull.returncode != 0:
        print(f"Warning: git pull --ff-only failed, continuing on current {args.base}.\n{pull.stderr}", file=sys.stderr)

    # Reuse existing branch if one matches the issue
    existing = find_existing_branch(args.issue)
    if existing:
        print(f"Reusing existing branch: {existing}")
        branch = existing

    # Build claude command
    cmd = ["claude", "-w", branch]
    if args.prompt:
        cmd.extend(["-p", args.prompt])

    print(f"Launching: {' '.join(cmd)}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
