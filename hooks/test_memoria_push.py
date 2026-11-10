"""Tests for hosted mode: pushing transcripts to Memoria, and recall's backend switch.

Run: python3 -m unittest hooks.test_memoria_push  (or discover -s hooks)
Everything runs in temp dirs against a fake server on 127.0.0.1; no real network,
no real keyring entry, and the real ~/.claude and ~/.config are never touched.
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

HOOKS = Path(__file__).resolve().parent
HOOK_PATH = HOOKS / "session-end-export.py"
PUSH_PATH = HOOKS / "memoria_push.py"
BACKEND_PATH = HOOKS.parent / "skills" / "recall" / "recall_backend.py"
SESSION_ID = "abcdef12-3456-7890-abcd-ef1234567890"
CODEX_ID = "0199aaaa-bbbb-7ccc-8ddd-eeeeffff0000"
KEY = "mem_testkey_0123456789abcdef"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def record(role: str, text: str, second: int, cwd: bool = True) -> str:
    value = {
        "type": role,
        "timestamp": f"2026-10-01T10:00:{second:02d}Z",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    }
    if cwd:
        value["cwd"] = "/tmp/demo"
    return json.dumps(value) + "\n"


class FakeMemoria:
    """A scripted stand-in for POST /v1/ingest/session."""

    def __init__(self) -> None:
        self.requests: list = []
        self.replies: list = []  # (status, body) per request; then 202
        self.delay = 0.0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                url = urlsplit(self.path)
                fake.requests.append({
                    "path": url.path,
                    "query": {k: v[0] for k, v in parse_qs(url.query).items()},
                    "headers": dict(self.headers),
                    "body": body,
                })
                if fake.delay:
                    time.sleep(fake.delay)
                status, reply = fake.replies.pop(0) if fake.replies else (202, {"complete": True})
                data = json.dumps(reply).encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except OSError:  # the client gave up first, as the timeout tests intend
                    pass

            def log_message(self, *args) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def closed_port_url() -> str:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}"


class Sandbox(unittest.TestCase):
    """Temp home for config, transcripts, logs and push state."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = self.root / "config" / "agent-skills" / "memoria.json"
        self.projects = self.root / "projects"
        self.transcript = self.projects / "-tmp-demo" / f"{SESSION_ID}.jsonl"
        self.transcript.parent.mkdir(parents=True)
        self.state = self.root / "push-state"
        self.logs = self.root / "logs"
        self.env = mock.patch.dict(os.environ, {
            "AGENT_SKILLS_MEMORIA_CONFIG": str(self.config),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "MEMORIA_API_KEY": KEY,
        })
        self.env.start()
        for name in ("MEMORIA_URL", "MEMORIA_PROFILE", "MEMORIA_ALLOW_INSECURE_HTTP"):
            os.environ.pop(name, None)
        self.push = load(PUSH_PATH, "memoria_push_under_test")
        self.messages: list = []
        self.server = None

    def tearDown(self) -> None:
        if self.server:
            self.server.close()
        self.env.stop()
        self.temporary.cleanup()

    def start_server(self) -> FakeMemoria:
        self.server = FakeMemoria()
        return self.server

    def configure(self, **values) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps({"push": True, "since": "2020-01-01", **values}))

    def settings(self):
        return self.push.load_settings()

    def run_push(self, sources=None) -> dict:
        sources = self.push.claude_sources(self.projects) if sources is None else sources
        return self.push.run(self.settings(), sources, self.state, self.messages.append)

    def spooled(self) -> list:
        spool = self.state / "spool"
        return sorted(spool.glob("*.json")) if spool.is_dir() else []

    def log_text(self) -> str:
        return "\n".join(self.messages)


