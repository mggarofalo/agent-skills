#!/usr/bin/env python3
"""Incrementally export Claude Code session JSONL files to Obsidian-compatible markdown.

Each session is read only from the byte offset where the previous run stopped;
parsed state (messages, metadata) is cached per session so a per-turn hook run
costs a stat() per session plus a parse of the newly appended records.

Only user/assistant text is exported. Thinking blocks, tool_use/tool_result and
progress events are skipped; file-history-snapshots contribute files_touched.

Output layout in OUTPUT_DIR (default ~/.claude/obsidian/sessions/):
    {YYYY-MM-DD}_{id8}.md             first chunk of a session
    {YYYY-MM-DD}_{id8}_part-NNN.md    chunk NNN >= 002 of the same session
Chunks are cut greedily at message boundaries (MAX_CHUNK_CHARS), so appending
to a session only ever rewrites its trailing chunk or adds a new one. Every
chunk carries full YAML frontmatter; start_time/end_time and files_touched
describe that chunk (union over a session's chunks gives the session view).
Files are written atomically and only when their bytes change.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # Windows: run unlocked
    fcntl = None

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
PROJECTS_DIR = Path(os.environ.get("CLAUDE_RECALL_PROJECTS", CLAUDE_DIR / "projects"))
OUTPUT_DIR = Path(os.environ.get("CLAUDE_RECALL_OUTPUT", CLAUDE_DIR / "obsidian" / "sessions"))
STATE_DIR = Path(os.environ.get("CLAUDE_RECALL_STATE", CLAUDE_DIR / "recall-export-state"))
MAX_CHUNK_CHARS = int(os.environ.get("CLAUDE_RECALL_CHUNK_CHARS", "65536"))
STATE_VERSION = 1

# Worktree suffixes to strip when deriving project name
WORKTREE_RE = re.compile(r"--claude-worktrees-[\w-]+$")
SKIPPED_TEXTS = {"[Request interrupted by user for tool use]"}


def derive_project_name(project_dir_name: str) -> str:
    """Fallback project name from the encoded project directory name.

    Used only when no record carries a cwd. Directory names encode the path
    with every non-alphanumeric character replaced by '-'.

    -Users-me-Source-agent-skills -> agent-skills
    C--Users-mggar-Source-Receipts--claude-worktrees-foo -> Receipts
    -Users-me -> Home
    """
    name = WORKTREE_RE.sub("", project_dir_name)
    home = re.sub(r"[^A-Za-z0-9]", "-", str(HOME))
    homes = [home, "C--Users-mggar"]
    for base in homes:
        for source in ("-Source", "-source"):
            prefix = f"{base}{source}-"
            if name.startswith(prefix):
                return name[len(prefix):] or "Home"
            if name == base + source:
                return "Home"
        if name == base:
            return "Home"
    return name


def project_from_cwd(cwd: str) -> str:
    """~/Source/<project>/... -> <project>; ~ -> Home; else the leaf name."""
    path = Path(cwd)
    for source in ("Source", "source"):
        try:
            relative = path.relative_to(HOME / source)
            return relative.parts[0] if relative.parts else "Home"
        except ValueError:
            continue
    if path == HOME:
        return "Home"
    return path.name or "Home"


def parse_iso_timestamp(ts: Any) -> datetime | None:
    """Parse ISO 8601 timestamp string to datetime."""
    if not ts or not isinstance(ts, str):
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
                text = block.get("text", "")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n\n".join(parts)
    return ""


# ---------------------------------------------------------------- parse state


def blank_state(path: Path, project_dir_name: str) -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "source": str(path),
        "inode": 0,
        "offset": 0,
        "session_id": path.stem,
        "project_dir": project_dir_name,
        "cwd": "",
        "slug": "",
        "git_branch": "",
        "first": "",
        "last": "",
        "messages": [],  # [{"role", "text", "ts"}]
        "files": {},  # path -> index of the message it is attributed to
    }


def note_time(state: dict[str, Any], ts: datetime | None) -> None:
    if ts is None:
        return
    if not state["first"] or ts < parse_iso_timestamp(state["first"]):
        state["first"] = ts.isoformat()
    if not state["last"] or ts > parse_iso_timestamp(state["last"]):
        state["last"] = ts.isoformat()


def update_state(state: dict[str, Any], obj: dict[str, Any]) -> None:
    """Fold one JSONL record into the session state."""
    if not state["git_branch"] and isinstance(obj.get("gitBranch"), str):
        state["git_branch"] = obj["gitBranch"]
    if not state["slug"] and isinstance(obj.get("slug"), str):
        state["slug"] = obj["slug"]
    if not state["cwd"] and isinstance(obj.get("cwd"), str):
        state["cwd"] = obj["cwd"]

    msg_type = obj.get("type", "")
    if msg_type == "file-history-snapshot":
        snapshot = obj.get("snapshot")
        if not isinstance(snapshot, dict):
            return
        backups = snapshot.get("trackedFileBackups")
        # Attribute each file to the message it was first seen at, so a chunk's
        # files_touched never changes once the chunk is closed.
        anchor = max(len(state["messages"]) - 1, 0)
        if isinstance(backups, dict):
            for filepath in backups:
                state["files"].setdefault(str(filepath).replace("\\", "/"), anchor)
        note_time(state, parse_iso_timestamp(snapshot.get("timestamp")))
        return

    if msg_type not in ("user", "assistant"):
        return
    ts = parse_iso_timestamp(obj.get("timestamp"))
    note_time(state, ts)
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return
    text = extract_text_from_content(msg.get("content"))
    if not text or text in SKIPPED_TEXTS:
        return
    state["messages"].append({"role": msg_type, "text": text, "ts": ts.isoformat() if ts else ""})


def read_appended(path: Path, state: dict[str, Any], stats: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Parse records appended since state["offset"]. Returns (state, rebuilt).

    A trailing record without a newline is left for the next run (the writer may
    still be mid-line). Complete-but-unparseable records are skipped with a
    diagnostic on stderr so one bad line never corrupts or blocks an export.
    """
    st = path.stat()
    offset = int(state.get("offset", 0))
    rebuilt = offset == 0 or offset > st.st_size or state.get("inode") != st.st_ino
    if rebuilt:
        state = blank_state(path, state["project_dir"])
        offset = 0
    state["inode"] = st.st_ino
    with path.open("rb") as handle:
        handle.seek(offset)
        while True:
            line_start = handle.tell()
            raw = handle.readline()
            if not raw:
                break
            if not raw.endswith(b"\n"):
                handle.seek(line_start)
                break
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                stats["malformed_lines"] += 1
                print(f"export_sessions: {path}:byte {line_start}: skipped unparseable record ({error})",
                      file=sys.stderr)
                continue
            if isinstance(obj, dict):
                update_state(state, obj)
        state["offset"] = handle.tell()
    return state, rebuilt


