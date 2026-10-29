from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent


def run_hook(name: str, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


class DestructiveGuardTests(unittest.TestCase):
    def payload(self, command: str, tool: str = "Bash") -> dict:
        return {"cwd": tempfile.gettempdir(), "tool_name": tool, "tool_input": {"command": command}}

    def test_allows_safe_command(self) -> None:
        result = run_hook("block-destructive-ops.py", self.payload("git status --short"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_blocks_hard_reset(self) -> None:
        result = run_hook("block-destructive-ops.py", self.payload("git reset --hard"))
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_blocks_broad_delete(self) -> None:
        result = run_hook("block-destructive-ops.py", self.payload("rm -rf /"))
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_blocks_codex_guardrail_patch(self) -> None:
        patch = "*** Begin Patch\n*** Update File: ~/.codex/config.toml\n@@\n-a=1\n+a=2\n*** End Patch"
        payload = self.payload(patch, "apply_patch")
        payload["permission_mode"] = "bypassPermissions"
        result = run_hook("block-destructive-ops.py", payload)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_allows_authorized_project_guidance_patch(self) -> None:
        patch = "*** Begin Patch\n*** Update File: AGENTS.md\n@@\n-old\n+new\n*** End Patch"
        result = run_hook("block-destructive-ops.py", self.payload(patch, "apply_patch"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_malformed_payload_fails_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOKS / "block-destructive-ops.py")],
            input="not json",
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("failing closed", result.stderr)


class WorktreeGuardTests(unittest.TestCase):
    def test_non_repository_allows_patch(self) -> None:
        payload = {
            "cwd": tempfile.gettempdir(),
            "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Add File: safe.txt\n+x\n*** End Patch"},
        }
        result = run_hook("enforce-worktree-paths.py", payload)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_blocks_patch_to_primary_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            primary = Path(directory) / "primary"
            worktree = Path(directory) / "worktree"
            primary.mkdir()
            subprocess.run(["git", "init", "-q", str(primary)], check=True)
            subprocess.run(["git", "-C", str(primary), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(primary), "config", "user.name", "Hook Test"], check=True)
            (primary / "tracked.txt").write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(primary), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(primary), "commit", "-qm", "initial"], check=True)
            subprocess.run(["git", "-C", str(primary), "worktree", "add", "-q", "--detach", str(worktree)], check=True)

            payload = {
                "cwd": str(worktree),
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": f"*** Begin Patch\n*** Update File: {primary / 'tracked.txt'}\n@@\n-original\n+changed\n*** End Patch"
                },
            }
            result = run_hook("enforce-worktree-paths.py", payload)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