class UnconfiguredTests(Sandbox):
    """With no config, or push not true, nothing changes."""

    def test_no_file_and_push_not_true_are_off(self) -> None:
        self.assertIsNone(self.settings())
        self.assertFalse(self.push.push_enabled())
        for values in ({}, {"push": False}, {"push": "yes"}, {"search": "memoria"}):
            self.config.parent.mkdir(parents=True, exist_ok=True)
            self.config.write_text(json.dumps(values))
            self.assertIsNone(self.settings(), values)
            self.assertFalse(self.push.push_enabled(), values)

    def test_unreadable_config_counts_as_on_so_the_worker_can_say_why(self) -> None:
        self.config.parent.mkdir(parents=True)
        self.config.write_text("{not json")
        self.assertTrue(self.push.push_enabled())
        with self.assertRaises(self.push.ConfigError):
            self.settings()

    def test_hook_does_not_read_stdin_or_mark_a_push_when_off(self) -> None:
        hook = load(HOOK_PATH, "hook_unconfigured")
        with mock.patch.object(hook, "LOG_DIR", self.logs), \
                mock.patch.object(hook, "PUSH_PENDING", self.logs / "memoria-push.pending"), \
                mock.patch("sys.stdin") as stdin:
            hook.request_push()
        stdin.read.assert_not_called()
        self.assertFalse(self.logs.exists())

    def test_worker_leaves_everything_alone_when_off(self) -> None:
        hook = load(HOOK_PATH, "hook_unconfigured_worker")
        marker = self.root / "memoria-push.pending"
        marker.touch()
        with mock.patch.object(hook, "PUSH_PENDING", marker), \
                mock.patch.object(hook, "PUSH_STATE", self.state), \
                tempfile.TemporaryFile("w+") as log:
            hook.push_if_requested(log)
            log.seek(0)
            self.assertEqual(log.read(), "")
        self.assertTrue(marker.exists())
        self.assertFalse(self.state.exists())


class SettingsTests(Sandbox):
    def test_url_rules_match_the_cli(self) -> None:
        check = self.push.check_url
        self.assertEqual(check("https://memoria.example.com", False), "https://memoria.example.com:443")
        self.assertEqual(check("http://127.0.0.1:8080", False), "http://127.0.0.1:8080")
        self.assertEqual(check("http://localhost", False), "http://localhost:80")
        self.assertEqual(check("http://10.0.0.5:5000", False), "http://10.0.0.5:5000")
        for refused in ("http://memoria.example.com", "http://8.8.8.8", "http://169.254.169.254",
                        "ftp://memoria.example.com", "https://user:pw@memoria.example.com"):
            with self.assertRaises(self.push.ConfigError, msg=refused):
                check(refused, False)
        self.assertEqual(check("http://memoria.example.com", True), "http://memoria.example.com:80")

    def test_url_falls_back_to_the_cli_profile(self) -> None:
        cli = self.root / "config" / "memoria" / "config.json"
        cli.parent.mkdir(parents=True)
        cli.write_text(json.dumps({"active_profile": "work",
                                   "profiles": {"work": {"api_url": "https://memoria.example.com/"}}}))
        self.configure()
        settings = self.settings()
        self.assertEqual((settings.url, settings.profile), ("https://memoria.example.com", "work"))

    def test_push_without_a_server_is_a_config_error(self) -> None:
        self.configure()
        with self.assertRaises(self.push.ConfigError):
            self.settings()


