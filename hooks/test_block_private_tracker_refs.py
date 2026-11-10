"""Tests for block-private-tracker-refs.py.

Run: python3 -m unittest discover -s hooks -v

Each case runs the hook as a subprocess with a JSON payload on stdin, exactly
as Claude Code does, against a placeholder config (no real tracker values
live in this repo). Git cases use throwaway repositories with and without a
remote. Tracker phrases are assembled at runtime so this file never contains
one literally, which keeps the hook from flagging its own tests on push.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "block-private-tracker-refs.py"
REMOTE = "https://github.com/example/project.git"
HOST = "tracker.example.invalid"
PHRASE = " ".join(["Plane", "issue"])  # a tracker phrase, built so it isn't literal here


class PrivateTrackerRefsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.config = os.path.join(root, "private-tracker.json")
        Path(self.config).write_text(
            json.dumps({"hosts": [HOST], "project_keys": ["ACME", "OPS"], "own_namespaces": ["me"]}),
            encoding="utf-8",
        )
        self.env = {**os.environ, "PRIVATE_TRACKER_CONFIG": self.config}
        self.remote = os.path.join(root, "remote")
        self.local_only = os.path.join(root, "local")
        for path, url in ((self.remote, REMOTE), (self.local_only, None)):
            os.makedirs(path)
            self.git(path, "init", "-q")
            if url:
                self.git(path, "remote", "add", "origin", url)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, cwd: str, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=cwd, check=True, capture_output=True, text=True,
        ).stdout.strip()

    def run_hook(self, payload, env=None) -> subprocess.CompletedProcess:
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            [sys.executable, str(HOOK)], input=raw, text=True, capture_output=True,
            timeout=20, check=False, env=env or self.env,
        )

    def shell(self, command: str, cwd: str, tool: str = "Bash", env=None):
        return self.run_hook({"tool_name": tool, "tool_input": {"command": command}, "cwd": cwd}, env)

    def commit(self, repo: str, message: str) -> str:
        Path(repo, "f.txt").write_text(message, encoding="utf-8")
        self.git(repo, "add", "f.txt")
        self.git(repo, "commit", "-q", "-m", message)
        return self.git(repo, "rev-parse", "HEAD")

    def assertAllowed(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def assertDenied(self, result: subprocess.CompletedProcess) -> str:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout, "expected a deny decision, got allow")
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        return output["permissionDecisionReason"]

    # git

    def test_commit_message_with_work_item_denied(self) -> None:
        reason = self.assertDenied(self.shell('git commit -m "Fix crash (ACME-1)"', self.remote))
        self.assertIn("ACME-1", reason)

    def own_repo(self) -> str:
        own = os.path.join(self._tmp.name, "own")
        os.makedirs(own)
        self.git(own, "init", "-q")
        self.git(own, "remote", "add", "origin", "https://github.com/me/agent-skills.git")
        return own

    def test_ids_blocked_in_own_repos_too(self) -> None:
        self.assertDenied(self.shell('git commit -m "feat: add guard (OPS-8)"', self.own_repo()))

    def test_host_blocked_in_own_repos_too(self) -> None:
        self.assertDenied(self.shell(f'git commit -m "docs: link https://{HOST}/x"', self.own_repo()))

    def test_tracker_phrase_allowed_in_own_repos(self) -> None:
        own = self.own_repo()
        self.assertAllowed(self.shell(f'git commit -m "docs: refresh the {PHRASE} guide"', own))
        self.commit(own, f"docs: refresh the {PHRASE} guide")
        self.assertAllowed(self.shell("git push origin HEAD", own))

    def test_tracker_phrase_denied_in_external_repo(self) -> None:
        self.assertDenied(self.shell(f'git commit -m "tracked as a {PHRASE}"', self.remote))

    def test_commit_message_file_with_tracker_host_denied(self) -> None:
        Path(self.remote, "msg.txt").write_text(f"see https://{HOST}/x\n", encoding="utf-8")
        self.assertDenied(self.shell("git commit -F msg.txt", self.remote))

    def test_git_dash_c_targets_other_repo(self) -> None:
        self.assertDenied(self.shell(f'git -C "{self.remote}" commit -m "OPS-3"', self.local_only))

    def test_clean_commit_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "Check setByteArray result"', self.remote))

    def test_color_plane_wording_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "Store the colormap plane lengths"', self.remote))

    def test_unknown_key_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "Fix CVE-2026-1234"', self.remote))

    def test_repo_without_remote_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "ACME-1 notes"', self.local_only))

    def test_push_of_unpushed_commit_with_work_item_denied(self) -> None:
        self.commit(self.remote, "Fix crash, tracked in ACME-2")
        reason = self.assertDenied(self.shell("git push origin HEAD", self.remote))
        self.assertIn("push", reason)

    def test_push_of_clean_commits_allowed(self) -> None:
        self.commit(self.remote, "Fix crash in TIFFReadDirectory")
        self.assertAllowed(self.shell("git push origin HEAD", self.remote))

    def test_powershell_tool_checked_too(self) -> None:
        self.assertDenied(self.shell(f'git commit -m "per {PHRASE} 4"', self.remote, tool="PowerShell"))

    # gh / glab

    def test_gh_comment_denied(self) -> None:
        self.assertDenied(
            self.shell('gh issue comment 5 --repo other/project --body "see ACME-1"', self.local_only)
        )

    def test_gh_id_on_own_repo_denied(self) -> None:
        self.assertDenied(self.shell('gh pr create --repo me/agent-skills --body "OPS-8"', self.local_only))

    def test_gh_phrase_on_own_repo_allowed(self) -> None:
        command = f'gh pr create --repo me/agent-skills --body "Update the {PHRASE} reference"'
        self.assertAllowed(self.shell(command, self.local_only))

    def test_gh_phrase_on_other_repo_denied(self) -> None:
        command = f'gh issue comment 5 --repo other/project --body "per our {PHRASE}"'
        self.assertDenied(self.shell(command, self.local_only))

    def test_clean_gh_allowed(self) -> None:
        self.assertAllowed(
            self.shell('gh pr create --title "fix: guard" --body "see https://example.com"', self.remote)
        )

    def test_glab_denied(self) -> None:
        self.assertDenied(self.shell(f'glab mr create --description "{PHRASE} 3"', self.remote))

    # HTTP

    def test_post_to_external_host_denied(self) -> None:
        self.assertDenied(self.shell(
            'curl -X POST https://gitlab.com/api/v4/projects/1/issues -d "title=ACME-1"', self.local_only
        ))

    def test_request_to_tracker_host_allowed(self) -> None:
        self.assertAllowed(self.shell(f"curl https://{HOST}/api/v1/projects/ -d ACME-1", self.local_only))

    def test_data_file_reference_checked(self) -> None:
        Path(self.local_only, "body.json").write_text('{"body": "OPS-9"}', encoding="utf-8")
        self.assertDenied(self.shell("curl -X POST https://example.com/hook -d @body.json", self.local_only))

    # browser and email

    def test_browser_form_input_denied(self) -> None:
        self.assertDenied(self.run_hook({
            "tool_name": "mcp__Claude_Browser__form_input",
            "tool_input": {"ref": "ref_1", "value": "Tracked as ACME-1"},
        }))

    def test_chrome_batch_typing_denied(self) -> None:
        self.assertDenied(self.run_hook({
            "tool_name": "mcp__claude-in-chrome__browser_batch",
            "tool_input": {"actions": [{"name": "computer", "input": {"action": "type", "text": HOST}}]},
        }))

    def test_clean_browser_text_allowed(self) -> None:
        self.assertAllowed(self.run_hook({
            "tool_name": "mcp__Claude_Browser__form_input",
            "tool_input": {"ref": "ref_1", "value": "Three more cases of the same pattern"},
        }))

    def test_email_send_denied(self) -> None:
        self.assertDenied(self.run_hook({
            "tool_name": "mcp__mail__send_message",
            "tool_input": {"to": "x@example.com", "body": f"Details at https://{HOST}/p/1"},
        }))

    # scope, config and failure

    def test_unrelated_tools_ignored(self) -> None:
        self.assertAllowed(self.run_hook({"tool_name": "Write", "tool_input": {"content": "ACME-1"}}))

    def test_tracker_cli_itself_allowed(self) -> None:
        command = f'{PHRASE.lower()} create -p ACME --name "ACME-2 follow-up"'
        self.assertAllowed(self.shell(command, self.remote))

    def test_missing_config_denies_outward_calls_only(self) -> None:
        env = {**os.environ, "PRIVATE_TRACKER_CONFIG": os.path.join(self._tmp.name, "nope.json")}
        reason = self.assertDenied(self.shell('git commit -m "anything"', self.remote, env=env))
        self.assertIn("config", reason)
        self.assertAllowed(self.shell("git status", self.remote, env=env))
        self.assertAllowed(self.shell('git commit -m "anything"', self.local_only, env=env))

    def test_invalid_config_treated_as_missing(self) -> None:
        Path(self.config).write_text('{"hosts": []}', encoding="utf-8")
        self.assertDenied(self.shell('gh pr list', self.remote))

    def test_malformed_payload_fails_closed(self) -> None:
        result = self.run_hook("{not json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("failing closed", result.stderr)

    # git hook modes

    def git_hook(self, *args: str, stdin: str = "", cwd: str = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(HOOK), *args], input=stdin, text=True,
            capture_output=True, timeout=20, check=False, cwd=cwd, env=self.env,
        )

    def test_commit_msg_mode(self) -> None:
        bad = Path(self.remote, "bad.txt")
        bad.write_text("Fix (OPS-4)\n", encoding="utf-8")
        good = Path(self.remote, "good.txt")
        good.write_text("Fix NULL read in TIFFRGBAImageBegin\n", encoding="utf-8")
        self.assertEqual(self.git_hook("--scan-file", str(bad)).returncode, 1)
        self.assertEqual(self.git_hook("--scan-file", str(good)).returncode, 0)

    def test_pre_push_mode(self) -> None:
        head = self.commit(self.remote, "clean change")
        line = f"refs/heads/main {head} refs/heads/main {'0' * 40}\n"
        self.assertEqual(self.git_hook("--git-pre-push", stdin=line, cwd=self.remote).returncode, 0)
        head = self.commit(self.remote, f"see {HOST} for context")
        line = f"refs/heads/main {head} refs/heads/main {'0' * 40}\n"
        result = self.git_hook("--git-pre-push", stdin=line, cwd=self.remote)
        self.assertEqual(result.returncode, 1)
        self.assertIn("private", result.stderr)


if __name__ == "__main__":
    unittest.main()
