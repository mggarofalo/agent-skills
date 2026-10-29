"""Claude Code PreToolUse hook: blocks destructive operations.

Catches high-consequence commands that are hard or impossible to reverse.
Designed to be the safety net when running with --dangerously-skip-permissions.

Git operations blocked (Bash):
  - git reset --hard (destroys uncommitted changes)
  - git push --force to main/master (rewrites shared history)
  - git clean -f (permanently deletes untracked files)
  - git checkout -- . / git restore . (discards all unstaged changes)

Filesystem operations blocked (Bash):
  - rm -rf with broad targets: . .. ~ $HOME / /* * (catastrophic data loss)
    Flags and targets are read per command segment (split on ; & | and
    newlines), so `rm -r foo; ls -f .` is not mistaken for `rm -rf .`.

Network operations blocked (Bash):
  - curl/wget piped to shell (arbitrary code execution)
  - curl -d @file / curl --data @file (data exfiltration)

Shell wrapper handling (Bash):
  - bash -c / sh -c / zsh -c wrappers: inner command is extracted and
    scanned so that quoting cannot bypass pattern checks
  - heredoc bodies are data, not commands: they are removed before any scan

Sensitive file protection (Bash):
  - any path-like word in the command (after shell unquoting, ~ and $VAR
    expansion, resolved against the payload's cwd) that hits the sensitive
    file rules below — e.g. `cat ~/.ssh/id_rsa`, `cat .env`

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
import shlex
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


def fail_closed(reason: str) -> None:
    """Deny because the guard could not reach a decision at all.

    Exit code 2 is used rather than the JSON protocol above. Both Claude Code
    and Codex treat exit 2 (with a reason on stderr) as a block, and it is the
    only signal that still works when stdout is unusable or the payload never
    parsed. Every other exit status — including 1 — is treated by both hosts as
    "hook failed", which permits the operation.
    """
    sys.stderr.write(f"BLOCKED (guard error, failing closed): {reason}\n")
    sys.exit(2)


# --- Path normalization ---

# Resolve ~ once at import time
HOME = os.path.realpath(os.path.expanduser("~")).replace("\\", "/")

# MSYS /c/Users/... -> C:/Users/... conversion
_MSYS_DRIVE = re.compile(r"^/([a-zA-Z])/")


def resolve_path(path: str, cwd: str) -> str:
    """Canonicalize a file path for consistent matching.

    Expands ~ and $VARS, converts MSYS paths to Windows format, anchors
    relative paths at cwd, resolves symlinks and ../ traversal, and
    normalizes to forward slashes.
    """
    path = os.path.expandvars(os.path.expanduser(path))
    m = _MSYS_DRIVE.match(path)
    if m:
        path = f"{m.group(1).upper()}:/{path[3:]}"
    resolved = os.path.realpath(os.path.join(cwd, path))
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


# Heredoc (<<EOF, <<-EOF, <<'EOF', <<"EOF"; not the <<< herestring). Group 1
# is the operator, group 4 the rest of its line (e.g. `> file` or `| sh`),
# which is kept; only the body and terminator line are removed.
HEREDOC = re.compile(
    r"(?<!<)(<<-?[ \t]*(['\"]?)(\w+)\2)([^\n]*)\n(?:.*?\n)??[ \t]*\3[ \t]*(?=\n|$)",
    re.DOTALL,
)


def strip_heredocs(command: str) -> str:
    """Remove heredoc bodies, which are data rather than commands."""
    return HEREDOC.sub(r"\1\4", command)


def strip_quoted_content(command: str) -> str:
    """Remove content inside quotes and heredocs to avoid false positives."""
    result = strip_heredocs(command)
    # Remove double-quoted strings (handling escaped quotes)
    result = re.sub(r'"(?:[^"\\]|\\.)*"', '""', result)
    # Remove single-quoted strings
    result = re.sub(r"'[^']*'", "''", result)
    return result


# Separators between simple commands. Applied to quote-stripped text, so a
# separator inside a quoted argument is already gone.
SEGMENT_SPLIT = re.compile(r"[;&|\n]")


def command_segments(stripped: str) -> list:
    """Split a quote-stripped command into its simple commands."""
    return [s for s in SEGMENT_SPLIT.split(stripped) if s.strip()]


# Git patterns (matched per segment)
RESET_HARD = re.compile(r"\bgit\s+reset\s+(?:\S+\s+)*--hard\b")
CLEAN_FORCE = re.compile(r"\bgit\s+clean\s+(?:\S+\s+)*(?:-[A-Za-z]*f|--force\b)")
DISCARD_ALL = re.compile(
    r"\bgit\s+(?:checkout\s+--\s+|restore\s+)\./?(?:\s|$)"
)

# Network patterns. PIPE_TO_SHELL spans segments (the pipe is the point),
# so it runs on the whole line; `.*` still catches `curl x | tee f | sh`.
PIPE_TO_SHELL = re.compile(r"\b(?:curl|wget)\s+.*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b")
CURL_EXFIL = re.compile(r"\bcurl\s+.*(?:-d\s*@|--data(?:-\w+)?\s+@)")

# bash -c / sh -c / zsh -c (incl. -lc etc.) wrapper — extract inner command for scanning
SHELL_DASH_C = re.compile(
    r"""\b(?:ba|z)?sh\s+(?:-\S+\s+)*-[A-Za-z]*c\s+(?:'([^']*)'|"((?:[^"\\]|\\.)*)")"""
)