class KeyTests(Sandbox):
    def stored(self, origin: str) -> str:
        return json.dumps({"origin": origin, "key": KEY})

    def test_env_key_wins(self) -> None:
        self.configure(url="https://memoria.example.com")
        with mock.patch.object(self.push, "keyring_get", side_effect=AssertionError("keyring read")):
            self.assertEqual(self.push.resolve_key(self.settings()), KEY)

    def test_keyring_key_goes_only_to_its_own_server(self) -> None:
        os.environ.pop("MEMORIA_API_KEY")
        self.configure(url="https://memoria.example.com", profile="desk")
        names = []
        with mock.patch.object(self.push, "keyring_get",
                               side_effect=lambda name: names.append(name) or self.stored("https://memoria.example.com:443")):
            self.assertEqual(self.push.resolve_key(self.settings()), KEY)
        self.assertEqual(names, ["desk/api-key"])
        with mock.patch.object(self.push, "keyring_get", return_value=self.stored("https://other.example.com:443")):
            with self.assertRaises(self.push.CredentialError) as raised:
                self.push.resolve_key(self.settings())
        self.assertNotIn(KEY, str(raised.exception))
        with mock.patch.object(self.push, "keyring_get", return_value=None):
            with self.assertRaises(self.push.CredentialError):
                self.push.resolve_key(self.settings())

    @unittest.skipUnless(os.name == "nt", "Credential Manager")
    def test_windows_missing_credential_is_none(self) -> None:
        self.assertIsNone(self.push.keyring_get("agent-skills-test-profile-that-does-not-exist/api-key"))

    def test_no_key_leaves_the_spool_alone(self) -> None:
        os.environ.pop("MEMORIA_API_KEY")
        server = self.start_server()
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        with mock.patch.object(self.push, "keyring_get", return_value=None):
            summary = self.run_push()
        self.assertEqual(summary["waiting"], 1)
        self.assertEqual(server.requests, [])
        self.assertEqual(len(self.spooled()), 1)
        self.assertIn("memoria auth login", self.log_text())


class PushTests(Sandbox):
    def test_sends_the_raw_transcript_to_the_session_route(self) -> None:
        server = self.start_server()
        self.configure(url=server.url, collections={"claude": "desk-claude"})
        self.transcript.write_text(record("user", "hello", 1) + record("assistant", "hi", 2))
        self.assertEqual(self.run_push()["sent"], 1)
        [request] = server.requests
        self.assertEqual(request["path"], "/v1/ingest/session")
        self.assertEqual(request["query"]["format"], "claude")
        self.assertEqual(request["query"]["sessionId"], SESSION_ID)
        self.assertEqual(request["query"]["projectDirectory"], "-tmp-demo")
        self.assertEqual(request["query"]["collection"], "desk-claude")
        self.assertRegex(request["query"]["updated"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        self.assertEqual(request["headers"]["Authorization"], f"Bearer {KEY}")
        self.assertEqual(request["headers"]["Content-Type"], "application/x-ndjson")
        self.assertEqual(request["body"], self.transcript.read_bytes())
        self.assertEqual(self.spooled(), [])
        self.assertNotIn(KEY, self.log_text())

    def test_codex_rollouts_go_as_codex(self) -> None:
        server = self.start_server()
        self.configure(url=server.url)
        rollout = self.root / "codex" / "sessions" / "2026" / "10" / f"rollout-2026-10-01T10-00-00-{CODEX_ID}.jsonl"
        rollout.parent.mkdir(parents=True)
        rollout.write_text('{"type":"session_meta"}\n')
        self.run_push(self.push.codex_sources(self.root / "codex"))
        [request] = server.requests
        self.assertEqual(request["query"]["format"], "codex")
        self.assertEqual(request["query"]["sessionId"], CODEX_ID)
        self.assertEqual(request["query"]["collection"], "codex-sessions")
        self.assertNotIn("projectDirectory", request["query"])

    def test_half_written_last_line_is_held_back(self) -> None:
        server = self.start_server()
        self.configure(url=server.url)
        whole = record("user", "hello", 1)
        self.transcript.write_bytes((whole + '{"type": "assist').encode())
        self.run_push()
        self.assertEqual(server.requests[0]["body"], whole.encode())

    def test_transcript_without_cwd_is_reported(self) -> None:
        server = self.start_server()
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1, cwd=False))
        self.run_push()
        self.assertEqual(len(server.requests), 1)
        self.assertIn("has no cwd", self.log_text())

    def test_sessions_older_than_since_are_left_to_migration(self) -> None:
        server = self.start_server()
        self.configure(url=server.url, since="2999-01-01T00:00:00Z")
        self.transcript.write_text(record("user", "hello", 1))
        self.run_push()
        self.assertEqual(server.requests, [])

    def test_first_run_baseline_is_when_the_config_was_written(self) -> None:
        server = self.start_server()
        self.transcript.write_text(record("user", "old", 1))
        old = time.time() - 3600
        os.utime(self.transcript, (old, old))
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"push": True, "url": server.url}))
        self.run_push()
        self.assertEqual(server.requests, [])
        with self.transcript.open("a") as handle:
            handle.write(record("user", "resumed", 2))
        self.run_push()
        self.assertEqual(len(server.requests), 1)


