#!/usr/bin/env python3
"""Export Claude Code session JSONL files to Obsidian-compatible markdown.

Streams each session line-by-line, extracting only user/assistant text content.
Skips thinking blocks, tool_use/tool_result, file-history-snapshots (but extracts
files_touched from them), and progress events.

Output: one markdown file per session at ~/.claude/obsidian/sessions/
Filename: {YYYY-MM-DD}_{session_id_short8}.md
Idempotent: skips sessions whose JSONL hasn't been modified since last export.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
OUTPUT_DIR = CLAUDE_DIR / "obsidian" / "sessions"

# Worktree suffixes to strip when deriving project name
WORKTREE_RE = re.compile(r"--claude-worktrees-[\w-]+$")


def derive_project_name(project_dir_name: str) -> str:
    """Extract human-readable project name from directory name.

    Directory names use -- after the drive letter and before worktree suffixes,
    but single - for all other path separators. Since project names can contain
    hyphens (e.g. agent-skills, sdlc-runner), we strip the known prefix rather
    than splitting on -.

    C--Users-mggar-Source-Receipts -> Receipts
    C--Users-mggar-Source-agent-skills -> agent-skills
    C--Users-mggar-Source-Receipts--claude-worktrees-foo -> Receipts
    C--Users-mggar -> Home
    """
    name = WORKTREE_RE.sub("", project_dir_name)
    # Strip known prefixes (case-insensitive Source/source)
    prefixes = ["C--Users-mggar-Source-", "C--Users-mggar-source-"]
    for prefix in prefixes:
        if name.startswith(prefix):
            remainder = name[len(prefix):]
            return remainder if remainder else "Home"
    # Handle bare home directory or Source-only
    if name in ("C--Users-mggar", "C--Users-mggar-Source", "C--Users-mggar-source"):
        return "Home"
    # Fallback: return the full name
    return name


def parse_iso_timestamp(ts: str) -> datetime | None:
    """Parse ISO 8601 timestamp string to datetime."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def extract_text_from_content(content) -> str:
    """Extract only text blocks from message content."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
        return "\n\n".join(parts)
    return ""


def process_session(jsonl_path: Path, project_dir_name: str) -> dict | None:
    """Process a single JSONL session file and return structured data.

    Returns None if the session has no meaningful content.
    """
    session_id = jsonl_path.stem
    project = derive_project_name(project_dir_name)
    git_branch = None
    slug = None
    files_touched: set[str] = set()
    messages: list[dict] = []
    first_timestamp = None
    last_timestamp = None

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type", "")

            # Extract metadata from any message
            if not git_branch and obj.get("gitBranch"):
                git_branch = obj["gitBranch"]
            if not slug and obj.get("slug"):
                slug = obj["slug"]

            # Extract files from snapshots
            if msg_type == "file-history-snapshot":
                snapshot = obj.get("snapshot", {})
                backups = snapshot.get("trackedFileBackups", {})
                for filepath in backups:
                    # Normalize path separators
                    files_touched.add(filepath.replace("\\", "/"))
                # Track timestamp from snapshot
                ts = parse_iso_timestamp(snapshot.get("timestamp"))
                if ts:
                    if first_timestamp is None or ts < first_timestamp:
                        first_timestamp = ts
                    if last_timestamp is None or ts > last_timestamp:
                        last_timestamp = ts
                continue

            # Skip progress events
            if msg_type == "progress":
                continue

            # Process user and assistant messages
            if msg_type in ("user", "assistant"):
                msg = obj.get("message", {})
                if not isinstance(msg, dict):
                    continue

                content = msg.get("content")
                text = extract_text_from_content(content)
                if not text:
                    continue

                # Skip very short automated messages
                if text in ("[Request interrupted by user for tool use]",):
                    continue

                role = msg_type
                messages.append({"role": role, "text": text})

                # Try to extract timestamp from message or surrounding context
                # Messages don't always have timestamps, but we can use
                # the session metadata

    if not messages:
        return None

    # Derive date from file modification time if no timestamps found
    if first_timestamp is None:
        mtime = jsonl_path.stat().st_mtime
        first_timestamp = datetime.fromtimestamp(mtime, tz=timezone.utc)
    if last_timestamp is None:
        last_timestamp = first_timestamp

    date_str = first_timestamp.strftime("%Y-%m-%d")

    return {
        "session_id": session_id,
        "slug": slug or "",
        "date": date_str,
        "start_time": first_timestamp.isoformat(),
        "end_time": last_timestamp.isoformat(),
        "project": project,
        "project_dir": project_dir_name,
        "git_branch": git_branch or "",
        "files_touched": sorted(files_touched),
        "messages": messages,
    }


def generate_tags(data: dict) -> list[str]:
    """Generate tags from session metadata."""
    tags = [f"project/{data['project']}"]
    if data["git_branch"]:
        # Sanitize branch name for tag
        branch = data["git_branch"].replace("/", "-")
        tags.append(f"branch/{branch}")
    return tags


def render_markdown(data: dict) -> str:
    """Render session data as markdown with YAML frontmatter."""
    tags = generate_tags(data)
    files_yaml = "\n".join(f'  - "{f}"' for f in data["files_touched"])
    tags_yaml = "\n".join(f'  - "{t}"' for t in tags)

    lines = [
        "---",
        f'session_id: "{data["session_id"]}"',
        f'slug: "{data["slug"]}"',
        f'date: "{data["date"]}"',
        f'start_time: "{data["start_time"]}"',
        f'end_time: "{data["end_time"]}"',
        f'project: "{data["project"]}"',
        f'git_branch: "{data["git_branch"]}"',
    ]

    if data["files_touched"]:
        lines.append("files_touched:")
        lines.append(files_yaml)
    else:
        lines.append("files_touched: []")

    if tags:
        lines.append("tags:")
        lines.append(tags_yaml)
    else:
        lines.append("tags: []")

    lines.append("---")
    lines.append("")

    # First user message as title
    first_user = next(
        (m for m in data["messages"] if m["role"] == "user"), None
    )
    if first_user:
        # Use first line or first 100 chars as title
        title_text = first_user["text"].split("\n")[0][:100]
        lines.append(f"# {title_text}")
        lines.append("")

    # Render conversation
    for msg in data["messages"]:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"## {role_label}")
        lines.append("")
        lines.append(msg["text"])
        lines.append("")

    return "\n".join(lines)


def export_all(force: bool = False, verbose: bool = False) -> dict:
    """Export all sessions to markdown. Returns stats dict."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stats = {"scanned": 0, "exported": 0, "skipped_uptodate": 0, "skipped_empty": 0}

    # Build index of already-exported session IDs -> output file mtime
    existing: dict[str, float] = {}
    for md_file in OUTPUT_DIR.glob("*.md"):
        # Filename: YYYY-MM-DD_sessionid8.md
        parts = md_file.stem.split("_", 1)
        if len(parts) == 2:
            existing[parts[1]] = md_file.stat().st_mtime

    # Walk all project directories
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue

        project_dir_name = project_dir.name
        jsonl_files = sorted(project_dir.glob("*.jsonl"))

        for jsonl_path in jsonl_files:
            stats["scanned"] += 1
            session_id = jsonl_path.stem
            short_id = session_id[:8]

            # Idempotency check: skip if already exported and source hasn't changed
            if not force and short_id in existing:
                source_mtime = jsonl_path.stat().st_mtime
                if source_mtime <= existing[short_id]:
                    stats["skipped_uptodate"] += 1
                    continue

            # Process session
            data = process_session(jsonl_path, project_dir_name)
            if data is None:
                stats["skipped_empty"] += 1
                continue

            # Write markdown
            md_content = render_markdown(data)
            output_filename = f"{data['date']}_{short_id}.md"
            output_path = OUTPUT_DIR / output_filename
            output_path.write_text(md_content, encoding="utf-8")

            # Set output mtime to match source for future idempotency checks
            source_mtime = jsonl_path.stat().st_mtime
            os.utime(output_path, (source_mtime, source_mtime))

            stats["exported"] += 1
            if verbose:
                print(
                    f"  Exported: {output_filename} "
                    f"({data['project']}, {len(data['messages'])} messages)"
                )

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Export Claude Code sessions to Obsidian markdown"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-export all sessions"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print each exported file"
    )
    args = parser.parse_args()

    print(f"Scanning sessions in {PROJECTS_DIR}")
    stats = export_all(force=args.force, verbose=args.verbose)

    print(f"\nDone.")
    print(f"  Scanned:    {stats['scanned']}")
    print(f"  Exported:   {stats['exported']}")
    print(f"  Up-to-date: {stats['skipped_uptodate']}")
    print(f"  Empty:      {stats['skipped_empty']}")
    print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