# ------------------------------------------------------------------ rendering


def chunk_messages(messages: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Greedy, prefix-stable split: appending messages only changes the last chunk."""
    chunks: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    size = 0
    for message in messages:
        message_size = len(message["role"]) + len(message["text"]) + 16
        if current and size + message_size > MAX_CHUNK_CHARS:
            chunks.append(current)
            current, size = [], 0
        current.append(message)
        size += message_size
    if current:
        chunks.append(current)
    return chunks


def yaml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def session_start(state: dict[str, Any], path: Path) -> datetime:
    first = parse_iso_timestamp(state["first"])
    if first is None:
        first = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return first


def session_project(state: dict[str, Any]) -> str:
    if state["cwd"]:
        return project_from_cwd(state["cwd"])
    return derive_project_name(state["project_dir"])


def generate_tags(project: str, git_branch: str) -> list[str]:
    tags = [f"project/{project}"]
    if git_branch:
        tags.append(f"branch/{git_branch.replace('/', '-')}")
    return tags


def render_chunk(state: dict[str, Any], start: datetime, messages: list[dict[str, str]],
                 chunk_index: int, message_start: int) -> str:
    message_end = message_start + len(messages) - 1
    chunk_first = parse_iso_timestamp(messages[0]["ts"]) or start
    chunk_last = parse_iso_timestamp(messages[-1]["ts"]) or chunk_first
    files = sorted(f for f, i in state["files"].items()
                   if message_start <= i <= message_end)
    project = session_project(state)

    lines = [
        "---",
        f"session_id: {yaml_string(state['session_id'])}",
        f"slug: {yaml_string(state['slug'])}",
        f"date: {yaml_string(start.strftime('%Y-%m-%d'))}",
        f"start_time: {yaml_string(chunk_first.isoformat())}",
        f"end_time: {yaml_string(chunk_last.isoformat())}",
        f"project: {yaml_string(project)}",
        f"git_branch: {yaml_string(state['git_branch'])}",
        f"chunk_index: {chunk_index}",
        f"message_start: {message_start}",
        f"message_count: {len(messages)}",
    ]
    if files:
        lines.append("files_touched:")
        lines.extend(f"  - {yaml_string(f)}" for f in files)
    else:
        lines.append("files_touched: []")
    lines.append("tags:")
    lines.extend(f"  - {yaml_string(t)}" for t in generate_tags(project, state["git_branch"]))
    lines.extend(["---", ""])

    first_user = next((m for m in messages if m["role"] == "user"), None)
    if first_user:
        lines.extend([f"# {first_user['text'].split(chr(10))[0][:100]}", ""])
    for msg in messages:
        lines.extend([f"## {'User' if msg['role'] == 'user' else 'Assistant'}", "", msg["text"], ""])
    return "\n".join(lines)


def chunk_filename(date: str, short_id: str, chunk_index: int) -> str:
    if chunk_index == 1:
        return f"{date}_{short_id}.md"
    return f"{date}_{short_id}_part-{chunk_index:03d}.md"


# ---------------------------------------------------------------------- files


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="": write "\n" as-is so the bytes match atomic_write_if_changed's
    # comparison; Windows text mode would write "\r\n" and rewrite every chunk.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                     prefix=".tmp-", suffix=".part", delete=False) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def atomic_write_if_changed(path: Path, text: str) -> bool:
    try:
        if path.read_bytes() == text.encode("utf-8"):
            return False
    except FileNotFoundError:
        pass
    atomic_write(path, text)
    return True


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", session_id)
    return STATE_DIR / f"{safe}.json"


def load_state(cache: Path, source: Path, project_dir_name: str) -> dict[str, Any]:
    try:
        value = json.loads(cache.read_text(encoding="utf-8"))
        if value.get("version") == STATE_VERSION and value.get("source") == str(source):
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return blank_state(source, project_dir_name)


def save_state(cache: Path, state: dict[str, Any], source_mtime_ns: int) -> None:
    atomic_write(cache, json.dumps(state, ensure_ascii=False, separators=(",", ":")))
    os.utime(cache, ns=(source_mtime_ns, source_mtime_ns))


# --------------------------------------------------------------------- export


def new_stats() -> dict[str, Any]:
    return {
        "scanned": 0,
        "exported": 0,  # sessions with at least one export file written or removed
        "unchanged": 0,  # sessions re-read whose exports were already identical
        "skipped_uptodate": 0,  # sessions untouched since the last run (mtime match)
        "skipped_empty": 0,  # sessions with no user/assistant text yet
        "incremental": 0,
        "rebuilt": 0,
        "chunks_written": 0,
        "chunks_unchanged": 0,
        "chunks_removed": 0,
        "malformed_lines": 0,
        "errors": [],
    }


def export_session(source: Path, project_dir_name: str, force: bool,
                   stats: dict[str, Any], verbose: bool, stream) -> None:
    cache = state_path(source.stem)
    mtime_ns = source.stat().st_mtime_ns
    if not force and cache.exists() and cache.stat().st_mtime_ns == mtime_ns:
        stats["skipped_uptodate"] += 1
        return

    state = blank_state(source, project_dir_name) if force else load_state(cache, source, project_dir_name)
    previous_offset = int(state.get("offset", 0))
    state, rebuilt = read_appended(source, state, stats)
    stats["rebuilt" if rebuilt else "incremental"] += 1

    short_id = state["session_id"][:8]
    wanted: set[str] = set()
    written = 0
    chunks = chunk_messages(state["messages"])
    if chunks:
        start = session_start(state, source)
        date = start.strftime("%Y-%m-%d")
        message_start = 0
        for index, messages in enumerate(chunks, 1):
            name = chunk_filename(date, short_id, index)
            wanted.add(name)
            if atomic_write_if_changed(OUTPUT_DIR / name, render_chunk(state, start, messages, index, message_start)):
                written += 1
            else:
                stats["chunks_unchanged"] += 1
            message_start += len(messages)

    removed = 0
    for pattern in (f"*_{short_id}.md", f"*_{short_id}_part-*.md"):
        for stale in OUTPUT_DIR.glob(pattern):
            if stale.name not in wanted:
                stale.unlink(missing_ok=True)
                removed += 1

    save_state(cache, state, mtime_ns)
    stats["chunks_written"] += written
    stats["chunks_removed"] += removed
    if not chunks and not removed:
        stats["skipped_empty"] += 1
    elif written or removed:
        stats["exported"] += 1
        if verbose:
            mode = "rebuilt" if rebuilt else f"appended from byte {previous_offset}"
            print(f"  Exported: {short_id} ({session_project(state)}, {len(state['messages'])} messages, "
                  f"{len(chunks)} chunks, {written} written, {removed} removed, {mode})", file=stream)
    else:
        stats["unchanged"] += 1


def export_all(force: bool = False, verbose: bool = False, stream=None) -> dict:
    """Export all sessions to markdown. Returns stats dict.

    Also imported by codex/skills/recall/scripts/export_sessions.py; keep the
    signature and the PROJECTS_DIR module attribute stable.
    """
    stream = stream or sys.stdout
    stats = new_stats()
    if not PROJECTS_DIR.is_dir():
        return stats
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / ".lock").open("a+") as lock:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            for source in sorted(project_dir.glob("*.jsonl")):
                stats["scanned"] += 1
                try:
                    export_session(source, project_dir.name, force, stats, verbose, stream)
                except OSError as error:
                    stats["errors"].append(f"{source}: {error}")
                    print(f"export_sessions: {source}: {error}", file=sys.stderr)
    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export Claude Code sessions to Obsidian markdown")
    parser.add_argument("--force", action="store_true", help="Re-parse and re-render all sessions")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print each exported session")
    parser.add_argument("--json", action="store_true",
                        help="Print only a JSON stats object on stdout (verbose lines go to stderr)")
    args = parser.parse_args()

    if args.json:
        stats = export_all(force=args.force, verbose=args.verbose, stream=sys.stderr)
        print(json.dumps(stats))
        return

    print(f"Scanning sessions in {PROJECTS_DIR}")
    stats = export_all(force=args.force, verbose=args.verbose)
    print("\nDone.")
    print(f"  Scanned:    {stats['scanned']}")
    print(f"  Exported:   {stats['exported']} ({stats['chunks_written']} chunks written, "
          f"{stats['chunks_removed']} removed)")
    print(f"  Unchanged:  {stats['unchanged']}")
    print(f"  Up-to-date: {stats['skipped_uptodate']}")
    print(f"  Empty:      {stats['skipped_empty']}")
    if stats["malformed_lines"]:
        print(f"  Malformed:  {stats['malformed_lines']} records skipped")
    if stats["errors"]:
        print(f"  Errors:     {len(stats['errors'])}")
    print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