class IdempotencyTests(Sandbox):
    def test_unchanged_transcript_is_not_sent_again(self) -> None:
        server = self.start_server()
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        self.run_push()
        self.run_push()
        self.assertEqual(len(server.requests), 1)

    def test_reexport_updates_the_same_session(self) -> None:
        server = self.start_server()
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        self.run_push()
        time.sleep(0.01)
        with self.transcript.open("a") as handle:
            handle.write(record("assistant", "more", 2))
        later = time.time() + 5
        os.utime(self.transcript, (later, later))
        self.run_push()
        first, second = server.requests
        self.assertEqual(first["query"]["sessionId"], second["query"]["sessionId"])
        self.assertEqual(first["query"]["projectDirectory"], second["query"]["projectDirectory"])
        self.assertLess(first["query"]["updated"], second["query"]["updated"])
        self.assertIn(b"more", second["body"])

    def test_spooling_twice_keeps_one_entry_per_transcript(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        self.transcript.write_text(record("user", "hello", 1))
        self.run_push()
        with self.transcript.open("a") as handle:
            handle.write(record("assistant", "more", 2))
        self.run_push()
        self.assertEqual(len(self.spooled()), 1)
        entry = json.loads(self.spooled()[0].read_text())
        self.assertEqual(entry["size"], self.transcript.stat().st_size)

    def test_stale_version_counts_as_done(self) -> None:
        server = self.start_server()
        server.replies = [(409, {"code": "stale_version"})]
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        self.run_push()
        self.run_push()
        self.assertEqual(len(server.requests), 1)
        self.assertEqual(self.spooled(), [])


class SpoolTests(Sandbox):
    def test_unreachable_server_spools_then_the_next_run_sends(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        self.transcript.write_text(record("user", "hello", 1))
        summary = self.run_push()
        self.assertEqual((summary["sent"], summary["waiting"]), (0, 1))
        [entry_path] = self.spooled()
        self.assertTrue(entry_path.with_suffix(".jsonl").exists(), "no copy kept for a retry")
        self.assertIn("unreachable", self.log_text())

        server = self.start_server()
        self.configure(url=server.url)
        self.assertEqual(self.run_push()["sent"], 1)
        self.assertEqual(len(server.requests), 1)
        self.assertEqual(self.spooled(), [])
        self.assertEqual(list((self.state / "spool").iterdir()), [])

    def test_the_kept_copy_is_sent_if_the_transcript_is_cleaned_up(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        self.transcript.write_text(record("user", "keep me", 1))
        sent_bytes = self.transcript.read_bytes()
        self.run_push()
        self.transcript.unlink()
        server = self.start_server()
        self.configure(url=server.url)
        self.run_push()
        [request] = server.requests
        self.assertEqual(request["body"], sent_bytes)

    def test_one_unreachable_session_stops_the_run_and_keeps_the_rest(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        for index in range(3):
            path = self.projects / "-tmp-demo" / f"{SESSION_ID[:-1]}{index}.jsonl"
            path.write_text(record("user", f"s{index}", 1))
        started = time.monotonic()
        summary = self.run_push()
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(summary["waiting"], 3)
        self.assertEqual(self.log_text().count("unreachable"), 1)

    def test_slow_server_is_cut_off_by_the_timeout(self) -> None:
        server = self.start_server()
        server.delay = 3
        self.configure(url=server.url, timeout=0.5)
        self.transcript.write_text(record("user", "hello", 1))
        started = time.monotonic()
        summary = self.run_push()
        self.assertLess(time.monotonic() - started, 2.5)
        self.assertEqual(summary["waiting"], 1)
        self.assertEqual(len(self.spooled()), 1)

    def test_budget_leaves_the_rest_for_the_next_run(self) -> None:
        server = self.start_server()
        server.delay = 0.3
        self.configure(url=server.url, budget=0.1)
        for index in range(3):
            (self.projects / "-tmp-demo" / f"{SESSION_ID[:-1]}{index}.jsonl").write_text(record("user", "x", 1))
        summary = self.run_push()
        self.assertEqual((summary["sent"], summary["waiting"]), (1, 2))
        self.assertIn("budget spent", self.log_text())

    def test_server_errors_and_auth_refusals_keep_the_entry(self) -> None:
        for status, code in ((503, "ingest_busy"), (401, "invalid_key"), (429, "rate_limited"), (404, ""),
                             (409, "ingest_not_enabled")):
            with self.subTest(status=status):
                server = self.start_server()
                server.replies = [(status, {"code": code})]
                self.configure(url=server.url)
                self.transcript.write_text(record("user", f"try {status}", 1))
                summary = self.run_push()
                self.assertEqual((summary["sent"], summary["held"]), (0, 0))
                [entry] = self.spooled()
                self.assertIsNone(json.loads(entry.read_text())["held"])
                self.assertEqual(self.run_push()["sent"], 1, "not retried on the next run")
                server.close()
                self.server = None

    def test_partial_upload_that_can_be_finished_is_sent_again(self) -> None:
        server = self.start_server()
        server.replies = [(207, {"complete": False, "retryable": True})]
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        self.run_push()
        self.assertEqual(len(self.spooled()), 1)
        self.run_push()
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(self.spooled(), [])


class RefusalTests(Sandbox):
    def test_session_shrank_is_held_and_surfaced_not_retried_or_dropped(self) -> None:
        server = self.start_server()
        server.replies = [(409, {"code": "session_shrank"})]
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        self.assertEqual(self.run_push()["held"], 1)
        self.assertIn("NEEDS ATTENTION", self.log_text())
        self.assertIn("session_shrank", self.log_text())
        self.messages.clear()

        self.run_push()
        self.assertEqual(len(server.requests), 1, "a held session was sent again unchanged")
        self.assertIn("NEEDS ATTENTION", self.log_text(), "held sessions must be reported on every run")
        self.assertEqual(len(self.spooled()), 1)

        with self.transcript.open("a") as handle:
            handle.write(record("assistant", "more", 2))
        later = time.time() + 5
        os.utime(self.transcript, (later, later))
        self.run_push()
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(self.spooled(), [])

    def test_payload_too_large_is_held_not_retried(self) -> None:
        server = self.start_server()
        server.replies = [(413, {"code": "payload_too_large"})]
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        self.assertEqual(self.run_push()["held"], 1)
        self.run_push()
        self.assertEqual(len(server.requests), 1)
        self.assertIn("payload_too_large", self.log_text())

    def test_one_held_session_does_not_stop_the_others(self) -> None:
        server = self.start_server()
        server.replies = [(409, {"code": "path_owned"})]
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "a", 1))
        other = self.projects / "-tmp-demo" / f"{SESSION_ID[:-1]}9.jsonl"
        other.write_text(record("user", "b", 1))
        later = time.time() + 5
        os.utime(other, (later, later))
        summary = self.run_push()
        self.assertEqual((summary["held"], summary["sent"]), (1, 1))


class CuttingServer:
    """Reads a little of an upload, answers 413 and resets the connection, as a server
    does when a body runs past its own limit: a client still sending sees a reset."""

    def __init__(self) -> None:
        self.connections = 0
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.url = f"http://127.0.0.1:{self.listener.getsockname()[1]}"
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self) -> None:
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            self.connections += 1
            with connection:
                connection.recv(4096)
                connection.sendall(b"HTTP/1.1 413 Payload Too Large\r\nContent-Length: 0\r\n\r\n")
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\x01\x00\x00\x00\x00\x00\x00\x00")

    def close(self) -> None:
        self.listener.close()


class TooLargeTests(Sandbox):
    def large_transcript(self) -> int:
        with self.transcript.open("w") as handle:
            for second in range(60):
                handle.write(record("user", "x" * 100_000, second))
        return self.transcript.stat().st_size

    def test_a_cut_off_upload_looks_like_an_outage_so_it_would_be_tried_forever(self) -> None:
        cutting = CuttingServer()
        self.addCleanup(cutting.close)
        self.configure(url=cutting.url)
        self.large_transcript()
        for _ in range(2):
            self.assertEqual(self.run_push()["held"], 0)
        self.assertEqual(cutting.connections, 2)
        self.assertIn("unreachable", self.log_text())

    def test_a_transcript_over_the_limit_is_held_without_being_sent(self) -> None:
        cutting = CuttingServer()
        self.addCleanup(cutting.close)
        size = self.large_transcript()
        self.configure(url=cutting.url, max_session_bytes=size - 1)
        self.assertEqual(self.run_push()["held"], 1)
        self.messages.clear()
        self.assertEqual(self.run_push()["held"], 1)
        self.assertEqual(cutting.connections, 0, "a transcript over the limit was sent")
        self.assertIn("NEEDS ATTENTION", self.log_text())
        self.assertIn(f"{size} bytes, over the server's {size - 1} byte limit", self.log_text())

    def test_the_limit_defaults_to_the_servers_and_must_be_a_whole_number(self) -> None:
        self.configure(url="https://memoria.example")
        self.assertEqual(self.settings().max_session_bytes, 256 * 1024 * 1024)
        for bad in (0, -1, 1.5, True, "big"):
            self.configure(url="https://memoria.example", max_session_bytes=bad)
            with self.assertRaises(self.push.ConfigError):
                self.settings()

    def test_no_copy_is_kept_of_a_transcript_too_large_to_send(self) -> None:
        size = self.large_transcript()
        self.configure(url=closed_port_url(), max_session_bytes=size - 1)
        # The small one is older, so it goes first, finds the server down and stops the run, which keeps copies of the rest.
        other = self.projects / "-tmp-demo" / f"{SESSION_ID[:-1]}9.jsonl"
        other.write_text(record("user", "small", 1))
        earlier = self.transcript.stat().st_mtime - 60
        os.utime(other, (earlier, earlier))
        self.assertEqual(self.run_push()["waiting"], 2)
        copies = list((self.state / "spool").glob("*.jsonl"))
        self.assertEqual(len(copies), 1, "the small transcript's copy is missing")
        self.assertLess(copies[0].stat().st_size, size, "the oversized transcript was copied")


class HookTests(Sandbox):
    """The real hook as a subprocess, as Claude Code runs it."""

    def setUp(self) -> None:
        super().setUp()
        if os.name == "nt":
            fake_qmd = self.root / "qmd.cmd"
            fake_qmd.write_text("@exit /b 0\n")
        else:
            fake_qmd = self.root / "qmd"
            fake_qmd.write_text("#!/bin/sh\nexit 0\n")
            fake_qmd.chmod(0o755)
        self.hook_env = {
            **os.environ,
            "CLAUDE_RECALL_PROJECTS": str(self.projects),
            "CLAUDE_RECALL_OUTPUT": str(self.root / "sessions"),
            "CLAUDE_RECALL_STATE": str(self.root / "export-state"),
            "CLAUDE_RECALL_LOG_DIR": str(self.logs),
            "CLAUDE_RECALL_PUSH_STATE": str(self.state),
            "CLAUDE_RECALL_QMD": str(fake_qmd),
        }

    def fire(self, event: str, runs: int) -> tuple:
        started = time.monotonic()
        result = subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps({"hook_event_name": event}),
                                text=True, capture_output=True, env=self.hook_env, timeout=20)
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.logs / "session-end-export.log"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            text = log.read_text() if log.exists() else ""
            if text.count("refresh finished") >= runs and not (self.logs / "session-recall.pending").exists():
                return elapsed, text
            time.sleep(0.05)
        self.fail(f"worker did not finish: {log.read_text() if log.exists() else 'no log'}")

    def test_unconfigured_hook_changes_nothing(self) -> None:
        server = self.start_server()
        self.transcript.write_text(record("user", "hello", 1))
        _, text = self.fire("SessionEnd", 1)
        self.assertEqual(server.requests, [])
        self.assertNotIn("memoria", text)
        self.assertFalse((self.logs / "memoria-push.pending").exists())
        self.assertFalse(self.state.exists())
        self.assertEqual(len(list((self.root / "sessions").glob("*.md"))), 1, "local export not written")

    def test_configured_hook_exports_locally_then_pushes_on_session_end_only(self) -> None:
        server = self.start_server()
        self.configure(url=server.url)
        self.transcript.write_text(record("user", "hello", 1))
        elapsed, _ = self.fire("Stop", 1)
        self.assertLess(elapsed, 3.0)
        self.assertEqual(server.requests, [], "pushed on Stop")

        elapsed, text = self.fire("SessionEnd", 2)
        self.assertLess(elapsed, 3.0)
        self.assertEqual(len(server.requests), 1)
        self.assertEqual(server.requests[0]["query"]["sessionId"], SESSION_ID)
        self.assertIn("memoria: sent", text)
        self.assertEqual(len(list((self.root / "sessions").glob("*.md"))), 1, "local export not written")

    def test_session_end_returns_fast_while_the_server_is_down(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        self.transcript.write_text(record("user", "hello", 1))
        elapsed, text = self.fire("SessionEnd", 1)
        self.assertLess(elapsed, 3.0)
        self.assertIn("kept claude session", text)
        self.assertEqual(len(self.spooled()), 1)

    def test_broken_config_is_logged_and_the_export_still_runs(self) -> None:
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{"push": true, "url": "http://memoria.example.com"}')
        self.transcript.write_text(record("user", "hello", 1))
        _, text = self.fire("SessionEnd", 1)
        self.assertIn("push is not configured correctly", text)
        self.assertEqual(len(list((self.root / "sessions").glob("*.md"))), 1)


class ReviewRegressionTests(Sandbox):
    def make_sessions(self, count: int) -> list:
        paths = []
        for index in range(count):
            path = self.projects / "-tmp-demo" / f"{SESSION_ID[:-2]}{index:02d}.jsonl"
            path.write_text(record("user", f"s{index}", 1))
            stamp = time.time() + index
            os.utime(path, (stamp, stamp))
            paths.append(path)
        return paths

    def test_missing_module_is_silent_in_both_hook_halves(self) -> None:
        hook = load(HOOK_PATH, "hook_partial_install")
        self.configure(url="https://memoria.example.com")
        marker = self.root / "memoria-push.pending"
        marker.touch()
        with mock.patch.object(hook, "PUSH_MODULE", self.root / "absent.py"), \
                mock.patch.object(hook, "PUSH_PENDING", marker), mock.patch("sys.stdin") as stdin, \
                tempfile.TemporaryFile("w+") as log:
            hook.request_push()
            hook.push_if_requested(log)
            log.seek(0)
            self.assertEqual(log.read(), "")
        stdin.read.assert_not_called()

    def test_config_path_that_is_not_a_file_is_off(self) -> None:
        self.config.mkdir(parents=True)
        self.assertFalse(self.push.push_enabled())

    def test_upper_case_scheme_still_bypasses_proxies(self) -> None:
        server = self.start_server()
        self.configure(url=server.url.replace("http://", "HTTP://"))
        self.assertTrue(self.settings().url.startswith("http://"))
        self.transcript.write_text(record("user", "hello", 1))
        with mock.patch.dict(os.environ, {"HTTP_PROXY": closed_port_url(), "http_proxy": closed_port_url()}):
            self.assertEqual(self.run_push()["sent"], 1)

    def test_url_with_a_query_is_refused(self) -> None:
        with self.assertRaises(self.push.ConfigError):
            self.push.check_url("https://memoria.example.com/?x=1", False)

    def test_every_untried_entry_gets_a_copy_when_a_run_stops(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        self.make_sessions(3)
        self.run_push()
        for entry in self.spooled():
            self.assertTrue(entry.with_suffix(".jsonl").exists(), entry.name)

    def test_every_entry_gets_a_copy_while_there_is_no_key(self) -> None:
        os.environ.pop("MEMORIA_API_KEY")
        self.configure(url=closed_port_url())
        paths = self.make_sessions(2)
        with mock.patch.object(self.push, "keyring_get", return_value=None):
            self.run_push()
        for path in paths:
            path.unlink()
        server = self.start_server()
        self.configure(url=server.url)
        os.environ["MEMORIA_API_KEY"] = KEY
        self.assertEqual(self.run_push()["sent"], 2)

    def test_an_entry_that_keeps_failing_goes_behind_the_others(self) -> None:
        self.configure(url=closed_port_url(), timeout=2)
        first, second = self.make_sessions(2)
        self.run_push()  # the oldest is tried and fails once
        server = self.start_server()
        self.configure(url=server.url)
        server.replies = [(503, {"code": "ingest_busy"})]
        self.run_push()
        self.assertEqual(server.requests[0]["query"]["sessionId"], second.stem)


class RecallBackendTests(Sandbox):
    def setUp(self) -> None:
        super().setUp()
        self.backend = load(BACKEND_PATH, "recall_backend_under_test")

    def test_reads_the_same_config_file_as_the_hook(self) -> None:
        os.environ.pop("AGENT_SKILLS_MEMORIA_CONFIG")
        self.assertEqual(self.backend.config_path(), self.push.config_path())

    def test_qmd_is_the_default(self) -> None:
        self.assertEqual(self.backend.describe(self.backend.read_config())["backend"], "qmd")
        self.configure(url="https://memoria.example.com")  # push on, search not
        self.assertEqual(self.backend.describe(self.backend.read_config())["backend"], "qmd")
        with mock.patch.object(self.backend.subprocess, "run") as run:
            self.assertEqual(self.backend.main(["query", "anything"]), 2)
        run.assert_not_called()

    def test_memoria_query_goes_through_the_cli(self) -> None:
        self.configure(search="memoria", profile="desk", url="https://memoria.example.com",
                       cli="/opt/bin/memoria", collections={"codex": "mac-codex"})
        with mock.patch.object(self.backend.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            self.assertEqual(self.backend.main(["query", "-weird query", "--intent", "why", "--limit", "5",
                                                "--project", "Receipts"]), 0)
        command = run.call_args.args[0]
        self.assertEqual(command[:5], ["/opt/bin/memoria", "--profile", "desk", "--api-url",
                                       "https://memoria.example.com"])
        self.assertEqual(command[-2:], ["--", "-weird query"])
        self.assertIn("claude-sessions", command)
        self.assertIn("mac-codex", command)
        self.assertNotIn(KEY, " ".join(command))
        joined = " ".join(command)
        self.assertIn("--intent why", joined)
        self.assertIn("--limit 5", joined)
        self.assertIn("--project Receipts", joined)

    def test_one_harness(self) -> None:
        self.configure(search="memoria", cli="memoria")
        with mock.patch.object(self.backend.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            self.backend.main(["query", "x", "--harness", "codex"])
        command = run.call_args.args[0]
        self.assertIn("codex-sessions", command)
        self.assertNotIn("claude-sessions", command)


if __name__ == "__main__":
    unittest.main()