def extract_inner_commands(command: str) -> list:
    """Extract command strings from bash -c / sh -c wrappers.

    Returns the inner command text from each bash -c / sh -c invocation
    found in the command, so they can be scanned independently.
    """
    result = []
    for m in SHELL_DASH_C.finditer(command):
        # Group 1 = single-quoted content, group 2 = double-quoted content
        cmd = m.group(1) if m.group(1) is not None else m.group(2)
        if cmd and cmd.strip():
            result.append(cmd)
    return result


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


BROAD_RM_TARGETS = {".", "..", "~", "/", "*"}


def _is_broad_target(word: str) -> bool:
    """True for . .. ~ $HOME / * and their `/` or `/*` suffixed forms."""
    word = word.replace("${HOME}", "~").replace("$HOME", "~")
    word = re.sub(r"/\*?$", "", word) or "/"
    return word in BROAD_RM_TARGETS


def is_dangerous_rm(segment: str) -> bool:
    """Check if an rm in this segment is recursive, forced, and broad.

    Only words after `rm` count, so flags belonging to another command in
    the same segment (or a later segment) cannot complete the match.
    """
    # Peel subshell / substitution punctuation: `$(rm`, `(rm`, `/)`
    words = [re.sub(r"^\$?[(`]+|[)`]+$", "", w) for w in segment.split()]
    start = next(
        (i for i, w in enumerate(words) if w == "rm" or w.endswith("/rm")), None
    )
    if start is None:
        return False
    recursive = force = False
    targets = []
    options_done = False
    for word in words[start + 1 :]:
        if not options_done and word == "--":
            options_done = True
        elif not options_done and word.startswith("--"):
            recursive = recursive or word == "--recursive"
            force = force or word == "--force"
        elif not options_done and re.fullmatch(r"-[A-Za-z]+", word):
            recursive = recursive or bool(re.search(r"[rR]", word))
            force = force or "f" in word
        else:
            targets.append(word)
    return recursive and force and any(_is_broad_target(t) for t in targets)


def check_bash_patterns(stripped: str) -> None:
    """Run all destructive-operation checks against a (quote-stripped) command.

    Calls deny() and exits if a dangerous pattern is found.
    """
    for segment in command_segments(stripped):
        check_segment(segment)

    # Network checks that span segments
    if PIPE_TO_SHELL.search(stripped):
        deny(
            "BLOCKED: piping curl/wget output to a shell executes arbitrary "
            "code. Download the script first, review it, then run it "
            "explicitly."
        )


def check_segment(segment: str) -> None:
    """Run the checks whose flags and targets must share one simple command."""
    # Git checks
    if RESET_HARD.search(segment):
        deny(
            "BLOCKED: `git reset --hard` destroys uncommitted changes "
            "irreversibly. Use `git stash` or `git reset --soft` instead, "
            "or confirm intent explicitly."
        )

    if is_force_push_to_main(segment):
        deny(
            "BLOCKED: `git push --force` to main/master rewrites shared "
            "history on the default branch. Use `--force-with-lease` on a "
            "feature branch and merge via PR."
        )

    if CLEAN_FORCE.search(segment):
        deny(
            "BLOCKED: `git clean -f` permanently deletes untracked files. "
            "List them with `git clean -dn` first."
        )

    if DISCARD_ALL.search(segment):
        deny(
            "BLOCKED: `git checkout -- .` / `git restore .` discards all "
            "unstaged changes in the working tree."
        )

    # Filesystem checks
    if is_dangerous_rm(segment):
        deny(
            "BLOCKED: `rm -rf` targets a dangerously broad path "
            "(., .., ~, /, *). This would cause catastrophic data loss. "
            "Use a more specific path, or delete files individually."
        )

    # Network checks
    if CURL_EXFIL.search(segment):
        deny(
            "BLOCKED: `curl -d @file` / `curl --data @file` can exfiltrate "
            "sensitive files to a remote server. Download the file "
            "explicitly first and review what you're sending."
        )


