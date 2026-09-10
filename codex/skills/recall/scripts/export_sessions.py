#!/usr/bin/env python3
"""Incrementally export Claude Code and Codex transcripts to searchable Markdown."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", HOME / ".codex"))
OUTPUT_DIR = Path(os.environ.get("CODEX_RECALL_OUTPUT", HOME / ".agent-history" / "codex-sessions"))
STATE_DIR = Path(os.environ.get("CODEX_RECALL_STATE", HOME / ".agent-history" / "codex-export-state"))
EXPORT_LOCK = Path(
    os.environ.get("CODEX_RECALL_EXPORT_LOCK", HOME / ".agent-history" / "codex-export.lock")
)
CLAUDE_EXPORTER = Path(
    os.environ.get(
        "CLAUDE_RECALL_EXPORTER",
        Path(__file__).resolve().parents[4] / "skills" / "recall" / "export_sessions.py",
    )
)
STATE_VERSION = 3
UUID_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.IGNORECASE)
MAX_CHUNK_CHARS = int(os.environ.get("CODEX_RECALL_CHUNK_CHARS", "65536"))
MONOLITH_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_codex_[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.md$",
    re.IGNORECASE,
)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def yaml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def text_blocks(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") not in {"input_text", "output_text", "text"}:
            continue
        value = block.get("text")
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n\n".join(parts)


def project_name(cwd: str) -> str:
    path = Path(cwd)
    try:
        relative = path.resolve().relative_to((HOME / "Source").resolve())
        return relative.parts[0] if relative.parts else "Home"
    except (OSError, ValueError):
        return path.name or "Home"


def patch_paths(command: str) -> set[str]:
    return {
        match.group(1).strip()
        for match in re.finditer(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", command, re.MULTILINE)
    }


def session_id_from_path(path: Path) -> str:
    match = UUID_RE.search(path.stem)
    return match.group(1) if match else path.stem


def source_rollouts() -> list[Path]:
    paths: list[Path] = []
    for directory in (CODEX_HOME / "sessions", CODEX_HOME / "archived_sessions"):
        if directory.exists():
            paths.extend(directory.rglob("*.jsonl"))
    return sorted(paths)


def blank_state(path: Path) -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "source": str(path),
        "offset": 0,
        "session_id": session_id_from_path(path),
        "root_thread_id": "",
        "parent_thread_id": "",
        "forked_from_id": "",
        "agent_path": "",
        "agent_role": "",
        "source_kind": "",
        "current_turn_id": "",
        "cwd": "",
        "first": "",
        "last": "",
        "messages": [],
        "files": [],
        "compaction_count": 0,
        "replacement_message_count": 0,
    }


def source_kind(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and value:
        return str(next(iter(value)))
    return ""


def update_state(state: dict[str, Any], item: dict[str, Any]) -> None:
    timestamp = parse_time(item.get("timestamp"))
    if timestamp:
        encoded = timestamp.isoformat()
        if not state["first"] or timestamp < parse_time(state["first"]):
            state["first"] = encoded
        if not state["last"] or timestamp > parse_time(state["last"]):
            state["last"] = encoded

    payload = item.get("payload")
    if not isinstance(payload, dict):
        return
    if item.get("type") == "turn_context":
        state["current_turn_id"] = str(payload.get("turn_id") or state["current_turn_id"])
        return
    if item.get("type") == "event_msg" and payload.get("type") in {"task_started", "turn_started"}:
        state["current_turn_id"] = str(payload.get("turn_id") or state["current_turn_id"])
        return
    if item.get("type") == "session_meta" and not state["cwd"]:
        state["session_id"] = str(payload.get("id") or state["session_id"])
        state["root_thread_id"] = str(payload.get("session_id") or state["session_id"])
        state["parent_thread_id"] = str(payload.get("parent_thread_id") or "")
        state["forked_from_id"] = str(payload.get("forked_from_id") or "")
        state["agent_path"] = str(payload.get("agent_path") or "")
        state["agent_role"] = str(payload.get("agent_role") or "")
        state["source_kind"] = source_kind(payload.get("source"))
        state["cwd"] = str(payload.get("cwd") or "")
        return
    if item.get("type") == "compacted":
        state["compaction_count"] += 1
        replacement = payload.get("replacement_history")
        if isinstance(replacement, list):
            state["replacement_message_count"] += sum(
                1
                for value in replacement
                if isinstance(value, dict)
                and value.get("type") == "message"
                and value.get("role") in {"user", "assistant"}
            )
        return
    if item.get("type") != "response_item":
        return
    if payload.get("type") == "message" and payload.get("role") in {"user", "assistant"}:
        text = text_blocks(payload.get("content"))
        if text:
            metadata = payload.get("internal_chat_message_metadata_passthrough")
            metadata_turn = metadata.get("turn_id") if isinstance(metadata, dict) else ""
            state["messages"].append(
                {
                    "id": str(payload.get("id") or ""),
                    "role": str(payload["role"]),
                    "text": text,
                    "timestamp": str(item.get("timestamp") or ""),
                    "turn_id": str(metadata_turn or state["current_turn_id"] or "unassigned"),
                }
            )
        return
    if payload.get("type") == "custom_tool_call" and payload.get("name") == "apply_patch":
        command = payload.get("input")
        if isinstance(command, str):
            state["files"] = sorted(set(state["files"]) | patch_paths(command))


def read_appended(path: Path, state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    size = path.stat().st_size
    offset = int(state.get("offset", 0))
    rebuilt = offset == 0 or offset > size or state.get("source") != str(path)
    if rebuilt:
        state = blank_state(path)
        offset = 0
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
            try:
                item = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(item, dict):
                update_state(state, item)
        state["offset"] = handle.tell()
    return state, rebuilt


def message_digest(messages: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for message in messages:
        digest.update(message["role"].encode())
        digest.update(b"\0")
        digest.update(message["text"].encode())
        digest.update(b"\0")
    return digest.hexdigest()


def chunk_messages(messages: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    chunks: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    size = 0
    for message in messages:
        message_size = len(message["role"]) + len(message["text"]) + 16
        if current and size + message_size > MAX_CHUNK_CHARS:
            chunks.append(current)
            current = []
            size = 0
        current.append(message)
        size += message_size
    if current:
        chunks.append(current)
    return chunks


def render_chunk(
    state: dict[str, Any], messages: list[dict[str, str]], chunk_index: int, message_start: int
) -> str:
    first = parse_time(state["first"]) or datetime.fromtimestamp(0, tz=timezone.utc)
    chunk_first = parse_time(messages[0].get("timestamp")) or first
    chunk_last = parse_time(messages[-1].get("timestamp")) or chunk_first
    turn_ids = list(dict.fromkeys(message["turn_id"] for message in messages))
    lines = [
        "---",
        f"session_id: {yaml_string(state['session_id'])}",
        f"root_thread_id: {yaml_string(state['root_thread_id'] or state['session_id'])}",
        f"parent_thread_id: {yaml_string(state['parent_thread_id'])}",
        f"forked_from_id: {yaml_string(state['forked_from_id'])}",
        'agent: "codex"',
        f"agent_path: {yaml_string(state['agent_path'])}",
        f"agent_role: {yaml_string(state['agent_role'])}",
        f"source_kind: {yaml_string(state['source_kind'])}",
        f"date: {yaml_string(first.strftime('%Y-%m-%d'))}",
        f"start_time: {yaml_string(chunk_first.isoformat())}",
        f"end_time: {yaml_string(chunk_last.isoformat())}",
        f"project: {yaml_string(project_name(state['cwd']))}",
        f"cwd: {yaml_string(state['cwd'])}",
        'git_branch: ""',
        f"chunk_index: {chunk_index}",
        f"message_start: {message_start}",
        f"message_end: {message_start + len(messages) - 1}",
        f"message_count: {len(messages)}",
        f"message_sha256: {yaml_string(message_digest(messages))}",
        f"turn_ids: {json.dumps(turn_ids)}",
    ]
    lines.extend(["---", ""])
    first_user = next((m["text"] for m in messages if m["role"] == "user"), "")
    if first_user:
        lines.extend([f"# {first_user.splitlines()[0][:100].replace('#', '').strip()}", ""])
    for message in messages:
        label = "User" if message["role"] == "user" else "Assistant"
        lines.extend([f"## {label}", "", message["text"], ""])
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
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


def load_state(path: Path, source: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("version") == STATE_VERSION and value.get("source") == str(source):
            return value
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return blank_state(source)


def target_path(state: dict[str, Any], chunk_index: int) -> Path:
    first = parse_time(state["first"]) or datetime.fromtimestamp(0, tz=timezone.utc)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", state["session_id"])
    return OUTPUT_DIR / f"{first:%Y-%m-%d}_codex_{safe}_chunk-{chunk_index:05d}.md"


def export_codex(force: bool, verbose: bool) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "scanned": 0,
        "exported": 0,
        "incremental": 0,
        "rebuilt": 0,
        "skipped": 0,
        "empty": 0,
        "sessions_updated": 0,
        "chunks_written": 0,
        "chunks_unchanged": 0,
        "errors": [],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for source in source_rollouts():
        stats["scanned"] += 1
        cache = state_path(session_id_from_path(source))
        source_stat = source.stat()
        if not force and cache.exists() and cache.stat().st_mtime_ns == source_stat.st_mtime_ns:
            stats["skipped"] += 1
            continue
        state = blank_state(source) if force else load_state(cache, source)
        previous_offset = int(state.get("offset", 0))
        try:
            state, rebuilt = read_appended(source, state)
        except OSError as error:
            stats["errors"].append(f"{source}: {error}")
            continue
        if not state["messages"]:
            atomic_write(cache, json.dumps(state, ensure_ascii=False, separators=(",", ":")))
            os.utime(cache, ns=(source_stat.st_mtime_ns, source_stat.st_mtime_ns))
            stats["empty"] += 1
            continue
        message_start = 0
        chunks = chunk_messages(state["messages"])
        for chunk_index, messages in enumerate(chunks, 1):
            target = target_path(state, chunk_index)
            rendered = render_chunk(state, messages, chunk_index, message_start)
            if atomic_write_if_changed(target, rendered):
                stats["chunks_written"] += 1
            else:
                stats["chunks_unchanged"] += 1
            message_start += len(messages)
        for stale in OUTPUT_DIR.glob(
            f"*_codex_{state['session_id']}_chunk-*.md"
        ):
            match = re.search(r"_chunk-(\d+)\.md$", stale.name)
            if match and int(match.group(1)) > len(chunks):
                stale.unlink()
                stats["chunks_written"] += 1
        atomic_write(cache, json.dumps(state, ensure_ascii=False, separators=(",", ":")))
        os.utime(cache, ns=(source_stat.st_mtime_ns, source_stat.st_mtime_ns))
        stats["sessions_updated"] += 1
        stats["rebuilt" if rebuilt else "incremental"] += 1
        if verbose:
            mode = "rebuilt" if rebuilt else f"appended from byte {previous_offset}"
            print(f"codex: {state['session_id']} ({len(chunks)} chunks, {mode})")
    stats["exported"] = stats["chunks_written"]
    return stats


def load_claude_exporter():
    if not CLAUDE_EXPORTER.exists():
        return None
    spec = importlib.util.spec_from_file_location("claude_session_exporter", CLAUDE_EXPORTER)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_claude(force: bool, verbose: bool) -> dict[str, int]:
    exporter = load_claude_exporter()
    if exporter is None or not exporter.PROJECTS_DIR.exists():
        return {"scanned": 0, "exported": 0, "skipped_uptodate": 0, "skipped_empty": 0}
    return exporter.export_all(force=force, verbose=verbose)


def parse_export_metadata(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        if handle.readline().rstrip() != "---":
            return result
        for line in handle:
            if line.rstrip() == "---":
                break
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                result[key] = value.strip().strip('"')
    return result


def verify_exports() -> dict[str, Any]:
    failures: list[str] = []
    checked = 0
    for source in source_rollouts():
        state, _ = read_appended(source, blank_state(source))
        if not state["messages"]:
            continue
        checked += 1
        message_start = 0
        chunks = chunk_messages(state["messages"])
        for chunk_index, messages in enumerate(chunks, 1):
            target = target_path(state, chunk_index)
            if not target.exists():
                failures.append(f"missing export chunk: {state['session_id']}:{chunk_index}")
                message_start += len(messages)
                continue
            actual = target.read_bytes().decode("utf-8")
            expected = render_chunk(state, messages, chunk_index, message_start)
            metadata = parse_export_metadata(target)
            expected_count = str(len(messages))
            if metadata.get("message_count") != expected_count:
                failures.append(
                    f"message count mismatch: {state['session_id']}:{chunk_index} source={expected_count} export={metadata.get('message_count')}"
                )
            if metadata.get("message_sha256") != message_digest(messages):
                failures.append(f"message digest mismatch: {state['session_id']}:{chunk_index}")
            if actual != expected:
                actual_hash = hashlib.sha256(actual.encode()).hexdigest()[:12]
                expected_hash = hashlib.sha256(expected.encode()).hexdigest()[:12]
                failures.append(
                    f"rendered transcript mismatch: {state['session_id']}:{chunk_index} "
                    f"actual={actual_hash} expected={expected_hash}"
                )
            message_start += len(messages)
    return {"checked": checked, "failures": failures, "ok": not failures}


def prune_monoliths() -> int:
    removed = 0
    for path in OUTPUT_DIR.glob("*.md"):
        if MONOLITH_RE.match(path.name):
            path.unlink()
            removed += 1
    return removed


def verify_qmd() -> dict[str, Any]:
    qmd = shutil.which("qmd")
    if not qmd:
        return {"available": False, "failures": ["qmd is not installed"], "ok": False}
    result = subprocess.run([qmd, "ls", "Codex-sessions"], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return {"available": True, "failures": [result.stderr.strip() or "qmd ls failed"], "ok": False}
    indexed_names = {
        match.group(1)
        for line in result.stdout.splitlines()
        if (match := re.search(r"qmd://Codex-sessions/(\S+\.md)$", line))
    }
    expected_names = {path.name.replace("_", "-") for path in OUTPUT_DIR.glob("*.md")}
    missing = sorted(expected_names - indexed_names)
    return {
        "available": True,
        "expected": len(expected_names),
        "indexed": len(expected_names & indexed_names),
        "missing": missing,
        "failures": [f"not indexed: {value}" for value in missing],
        "ok": not missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild all Codex exports and state")
    parser.add_argument("--verify", action="store_true", help="compare source messages with exports")
    parser.add_argument("--verify-qmd", action="store_true", help="confirm every export is listed by QMD")
    parser.add_argument("--skip-claude", action="store_true", help="do not refresh Claude exports")
    parser.add_argument(
        "--prune-monoliths",
        action="store_true",
        help="remove superseded whole-session exports after chunk migration",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    EXPORT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with EXPORT_LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        results: dict[str, Any] = {
            "output": str(OUTPUT_DIR),
            "claude": (
                {"scanned": 0, "exported": 0, "skipped_uptodate": 0, "skipped_empty": 0}
                if args.skip_claude
                else export_claude(args.force, args.verbose)
            ),
            "codex": export_codex(args.force, args.verbose),
        }
        if args.prune_monoliths:
            results["monoliths_removed"] = prune_monoliths()
        if args.verify:
            results["verification"] = verify_exports()
        if args.verify_qmd:
            results["qmd"] = verify_qmd()
    print(json.dumps(results, indent=2))
    if any(not results[name]["ok"] for name in ("verification", "qmd") if name in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
