"""Claude Code PreToolUse hook: blocks destructive operations.

Catches high-consequence commands that are hard or impossible to reverse.
Designed to be the safety net when running with --dangerously-skip-permissions.

Git operations blocked (Bash):
  - git reset --hard (destroys uncommitted changes)
  - git push --force to main/master (rewrites shared history)
  - git clean -f (permanently deletes untracked files)
  - git checkout -- . / git restore . (discards all unstaged changes)

Filesystem operations blocked (Bash):
  - rm -rf with broad targets: . .. ~ / /* * (catastrophic data loss)

Network operations blocked (Bash):
  - curl/wget piped to shell (arbitrary code execution)
  - curl -d @file / curl --data @file (data exfiltration)

Sensitive file protection (Read, Write, Edit):
  - ~/.ssh/**, ~/.aws/**, ~/.gnupg/**, ~/.config/gh/** (auth dirs)
  - ~/.netrc
  - .env, .env.* (except .env.example, .env.template, .env.sample)
  - *.pem, *.key, *.pfx, *.p12 (except Read under node_modules/)
  - .npmrc, .pypirc (package manager auth)
  - id_rsa*, id_ed25519*, id_ecdsa* (SSH keys)
  - credentials.json, service-account*.json (cloud credentials)

Self-modification protection (Write, Edit):
  - ~/.claude/hooks/** (could disable this very hook)
  - ~/.claude/settings.json, ~/.claude/settings.local.json
  - **/CLAUDE.md (could rewrite safety instructions)

Allowed (legitimate workflow):
  - --force-with-lease on any branch
  - git branch -D (low-risk post-merge cleanup)
  - git reset --soft / --mixed (non-destructive)
  - git push --force to feature branches
  - rm -rf with specific paths (node_modules, dist, build, etc.)
  - curl/wget without pipe to shell or file upload
  - .env.example, .env.template, .env.sample (scaffold files)
  - Read of *.pem / *.key under node_modules/ (bundled test fixtures)
  - Read of CLAUDE.md, settings.json, hooks/ (Claude needs context)
"""

import json
import os
import re
import sys


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


# --- Path normalization ---

# Resolve ~ once at import time
HOME = os.path.realpath(os.path.expanduser("~")).replace("\\", "/")

# MSYS /c/Users/... -> C:/Users/... conversion
_MSYS_DRIVE = re.compile(r"^/([a-zA-Z])/")


def resolve_path(path: str) -> str:
    """Canonicalize a file path for consistent matching.

    Converts MSYS paths to Windows format, resolves symlinks and ../
    traversal, and normalizes to forward slashes.
    """
    m = _MSYS_DRIVE.match(path)
    if m:
        path = f"{m.group(1).upper()}:/{path[3:]}"
    resolved = os.path.realpath(path)
    return resolved.replace("\\", "/")


# --- Sensitive file protection ---


def _resolve_anchor(subpath: str) -> str:
    """Resolve a ~-relative path through realpath for symlink consistency."""
    return os.path.realpath(
        os.path.join(os.path.expanduser("~"), subpath)
    ).replace("\\", "/")


# Home-directory sensitive directories (absolute, symlink-resolved)
SENSITIVE_DIRS = [
    _resolve_anchor(".ssh"),
    _resolve_anchor(".aws"),
    _resolve_anchor(".gnupg"),
    _resolve_anchor(os.path.join(".config", "gh")),
]

# Home-directory sensitive files (absolute, symlink-resolved)
SENSITIVE_HOME_FILES = [
    _resolve_anchor(".netrc"),
]

