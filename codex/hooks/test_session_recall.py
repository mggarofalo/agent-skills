"""Tests for the Codex exporter, refresh hook, hosted-mode wiring and recall backend.

Run: python3 -m unittest discover -s codex/hooks

The exporter and hook import fcntl, which Windows lacks. There, each module is
loaded with a stand-in fcntl that raises SkipTest the moment any code touches it,
so tests of the locking paths skip with a reason and everything else still runs.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

EXPORTER_PATH = Path(__file__).resolve().parents[1] / "skills" / "recall" / "scripts" / "export_sessions.py"
HOOK_PATH = Path(__file__).resolve().parent / "session-end-export.py"
BACKEND_PATH = Path(__file__).resolve().parents[1] / "skills" / "recall" / "scripts" / "recall_backend.py"
HAS_FCNTL = importlib.util.find_spec("fcntl") is not None
NO_FCNTL = "needs fcntl (file locking), which this platform lacks; Codex hooks run on macOS and Linux"


def fcntl_stand_in() -> types.ModuleType:
    module = types.ModuleType("fcntl")

    def missing(name: str):
        raise unittest.SkipTest(f"{NO_FCNTL} (reached fcntl.{name})")

    module.__getattr__ = missing
    return module


def load(path: Path, name: str):
    """Load a module by path. Without fcntl, a stand-in is visible only while it loads."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    stand_in = not HAS_FCNTL and "fcntl" not in sys.modules
    if stand_in:
        sys.modules["fcntl"] = fcntl_stand_in()
    try:
        spec.loader.exec_module(module)
    finally:
        if stand_in:
            sys.modules.pop("fcntl", None)  # never leak it to modules that test for fcntl
    return module


def load_exporter():
    return load(EXPORTER_PATH, "codex_recall_exporter")


def load_hook():
    return load(HOOK_PATH, "codex_recall_hook")


def record(record_type: str, payload: dict, timestamp: str) -> str:
    return json.dumps({"timestamp": timestamp, "type": record_type, "payload": payload}) + "\n"


class IncrementalExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.exporter = load_exporter()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.codex_home = self.root / ".codex"
        self.output = self.root / "exports"
        self.state = self.root / "state"
        self.source = (
            self.codex_home
            / "sessions"
            / "2026"
            / "09"
            / "09"
            / "rollout-2026-09-09T10-00-00-11111111-1111-1111-1111-111111111111.jsonl"
        )
        self.source.parent.mkdir(parents=True)
        self.patches = [
            mock.patch.object(self.exporter, "CODEX_HOME", self.codex_home),
            mock.patch.object(self.exporter, "OUTPUT_DIR", self.output),
            mock.patch.object(self.exporter, "STATE_DIR", self.state),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def initial_rollout(self) -> str:
        return "".join(
            [
                record(
                    "session_meta",
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "session_id": "11111111-1111-1111-1111-111111111111",
                        "cwd": "/tmp/project",
                        "source": "cli",
                    },
                    "2026-09-09T14:00:00Z",
                ),
                record(
                    "response_item",
                    {"id": "u1", "type": "message", "role": "user", "content": [{"type": "input_text", "text": "first"}]},
                    "2026-09-09T14:00:01Z",
                ),
                record(
                    "response_item",
                    {"id": "a1", "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "answer"}]},
                    "2026-09-09T14:00:02Z",
                ),
            ]
        )

    def test_incremental_append_preserves_pre_compaction_messages(self) -> None:
        self.source.write_text(self.initial_rollout(), encoding="utf-8")
        first = self.exporter.export_codex(False, False)
        self.assertEqual(first["rebuilt"], 1)

        with self.source.open("a", encoding="utf-8") as handle:
            handle.write(
                record(
                    "compacted",
                    {"replacement_history": [{"type": "compaction", "encrypted_content": "opaque"}]},
                    "2026-09-09T14:00:03Z",
                )
            )
            handle.write(
                record(
                    "response_item",
                    {"id": "u2", "type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]},
                    "2026-09-09T14:00:04Z",
                )
            )

        second = self.exporter.export_codex(False, False)
        self.assertEqual(second["incremental"], 1)
        target = next(self.output.glob("*.md"))
        text = target.read_text(encoding="utf-8")
        self.assertIn("message_count: 3", text)
        self.assertEqual(text.count("## User"), 2)
        self.assertIn("first", text)
        self.assertIn("second", text)
        state = json.loads(next(self.state.glob("*.json")).read_text())
        self.assertEqual(state["compaction_count"], 1)

    def test_partial_last_record_is_retried(self) -> None:
        complete = self.initial_rollout()
        partial = record(
            "response_item",
            {"id": "u2", "type": "message", "role": "user", "content": [{"type": "input_text", "text": "later"}]},
            "2026-09-09T14:00:03Z",
        )
        self.source.write_bytes(complete.encode() + partial[:-4].encode())
        self.exporter.export_codex(False, False)
        self.source.write_bytes(complete.encode() + partial.encode())
        self.exporter.export_codex(False, False)
        text = next(self.output.glob("*.md")).read_text(encoding="utf-8")
        self.assertIn("message_count: 3", text)
        self.assertIn("later", text)

    def test_lineage_uses_first_session_metadata(self) -> None:
        child_id = "11111111-1111-1111-1111-111111111111"
        root_id = "22222222-2222-2222-2222-222222222222"
        self.source.write_text(
            "".join(
                [
                    record(
                        "session_meta",
                        {
                            "id": child_id,
                            "session_id": root_id,
                            "parent_thread_id": root_id,
                            "forked_from_id": root_id,
                            "agent_path": "/root/worker",
                            "agent_role": "worker",
                            "cwd": "/tmp/project",
                            "source": {"subagent": {}},
                        },
                        "2026-09-09T14:00:00Z",
                    ),
                    record(
                        "session_meta",
                        {"id": root_id, "session_id": root_id, "cwd": "/tmp/project", "source": "cli"},
                        "2026-09-09T14:00:00Z",
                    ),
                    record(
                        "response_item",
                        {"id": "a1", "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "child reply"}]},
                        "2026-09-09T14:00:01Z",
                    ),
                ]
            ),
            encoding="utf-8",
        )
        self.exporter.export_codex(False, False)
        metadata = self.exporter.parse_export_metadata(next(self.output.glob("*.md")))
        self.assertEqual(metadata["session_id"], child_id)
        self.assertEqual(metadata["root_thread_id"], root_id)
        self.assertEqual(metadata["parent_thread_id"], root_id)
        self.assertEqual(metadata["agent_path"], "/root/worker")

    def test_archived_rollouts_are_exported(self) -> None:
        self.source.write_text(self.initial_rollout(), encoding="utf-8")
        archived = (
            self.codex_home
            / "archived_sessions"
            / "rollout-2026-09-08T10-00-00-33333333-3333-3333-3333-333333333333.jsonl"
        )
        archived.parent.mkdir(parents=True)
        archived.write_text(
            self.initial_rollout().replace(
                "11111111-1111-1111-1111-111111111111",
                "33333333-3333-3333-3333-333333333333",
            ),
            encoding="utf-8",
        )
        result = self.exporter.export_codex(False, False)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(len(list(self.output.glob("*_chunk-*.md"))), 2)

    def test_verifier_detects_tampered_export_metadata(self) -> None:
        self.source.write_text(self.initial_rollout(), encoding="utf-8")
        self.exporter.export_codex(False, False)
        target = next(self.output.glob("*.md"))
        target.write_text(target.read_text().replace("message_count: 2", "message_count: 1"))
        result = self.exporter.verify_exports()
        self.assertFalse(result["ok"])
        self.assertIn("message count mismatch", result["failures"][0])

    def test_carriage_returns_do_not_force_chunk_rewrites(self) -> None:
        source = self.initial_rollout().replace("answer", "step 1\rstep 2")
        self.source.write_text(source, encoding="utf-8", newline="")
        self.exporter.export_codex(False, False)
        cache = self.exporter.state_path("11111111-1111-1111-1111-111111111111")
        os.utime(cache, ns=(self.source.stat().st_mtime_ns - 1, self.source.stat().st_mtime_ns - 1))
        result = self.exporter.export_codex(False, False)
        self.assertEqual(result["chunks_written"], 0)
        self.assertEqual(result["chunks_unchanged"], 1)

    def test_only_last_bounded_chunk_changes_after_append(self) -> None:
        with mock.patch.object(self.exporter, "MAX_CHUNK_CHARS", 20):
            self.source.write_text(self.initial_rollout(), encoding="utf-8")
            self.exporter.export_codex(False, False)
            chunks = sorted(self.output.glob("*_chunk-*.md"))
            self.assertEqual(len(chunks), 2)
            first_bytes = chunks[0].read_bytes()
            with self.source.open("a", encoding="utf-8") as handle:
                handle.write(
                    record(
                        "response_item",
                        {"id": "u2", "type": "message", "role": "user", "content": [{"type": "input_text", "text": "third"}]},
                        "2026-09-09T14:00:03Z",
                    )
                )
            result = self.exporter.export_codex(False, False)
            self.assertEqual(result["chunks_written"], 1)
            self.assertEqual(chunks[0].read_bytes(), first_bytes)

    def test_compaction_and_tool_metadata_do_not_rewrite_chunks(self) -> None:
        self.source.write_text(self.initial_rollout(), encoding="utf-8")
        self.exporter.export_codex(False, False)
        before = next(self.output.glob("*_chunk-*.md")).read_bytes()
        with self.source.open("a", encoding="utf-8") as handle:
            handle.write(
                record(
                    "compacted",
                    {"replacement_history": [{"type": "compaction", "encrypted_content": "opaque"}]},
                    "2026-09-09T14:00:03Z",
                )
            )
            handle.write(
                record(
                    "response_item",
                    {"type": "custom_tool_call", "name": "apply_patch", "input": "*** Update File: x.py"},
                    "2026-09-09T14:00:04Z",
                )
            )
        result = self.exporter.export_codex(False, False)
        self.assertEqual(result["chunks_written"], 0)
        self.assertEqual(next(self.output.glob("*_chunk-*.md")).read_bytes(), before)


class RefreshWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hook = load_hook()

    def completed(self, stdout: str, returncode: int = 0):
        return type("Completed", (), {"stdout": stdout, "stderr": "", "returncode": returncode})()

    def test_skips_qmd_when_no_export_changed(self) -> None:
        payload = json.dumps({"codex": {"exported": 0}, "claude": {"exported": 0}})
        with tempfile.TemporaryFile(mode="w+") as log, mock.patch.object(
            self.hook.subprocess, "run", return_value=self.completed(payload)
        ) as run, mock.patch.object(self.hook.shutil, "which", return_value="/usr/bin/qmd"):
            self.assertTrue(self.hook.run_refresh(log))
        self.assertEqual(run.call_count, 1)

    def test_updates_and_embeds_when_an_export_changed(self) -> None:
        payload = json.dumps({"codex": {"exported": 1}, "claude": {"exported": 0}})
        calls = [self.completed(payload), self.completed(""), self.completed("")]
        with tempfile.TemporaryFile(mode="w+") as log, mock.patch.object(
            self.hook.subprocess, "run", side_effect=calls
        ) as run, mock.patch.object(self.hook.shutil, "which", return_value="/usr/bin/qmd"):
            self.assertTrue(self.hook.run_refresh(log))
        self.assertEqual(run.call_args_list[1].args[0], ["/usr/bin/qmd", "update"])
        self.assertEqual(
            run.call_args_list[2].args[0],
            ["/usr/bin/qmd", "embed", "-c", "Codex-sessions"],
        )


class WorkerLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hook = load_hook()
        self.temporary = tempfile.TemporaryDirectory()
        logs = Path(self.temporary.name)
        self.patches = [
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

    def test_a_request_during_a_refresh_runs_one_more_pass(self) -> None:
        calls = []

        def refresh(log):
            calls.append(1)
            if len(calls) == 1:
                self.hook.PENDING.touch()
            return True

        self.hook.PENDING.touch()
        with mock.patch.object(self.hook, "run_refresh", side_effect=refresh):
            self.hook.worker()
        self.assertEqual(len(calls), 2)
        self.assertFalse(self.hook.PENDING.exists())


class HostedWiringTests(unittest.TestCase):
    """The Codex hook's hosted-mode switch. memoria_push itself is tested in hooks/."""

    def setUp(self) -> None:
        self.hook = load_hook()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = self.root / "memoria.json"
        self.marker = self.root / "memoria-push.pending"
        self.patches = [
            mock.patch.dict(os.environ, {"AGENT_SKILLS_MEMORIA_CONFIG": str(self.config)}),
            mock.patch.object(self.hook, "PUSH_PENDING", self.marker),
            mock.patch.object(self.hook, "PUSH_STATE", self.root / "push-state"),
            mock.patch.object(self.hook, "CODEX_HOME", self.root / "codex"),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def configure(self) -> None:
        self.config.write_text(json.dumps({"push": True, "url": "https://memoria.example.com"}))

    def request(self, event: str) -> None:
        with mock.patch("sys.stdin", io.StringIO(json.dumps({"hook_event_name": event}))):
            self.hook.request_push()

    def test_unconfigured_reads_no_input_and_marks_nothing(self) -> None:
        with mock.patch("sys.stdin") as stdin:
            self.hook.request_push()
        stdin.read.assert_not_called()
        self.assertFalse(self.marker.exists())

    def test_only_session_end_marks_a_push(self) -> None:
        self.configure()
        for event in ("Stop", "SubagentStop", "PostCompact"):
            self.request(event)
            self.assertFalse(self.marker.exists(), event)
        self.request("SessionEnd")
        self.assertTrue(self.marker.exists())

    def test_the_shared_module_is_found_from_the_codex_hook(self) -> None:
        self.assertTrue(self.hook.PUSH_MODULE.is_file(), self.hook.PUSH_MODULE)

    def test_worker_sends_codex_rollouts_when_marked(self) -> None:
        self.configure()
        self.marker.touch()
        push = self.hook.load_push()
        with mock.patch.object(self.hook, "load_push", return_value=push), \
                mock.patch.object(push, "run", return_value={}) as run, tempfile.TemporaryFile("w+") as log:
            self.hook.push_if_requested(log)
        settings, sources, state_dir, _ = run.call_args.args
        self.assertEqual(settings.origin, "https://memoria.example.com:443")
        self.assertEqual(sources, [])
        self.assertEqual(state_dir, self.root / "push-state")
        self.assertFalse(self.marker.exists())

    def test_worker_does_nothing_unconfigured(self) -> None:
        self.marker.touch()
        with mock.patch.object(self.hook, "load_push", wraps=self.hook.load_push), \
                tempfile.TemporaryFile("w+") as log:
            self.hook.push_if_requested(log)
            log.seek(0)
            self.assertEqual(log.read(), "")
        self.assertTrue(self.marker.exists())


class RecallBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = load(BACKEND_PATH, "codex_recall_backend")
        self.temporary = tempfile.TemporaryDirectory()
        self.config = Path(self.temporary.name) / "memoria.json"
        self.env = mock.patch.dict(os.environ, {"AGENT_SKILLS_MEMORIA_CONFIG": str(self.config)})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.temporary.cleanup()

    def test_reaches_the_shared_helper(self) -> None:
        self.assertTrue(self.backend.SHARED.is_file(), self.backend.SHARED)
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(self.backend.main([]), 0)
        self.assertEqual(json.loads(out.getvalue())["backend"], "qmd")

    def test_memoria_query_for_codex_goes_through_the_cli(self) -> None:
        self.config.write_text(json.dumps({"search": "memoria", "cli": "memoria"}))
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0)) as run:
            self.assertEqual(self.backend.main(["query", "retries", "--harness", "codex"]), 0)
        command = run.call_args.args[0]
        self.assertIn("codex-sessions", command)
        self.assertNotIn("claude-sessions", command)
        self.assertEqual(command[-2:], ["--", "retries"])

    def test_missing_shared_helper_says_so(self) -> None:
        with mock.patch.object(self.backend, "SHARED", Path(self.temporary.name) / "absent.py"), \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(self.backend.main([]), 2)
        self.assertIn("missing", err.getvalue())


if __name__ == "__main__":
    unittest.main()