# --- Shell access to sensitive files ---

# Redirection or curl-upload prefix glued to a path: `<.env`, `2>f`, `@file`
_WORD_PREFIX = re.compile(r"^(?:\d*[<>]+&?|@)")
# `--opt=value` or `VAR=value`: the value is the part that may be a path
_ASSIGNMENT = re.compile(r"^(?:-[\w-]*|[A-Za-z_]\w*)=(.*)$")


def shell_words(command: str) -> list:
    """Split a command into shell words without raising.

    Unbalanced quotes make shlex raise; fall back to whitespace splitting
    with quote characters dropped so the scan still runs.
    """
    try:
        return shlex.split(command)
    except ValueError:
        return [w.strip("'\"") for w in command.split()]


def check_shell_paths(command: str, cwd: str) -> None:
    """Deny any path-like word in the command that names a sensitive file."""
    for word in shell_words(strip_heredocs(command)):
        candidate = _WORD_PREFIX.sub("", word.strip(";,()`"))
        assignment = _ASSIGNMENT.match(candidate)
        if assignment:
            candidate = assignment.group(1)
        elif candidate.startswith("-"):
            continue
        if not candidate or "://" in candidate:
            continue
        if not ("/" in candidate or candidate.startswith((".", "~", "$"))):
            continue
        if is_sensitive_path(resolve_path(candidate, cwd), "Bash"):
            deny(
                f"BLOCKED: Bash command touches `{candidate}` — this is a "
                "credential or secret file. Access sensitive files manually "
                "outside Claude Code to avoid accidental exposure."
            )


# --- Dispatch ---


def main() -> None:
    try:
        raw = sys.stdin.read()
    except Exception as exc:  # unreadable stdin — cannot evaluate the call
        fail_closed(f"could not read hook payload: {exc}")

    try:
        payload = json.loads(raw)
    except ValueError as exc:
        fail_closed(f"unparseable hook payload: {exc}")

    if not isinstance(payload, dict):
        fail_closed(f"hook payload was {type(payload).__name__}, expected object")

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if not isinstance(tool_input, dict):
        fail_closed(f"tool_input was {type(tool_input).__name__}, expected object")

    # Relative paths resolve against the session's cwd, not the hook's.
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        cwd = os.getcwd()

    # --- File tool checks: Read, Write, Edit ---

    if tool_name in ("Read", "Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if not file_path:
            sys.exit(0)
        if not isinstance(file_path, str):
            fail_closed(
                f"{tool_name}.file_path was {type(file_path).__name__}, expected string"
            )

        resolved = resolve_path(file_path, cwd)

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
    if not isinstance(command, str):
        # Codex currently sends Bash.command as a string. If a host ever sends
        # argv, the rules below would silently match nothing — deny instead.
        fail_closed(
            f"Bash.command was {type(command).__name__}, expected string; "
            "the command rules cannot evaluate this payload"
        )
    if not command.strip():
        sys.exit(0)

    # Check the raw command (after stripping quotes to avoid false positives
    # from heredocs / commit messages).
    check_bash_patterns(strip_quoted_content(command))

    # Also extract and check inner commands from bash -c / sh -c wrappers.
    # Without this, `bash -c 'git reset --hard'` would evade detection
    # because strip_quoted_content removes the single-quoted payload.
    # Heredoc bodies are stripped first: a wrapper written into a file is
    # data, not something this command runs.
    inner_commands = extract_inner_commands(strip_heredocs(command))
    for inner in inner_commands:
        check_bash_patterns(strip_quoted_content(inner))

    # Credential files named anywhere in the command or its inner commands.
    for text in [command, *inner_commands]:
        check_shell_paths(text, cwd)

    # Allowed
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — any failure must deny
        fail_closed(f"{type(exc).__name__}: {exc}")
