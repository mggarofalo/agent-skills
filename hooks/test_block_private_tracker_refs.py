"""Tests for block-private-tracker-refs.py.

Run: python3 -m unittest discover -s hooks -v

Each case runs the hook as a subprocess with a JSON payload on stdin, exactly
as Claude Code does. Git cases use throwaway repositories whose remotes are
either external (gitlab.com/libtiff) or owned by mggarofalo.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "block-private-tracker-refs.py"
EXTERNAL_REMOTE = "https://gitlab.com/libtiff/libtiff.git"
OWN_REMOTE = "https://github.com/mggarofalo/agent-skills.git"


def run_hook(payload) -> subprocess.CompletedProcess:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def git(cwd: str, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd, check=True, capture_output=True,
    )


class PrivateTrackerRefsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.external = os.path.join(root, "external")
        self.own = os.path.join(root, "own")
        self.local_only = os.path.join(root, "local")
        for path, remote in (
            (self.external, EXTERNAL_REMOTE),
            (self.own, OWN_REMOTE),
            (self.local_only, None),
        ):
            os.makedirs(path)
            git(path, "init", "-q")
            if remote:
                git(path, "remote", "add", "origin", remote)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def shell(self, command: str, cwd: str, tool: str = "Bash") -> subprocess.CompletedProcess:
        return run_hook({"tool_name": tool, "tool_input": {"command": command}, "cwd": cwd})

    def commit(self, repo: str, message: str) -> None:
        Path(repo, "f.txt").write_text(message, encoding="utf-8")
        git(repo, "add", "f.txt")
        git(repo, "commit", "-q", "-m", message)

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

    def test_commit_message_with_work_item_in_external_repo_denied(self) -> None:
        reason = self.assertDenied(self.shell('git commit -m "Fix crash (SECRES-1)"', self.external))
        self.assertIn("SECRES-1", reason)

    def test_commit_message_file_with_plane_host_denied(self) -> None:
        Path(self.external, "msg.txt").write_text(
            "see https://plane.wallingford.me/dev/x\n", encoding="utf-8"
        )
        self.assertDenied(self.shell("git commit -F msg.txt", self.external))

    def test_git_dash_c_targets_external_repo(self) -> None:
        self.assertDenied(self.shell(f'git -C "{self.external}" commit -m "MARVEL-3"', self.own))

    def test_clean_commit_in_external_repo_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "Check setByteArray result"', self.external))

    def test_color_plane_wording_allowed(self) -> None:
        self.assertAllowed(
            self.shell('git commit -m "Store the colormap plane lengths"', self.external)
        )

    def test_work_item_in_own_repo_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "feat: add guard (SKILLS-8)"', self.own))

    def test_repo_without_remote_allowed(self) -> None:
        self.assertAllowed(self.shell('git commit -m "SECRES-1 notes"', self.local_only))

    def test_push_of_unpushed_commit_with_work_item_denied(self) -> None:
        self.commit(self.external, "Fix crash, tracked in SECRES-2")
        reason = self.assertDenied(self.shell("git push origin HEAD", self.external))
        self.assertIn("push", reason)

    def test_push_of_clean_commits_allowed(self) -> None:
        self.commit(self.external, "Fix crash in TIFFReadDirectory")
        self.assertAllowed(self.shell("git push origin HEAD", self.external))

    def test_powershell_tool_checked_too(self) -> None:
        self.assertDenied(
            self.shell('git commit -m "per Plane issue 4"', self.external, tool="PowerShell")
        )

    # gh / glab

    def test_gh_comment_on_external_repo_denied(self) -> None:
        self.assertDenied(
            self.shell('gh issue comment 5 --repo libtiff/libtiff --body "see SECRES-1"', self.own)
        )

    def test_gh_on_own_repo_allowed(self) -> None:
        self.assertAllowed(
            self.shell('gh pr create --repo mggarofalo/agent-skills --body "SKILLS-8"', self.external)
        )

    def test_glab_in_external_checkout_denied(self) -> None:
        self.assertDenied(self.shell('glab mr create --description "Plane work item 3"', self.external))

    # HTTP

    def test_post_to_external_host_denied(self) -> None:
        self.assertDenied(
            self.shell(
                'curl -X POST https://gitlab.com/api/v4/projects/1/issues -d "title=SECRES-1"',
                self.local_only,
            )
        )

    def test_request_to_plane_host_allowed(self) -> None:
        self.assertAllowed(
            self.shell(
                "curl https://plane.wallingford.me/api/v1/workspaces/dev/projects/ -d SECRES-1",
                self.local_only,
            )
        )

    def test_data_file_reference_checked(self) -> None:
        Path(self.local_only, "body.json").write_text('{"body": "SECRES-9"}', encoding="utf-8")
        self.assertDenied(
            self.shell("curl -X POST https://example.com/hook -d @body.json", self.local_only)
        )

    # browser and email

    def test_browser_form_input_denied(self) -> None:
        result = run_hook({
            "tool_name": "mcp__Claude_Browser__form_input",
            "tool_input": {"ref": "ref_1", "value": "Tracked as SECRES-1"},
        })
        self.assertDenied(result)

    def test_chrome_batch_typing_denied(self) -> None:
        result = run_hook({
            "tool_name": "mcp__claude-in-chrome__browser_batch",
            "tool_input": {"actions": [
                {"name": "computer", "input": {"action": "type", "text": "plane.wallingford.me"}}
            ]},
        })
        self.assertDenied(result)

    def test_clean_browser_text_allowed(self) -> None:
        result = run_hook({
            "tool_name": "mcp__Claude_Browser__form_input",
            "tool_input": {"ref": "ref_1", "value": "Three more cases of the same pattern"},
        })
        self.assertAllowed(result)

    def test_email_send_denied(self) -> None:
        result = run_hook({
            "tool_name": "mcp__9b6120c5__send_message",
            "tool_input": {"to": "x@example.com", "body": "Details in plane project SECRES"},
        })
        self.assertDenied(result)

    # scope and failure

    def test_unrelated_tools_ignored(self) -> None:
        result = run_hook({"tool_name": "Write", "tool_input": {"content": "SECRES-1"}})
        self.assertAllowed(result)

    def test_plane_cli_itself_allowed(self) -> None:
        self.assertAllowed(
            self.shell('plane issue create -p SECRES --name "SECRES-2 follow-up"', self.external)
        )

    # git hook modes

    def git_hook(self, *args: str, stdin: str = "", cwd: str = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(HOOK), *args], input=stdin, text=True,
            capture_output=True, timeout=20, check=False, cwd=cwd,
        )

    def test_commit_msg_mode(self) -> None:
        bad = Path(self.external, "bad.txt")
        bad.write_text("Fix (SECRES-4)\n", encoding="utf-8")
        good = Path(self.external, "good.txt")
        good.write_text("Fix NULL read in TIFFRGBAImageBegin\n", encoding="utf-8")
        self.assertEqual(self.git_hook("--scan-file", str(bad)).returncode, 1)
        self.assertEqual(self.git_hook("--scan-file", str(good)).returncode, 0)

    def test_pre_push_mode(self) -> None:
        self.commit(self.external, "clean change")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.external, capture_output=True, text=True
        ).stdout.strip()
        line = f"refs/heads/main {head} refs/heads/main {'0' * 40}\n"
        self.assertEqual(self.git_hook("--git-pre-push", stdin=line, cwd=self.external).returncode, 0)
        self.commit(self.external, "see plane.wallingford.me for context")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.external, capture_output=True, text=True
        ).stdout.strip()
        line = f"refs/heads/main {head} refs/heads/main {'0' * 40}\n"
        result = self.git_hook("--git-pre-push", stdin=line, cwd=self.external)
        self.assertEqual(result.returncode, 1)
        self.assertIn("private", result.stderr)

    def test_malformed_payload_fails_closed(self) -> None:
        result = run_hook("{not json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("failing closed", result.stderr)


if __name__ == "__main__":
    unittest.main()
