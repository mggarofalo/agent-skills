"""Tests for the Claude session-recall exporter and its refresh hook.

Run: python3 hooks/test_session_recall.py
Everything runs in temp dirs; the real ~/.claude and the real QMD index are never touched.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HOOK_PATH = Path(__file__).resolve().parent / "session-end-export.py"
EXPORTER_PATH = Path(__file__).resolve().parents[1] / "skills" / "recall" / "export_sessions.py"
SESSION_ID = "abcdef12-3456-7890-abcd-ef1234567890"
CHUNK_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[0-9a-f]{8}(_part-\d{3})?\.md$")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(role: str, text: str, second: int) -> str:
    return json.dumps({
        "type": role,
        "cwd": "/tmp/demo",
        "gitBranch": "main",
        "slug": "quiet-testing-otter",
        "timestamp": f"2026-10-01T10:00:{second:02d}Z",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    }) + "\n"


class TempDirs:
    def make_dirs(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.projects = self.root / "projects"
        self.output = self.root / "sessions"
        self.state = self.root / "state"
        self.source = self.projects / "-tmp-demo" / f"{SESSION_ID}.jsonl"
        self.source.parent.mkdir(parents=True)


class ExporterTests(TempDirs, unittest.TestCase):
    def setUp(self) -> None:
        self.make_dirs()
        self.exporter = load(EXPORTER_PATH, "claude_recall_exporter")
        self.patches = [
            mock.patch.object(self.exporter, "PROJECTS_DIR", self.projects),
            mock.patch.object(self.exporter, "OUTPUT_DIR", self.output),
            mock.patch.object(self.exporter, "STATE_DIR", self.state),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def export(self) -> dict:
        with contextlib.redirect_stderr(io.StringIO()) as err:
            stats = self.exporter.export_all()
        self.stderr = err.getvalue()
        return stats

    def append(self, text: str) -> None:
        with self.source.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def chunks(self) -> list[Path]:
        return sorted(self.output.glob("*.md"))

    def test_unchanged_source_is_skipped_and_touch_rewrites_nothing(self) -> None:
        self.source.write_text(record("user", "hello", 1) + record("assistant", "hi", 2))
        self.assertEqual(self.export()["exported"], 1)
        second = self.export()
        self.assertEqual((second["exported"], second["skipped_uptodate"]), (0, 1))
        os.utime(self.source, ns=(time.time_ns(), time.time_ns()))
        third = self.export()
        self.assertEqual((third["exported"], third["unchanged"], third["chunks_written"]), (0, 1, 0))

    def test_incremental_reexport_only_touches_trailing_chunk(self) -> None:
        with mock.patch.object(self.exporter, "MAX_CHUNK_CHARS", 80):
            self.source.write_text("".join(
                record("user" if i % 2 == 0 else "assistant", f"message {i} " + "x" * 30, i)
                for i in range(6)
            ))
            self.export()
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.chunks()}
            self.assertGreaterEqual(len(before), 3)
            trailing = max(before)

            self.append(record("user", "appended " + "y" * 10, 30))
            stats = self.export()

            self.assertEqual((stats["incremental"], stats["rebuilt"]), (1, 0))
            self.assertEqual(stats["chunks_written"], 1)
            after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.chunks()}
            for name, value in before.items():
                if name != trailing:
                    self.assertEqual(after[name], value, f"{name} was rewritten")
            changed = [n for n in after if after[n] != before.get(n)]
            self.assertEqual(len(changed), 1)
            self.assertIn("appended", after[changed[0]][0].decode())

    def test_chunk_layout_and_frontmatter(self) -> None:
        with mock.patch.object(self.exporter, "MAX_CHUNK_CHARS", 60):
            self.source.write_text("".join(record("user", f"m{i} " + "z" * 40, i) for i in range(3)))
            self.export()
        names = [p.name for p in self.chunks()]
        self.assertEqual(names, ["2026-10-01_abcdef12.md", "2026-10-01_abcdef12_part-002.md",
                                 "2026-10-01_abcdef12_part-003.md"])
        for index, path in enumerate(self.chunks(), 1):
            self.assertRegex(path.name, CHUNK_NAME_RE)
            text = path.read_text()
            self.assertTrue(text.startswith("---\n"))
            self.assertIn(f'session_id: "{SESSION_ID}"', text)
            self.assertIn('date: "2026-10-01"', text)
            self.assertIn(f"chunk_index: {index}", text)
            self.assertIn('project: "demo"', text)

    def test_malformed_line_is_skipped_with_diagnostic(self) -> None:
        self.source.write_text(record("user", "before", 1) + "{not json\n" + record("assistant", "after", 2))
        stats = self.export()
        self.assertEqual(stats["malformed_lines"], 1)
        self.assertIn("skipped unparseable record", self.stderr)
        text = self.chunks()[0].read_text()
        self.assertIn("before", text)
        self.assertIn("after", text)
        self.assertIn("message_count: 2", text)

    def test_partial_trailing_record_is_retried(self) -> None:
        full = record("assistant", "later", 2)
        self.source.write_text(record("user", "first", 1) + full[:-10])
        stats = self.export()
        self.assertEqual(stats["malformed_lines"], 0)
        self.assertNotIn("later", self.chunks()[0].read_text())
        self.append(full[-10:])
        self.export()
        self.assertIn("later", self.chunks()[0].read_text())

    def test_truncated_source_is_rebuilt(self) -> None:
        self.source.write_text(record("user", "old", 1) + record("assistant", "old reply", 2))
        self.export()
        self.source.write_text(record("user", "new", 3))
        stats = self.export()
        self.assertEqual(stats["rebuilt"], 1)
        text = self.chunks()[0].read_text()
        self.assertNotIn("old", text)

    def test_codex_import_contract(self) -> None:
        self.assertTrue(callable(self.exporter.export_all))
        self.assertTrue(hasattr(self.exporter, "PROJECTS_DIR"))
        self.assertIn("exported", self.export())


class Completed:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


class RefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hook = load(HOOK_PATH, "claude_recall_hook")
        self.env = mock.patch.dict(os.environ, {"CLAUDE_RECALL_QMD": "/fake/qmd"})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()

    def test_skips_qmd_when_nothing_changed(self) -> None:
        with tempfile.TemporaryFile("w+") as log, mock.patch.object(
            self.hook.subprocess, "run", return_value=Completed(json.dumps({"exported": 0}))
        ) as run:
            self.assertTrue(self.hook.run_refresh(log))
            log.seek(0)
            self.assertIn("skipped QMD", log.read())
        self.assertEqual(run.call_count, 1)
        self.assertIn("--json", run.call_args.args[0])

    def test_updates_and_embeds_when_changed(self) -> None:
        calls = [Completed(json.dumps({"exported": 2})), Completed(), Completed()]
        with tempfile.TemporaryFile("w+") as log, mock.patch.object(
            self.hook.subprocess, "run", side_effect=calls
        ) as run:
            self.assertTrue(self.hook.run_refresh(log))
        self.assertEqual(run.call_args_list[1].args[0], ["/fake/qmd", "update"])
        self.assertEqual(run.call_args_list[2].args[0], ["/fake/qmd", "embed", "-c", "Claude-sessions"])

    def test_failed_export_skips_qmd(self) -> None:
        with tempfile.TemporaryFile("w+") as log, mock.patch.object(
            self.hook.subprocess, "run", return_value=Completed("", 1)
        ) as run:
            self.assertFalse(self.hook.run_refresh(log))
        self.assertEqual(run.call_count, 1)


class WorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hook = load(HOOK_PATH, "claude_recall_hook")
        self.temporary = tempfile.TemporaryDirectory()
        logs = Path(self.temporary.name)
        self.patches = [
            mock.patch.object(self.hook, "LOG_DIR", logs),
            mock.patch.object(self.hook, "LOG", logs / "export.log"),
            mock.patch.object(self.hook, "LOCK", logs / "recall.lock"),
            mock.patch.object(self.hook, "PENDING", logs / "recall.pending"),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def test_requests_during_a_refresh_coalesce_into_one_rerun(self) -> None:
        calls = []

        def refresh(log):
            calls.append(1)
            if len(calls) == 1:
                # Three hook events land mid-refresh; their workers lose the lock.
                for _ in range(3):
                    self.hook.PENDING.touch()
                    self.hook.worker()
                self.assertEqual(len(calls), 1, "a second worker ran while the lock was held")
            return True

        self.hook.PENDING.touch()
        with mock.patch.object(self.hook, "run_refresh", side_effect=refresh):
            self.hook.worker()
        self.assertEqual(len(calls), 2)
        self.assertFalse(self.hook.PENDING.exists())

    def test_refresh_exception_is_logged_and_worker_survives(self) -> None:
        self.hook.PENDING.touch()
        with mock.patch.object(self.hook, "run_refresh", side_effect=RuntimeError("boom")):
            self.hook.worker()
        self.assertIn("boom", self.hook.LOG.read_text())

    def test_main_returns_zero_even_if_spawn_fails(self) -> None:
        with mock.patch.object(self.hook.subprocess, "Popen", side_effect=OSError("no fork")), \
                mock.patch.object(sys, "argv", ["hook"]):
            self.assertEqual(self.hook.main(), 0)
        self.assertIn("no fork", self.hook.LOG.read_text())


class EndToEndTests(TempDirs, unittest.TestCase):
    """Run the real hook as a subprocess against temp dirs and a fake qmd."""

    def setUp(self) -> None:
        self.make_dirs()
        self.logs = self.root / "logs"
        self.qmd_calls = self.root / "qmd-calls.txt"
        fake_qmd = self.root / "qmd"
        fake_qmd.write_text(f'#!/bin/sh\necho "$@" >> "{self.qmd_calls}"\n')
        fake_qmd.chmod(0o755)
        self.env = {
            **os.environ,
            "CLAUDE_RECALL_PROJECTS": str(self.projects),
            "CLAUDE_RECALL_OUTPUT": str(self.output),
            "CLAUDE_RECALL_STATE": str(self.state),
            "CLAUDE_RECALL_LOG_DIR": str(self.logs),
            "CLAUDE_RECALL_QMD": str(fake_qmd),
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fire_hook_and_wait(self, finished_runs: int) -> float:
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)], input='{"hook_event_name":"Stop"}',
            text=True, capture_output=True, env=self.env, timeout=10,
        )
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.logs / "session-end-export.log"
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if log.exists() and log.read_text().count("refresh finished") >= finished_runs \
                    and not (self.logs / "session-recall.pending").exists():
                return elapsed
            time.sleep(0.05)
        self.fail(f"worker did not finish: {log.read_text() if log.exists() else 'no log'}")

    def test_hook_returns_fast_and_refreshes_only_on_change(self) -> None:
        self.source.write_text(record("user", "hello", 1) + record("assistant", "hi", 2))
        elapsed = self.fire_hook_and_wait(1)
        self.assertLess(elapsed, 3.0)
        self.assertEqual(self.qmd_calls.read_text().splitlines(), ["update", "embed -c Claude-sessions"])
        self.assertEqual(len(list(self.output.glob("*.md"))), 1)

        self.fire_hook_and_wait(2)
        self.assertEqual(len(self.qmd_calls.read_text().splitlines()), 2)
        self.assertIn("no session changes", (self.logs / "session-end-export.log").read_text())


if __name__ == "__main__":
    unittest.main()
