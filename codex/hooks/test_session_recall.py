from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

EXPORTER_PATH = Path(__file__).resolve().parents[1] / "skills" / "recall" / "scripts" / "export_sessions.py"
HOOK_PATH = Path(__file__).resolve().parent / "session-end-export.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location("codex_recall_exporter", EXPORTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_hook():
    spec = importlib.util.spec_from_file_location("codex_recall_hook", HOOK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


if __name__ == "__main__":
    unittest.main()