# Pattern-based sensitive file checks (regex on resolved forward-slash path)
SENSITIVE_PATH_PATTERNS = [
    # .env files — negative lookahead excludes .env.example/template/sample
    re.compile(r"(?:^|/)\.env(?:\.(?!example$|template$|sample$)\S+)?$"),
    # Crypto keys / certificates
    re.compile(r"\.(?:pem|key|pfx|p12)$", re.I),
    # Package manager auth
    re.compile(r"(?:^|/)\.npmrc$"),
    re.compile(r"(?:^|/)\.pypirc$"),
    # SSH keys outside ~/.ssh/ (the dir check handles those inside)
    re.compile(r"(?:^|/)id_(?:rsa|ed25519|ecdsa)"),
    # Cloud provider credentials
    re.compile(r"(?:^|/)credentials\.json$"),
    re.compile(r"(?:^|/)service-account.*\.json$", re.I),
]


def _starts_with_dir(path: str, directory: str) -> bool:
    """Check if path is inside directory (or is the directory itself)."""
    return path == directory or path.startswith(directory + "/")


def is_sensitive_path(path: str, tool_name: str) -> bool:
    """Check if a resolved, normalized path targets a sensitive file.

    Returns False for explicitly allowed exceptions.
    """
    # Home-directory sensitive dirs
    for d in SENSITIVE_DIRS:
        if _starts_with_dir(path, d):
            return True

    # Home-directory sensitive files
    if path in SENSITIVE_HOME_FILES:
        return True

    # Pattern-based checks
    for pattern in SENSITIVE_PATH_PATTERNS:
        if pattern.search(path):
            # Exception: Read of *.pem / *.key under node_modules/
            if (
                tool_name == "Read"
                and "/node_modules/" in path
                and re.search(r"\.(?:pem|key)$", path, re.I)
            ):
                return False
            return True

    return False


# --- Self-modification protection ---

SELF_MOD_DIR = _resolve_anchor(os.path.join(".claude", "hooks"))
SELF_MOD_FILES = [
    _resolve_anchor(os.path.join(".claude", "settings.json")),
    _resolve_anchor(os.path.join(".claude", "settings.local.json")),
]
CLAUDE_MD = re.compile(r"(?:^|/)CLAUDE\.md$")


def is_self_modification(path: str) -> bool:
    """Check if a resolved, normalized path targets Claude Code config."""
    if _starts_with_dir(path, SELF_MOD_DIR):
        return True
    if path in SELF_MOD_FILES:
        return True
    if CLAUDE_MD.search(path):
        return True
    return False


# --- Bash command patterns ---


def strip_quoted_content(command: str) -> str:
    """Remove content inside quotes and heredocs to avoid false positives."""
    # Remove heredoc content (<<'EOF'...EOF, <<"EOF"...EOF, <<EOF...EOF)
    result = re.sub(
        r"<<-?\s*['\"]?(\w+)['\"]?\s*\n.*?\n\s*\1",
        "",
        command,
        flags=re.DOTALL,
    )
    # Remove double-quoted strings (handling escaped quotes)
    result = re.sub(r'"(?:[^"\\]|\\.)*"', '""', result)
    # Remove single-quoted strings
    result = re.sub(r"'[^']*'", "''", result)
    return result


# Git patterns
RESET_HARD = re.compile(r"git\s+reset\s+--hard")
CLEAN_FORCE = re.compile(r"git\s+clean\s+(?:.*\s)?-[a-z]*f")
DISCARD_ALL = re.compile(r"git\s+(?:checkout\s+--\s+\.|restore\s+\.)")

# Network patterns
PIPE_TO_SHELL = re.compile(r"(?:curl|wget)\s+.*\|\s*(?:ba)?sh\b")
CURL_EXFIL = re.compile(r"curl\s+.*(?:-d\s*@|--data(?:-\w+)?\s+@)")


def is_force_push_to_main(command: str) -> bool:
    """Check if command is a force push to main/master."""
    if not re.search(r"git\s+push\b", command):
        return False
    # --force-with-lease is safe — allow it
    if re.search(r"--force-with-lease", command):
        return False
    # Must have --force or -f
    if not re.search(r"(?:--force\b|-f\b)", command):
        return False
    # Must target main or master
    if not re.search(r"\b(?:main|master)\b", command):
        return False
    return True


def is_dangerous_rm(command: str) -> bool:
    """Check if rm -rf targets a dangerously broad path."""
    if not re.search(r"\brm\b", command):
        return False
    # Must have recursive flag (-r, -R, or --recursive, possibly combined like -rf)
    if not re.search(r"-[a-zA-Z]*[rR]|--recursive", command):
        return False
    # Must have force flag (-f or --force, possibly combined like -rf)
    if not re.search(r"-[a-zA-Z]*f|--force", command):
        return False
    # Check for dangerous broad targets
    for pattern in [
        r"(?:^|\s)\./?(?:\s|$)",      # . or ./
        r"(?:^|\s)\.\./?(?:\s|$)",     # .. or ../
        r"(?:^|\s)~/?(?:\s|$)",        # ~ or ~/
        r"(?:^|\s)/(?:\s|$|\*)",       # / or /*
        r"(?:^|\s)\*(?:\s|$)",         # bare *
    ]:
        if re.search(pattern, command):
            return True
    return False


# --- Dispatch ---


def main() -> None:
    payload = json.loads(sys.stdin.read())
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    # --- File tool checks: Read, Write, Edit ---

    if tool_name in ("Read", "Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if not file_path:
            sys.exit(0)

        resolved = resolve_path(file_path)

        # Sensitive file check (all three tools)
        if is_sensitive_path(resolved, tool_name):
            deny(
                f"BLOCKED: `{tool_name}` on `{os.path.basename(file_path)}` "
                "— this is a credential or secret file. Access sensitive "
                "files manually outside Claude Code to avoid accidental "
                "exposure."
            )

        # Self-modification check (Write and Edit only)
        if tool_name in ("Write", "Edit") and is_self_modification(resolved):
            deny(
                f"BLOCKED: `{tool_name}` on `{file_path}` — this is a "
                "Claude Code configuration or hook file. Self-modification "
                "of guardrails is blocked to prevent prompt injection from "
                "disabling safety checks. Edit this file manually if "
                "changes are needed."
            )

        sys.exit(0)

    # --- Bash tool checks ---

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command.strip():
        sys.exit(0)

    # Strip quoted content so patterns inside strings/heredocs don't trigger
    stripped = strip_quoted_content(command)

    # Git checks
    if RESET_HARD.search(stripped):
        deny(
            "BLOCKED: `git reset --hard` destroys uncommitted changes "
            "irreversibly. Use `git stash` or `git reset --soft` instead, "
            "or confirm intent explicitly."
        )

    if is_force_push_to_main(stripped):
        deny(
            "BLOCKED: `git push --force` to main/master rewrites shared "
            "history on the default branch. Use `--force-with-lease` on a "
            "feature branch and merge via PR."
        )

    if CLEAN_FORCE.search(stripped):
        deny(
            "BLOCKED: `git clean -f` permanently deletes untracked files. "
            "List them with `git clean -dn` first."
        )

    if DISCARD_ALL.search(stripped):
        deny(
            "BLOCKED: `git checkout -- .` / `git restore .` discards all "
            "unstaged changes in the working tree."
        )

    # Filesystem checks
    if is_dangerous_rm(stripped):
        deny(
            "BLOCKED: `rm -rf` targets a dangerously broad path "
            "(., .., ~, /, *). This would cause catastrophic data loss. "
            "Use a more specific path, or delete files individually."
        )

    # Network checks
    if PIPE_TO_SHELL.search(stripped):
        deny(
            "BLOCKED: piping curl/wget output to a shell executes arbitrary "
            "code. Download the script first, review it, then run it "
            "explicitly."
        )

    if CURL_EXFIL.search(stripped):
        deny(
            "BLOCKED: `curl -d @file` / `curl --data @file` can exfiltrate "
            "sensitive files to a remote server. Download the file "
            "explicitly first and review what you're sending."
        )

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    main()
