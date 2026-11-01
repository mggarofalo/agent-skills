"""Claude Code PreToolUse hook: keep private Plane references out of external work.

The Plane instance (plane.wallingford.me) is private. Its project IDs
(SECRES-12, MARVEL-3, ...) and links must never reach anything outside it:
upstream issues, comments, merge requests, commit messages, emails.

This hook denies an outward-facing tool call when its content mentions the
Plane host, a Plane work-item ID, or "Plane issue/work item/project/ticket".
Outward-facing means:

- git commit/tag/notes/push, gh, glab: only when the target repository is
  external (none of its remotes is owned by mggarofalo). Commits in your own
  repos may reference Plane IDs, as agent-skills commits do. A push is checked
  against the messages and added lines of commits not yet on any remote.
- curl/wget/Invoke-RestMethod/Invoke-WebRequest: when any URL in the command
  points at a host other than Plane or localhost.
- Browser text entry (form_input, typing, javascript, batches) in the
  built-in browser and Claude in Chrome. The page URL isn't in the payload,
  so this applies on every site; edit Plane with the plane CLI instead.
- Email: send, reply, forward and draft tools.

Files passed by reference (git commit -F, gh --body-file, curl -d @file) are
read and checked too. Matching is case-insensitive; the bare word "plane" is
not a match, because image formats legitimately talk about color planes.

Fails closed (exit 2) on a payload it can't parse, like the other guards.

The same patterns back plain git hooks for external clones, which also catch
commits made by hand:

    commit-msg:  python <this file> --scan-file "$1"
    pre-push:    python <this file> --git-pre-push     (reads git's ref lines)

Both exit 1 with a message when they find a private reference.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from urllib.parse import urlparse

OWNER = "mggarofalo"
INTERNAL_HOSTS = {"plane.wallingford.me", "localhost", "127.0.0.1", "::1"}

# Plane project identifiers, from `plane project list`. Add new projects here.
PLANE_PROJECTS = (
    "EVERYTHING", "GAS", "GHSYNC", "MARVEL", "MEMORIA", "PLANECLI", "PPLLM",
    "RECEIPTS", "SECRES", "SHOPPING", "SKILLS", "SPEAKTYPE", "WHISPER", "WSLUX",
)

PRIVATE_PATTERNS = (
    ("the private Plane host", re.compile(r"plane\.wallingford\.me", re.I)),
    (
        "a Plane work-item ID",
        re.compile(r"\b(?:%s)-\d+\b" % "|".join(PLANE_PROJECTS), re.I),
    ),
    (
        "a reference to Plane tracking",
        re.compile(r"\bplane\s+(?:issues?|work[- ]?items?|projects?|tickets?|cli)\b", re.I),
    ),
)

SHELL_TOOLS = {"Bash", "PowerShell"}
BROWSER_ACTIONS = ("form_input", "computer", "javascript_tool", "browser_batch")
EMAIL_ACTIONS = ("send_message", "create_draft", "update_draft", "reply", "forward")

GIT_WRITE = re.compile(
    r"\bgit(?P<opts>(?:\s+-C\s+\S+|\s+-c\s+\S+)*)\s+(?P<verb>commit|tag|notes|push)\b"
)
FORGE_CLI = re.compile(r"(?:^|[\s;&|(])(?:gh|glab)\s+\S")
HTTP_CLIENT = re.compile(
    r"(?:^|[\s;&|(])(?:curl|wget|Invoke-RestMethod|Invoke-WebRequest|irm|iwr)\b", re.I
)
URL = re.compile(r"https?://[^\s'\"<>)]+", re.I)
FILE_FLAGS = {"-F", "--file", "--body-file", "-T", "--upload-file", "-InFile"}
DATA_FLAGS = {"-d", "--data", "--data-binary", "--data-raw", "--data-urlencode"}
MAX_FILE_BYTES = 1 << 20


def deny(reason: str) -> None:
    """Output JSON denial to stdout and exit."""
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


def find_private(text: str):
    """Return (description, matched text) for the first private reference, or None."""
    for description, pattern in PRIVATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return description, match.group(0)
    return None


def block(found, where: str) -> None:
    description, matched = found
    deny(
        f"BLOCKED: {where} contains {description} ({matched!r}). The Plane instance is "
        "private: never mention it, its links, or its work-item IDs in external issues, "
        "comments, MRs/PRs, commit messages or email. Remove the reference and retry; "
        "keep tracking details in Plane itself."
    )


def words(command: str):
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def referenced_files(command: str, cwd: str) -> str:
    """Contents of files a command sends by reference (-F msg, -d @body, ...)."""
    tokens = words(command)
    paths = []
    for i, token in enumerate(tokens):
        if token in FILE_FLAGS and i + 1 < len(tokens):
            paths.append(tokens[i + 1])
        elif token in DATA_FLAGS and i + 1 < len(tokens) and tokens[i + 1].startswith("@"):
            paths.append(tokens[i + 1][1:])
        elif token.startswith(("--file=", "--body-file=")):
            paths.append(token.split("=", 1)[1])
    chunks = []
    for path in paths:
        full = os.path.join(cwd, os.path.expanduser(path))
        try:
            with open(full, "rb") as f:
                chunks.append(f.read(MAX_FILE_BYTES).decode("utf-8", "replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def git(args, cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def is_own_remote(url: str) -> bool:
    return bool(re.search(r"[/:]%s/" % re.escape(OWNER), url, re.I))


def repo_is_external(repo_dir: str) -> bool:
    """True when the repo has a remote and none of its remotes belong to OWNER."""
    urls = git(["remote", "-v"], repo_dir).split()
    remotes = [u for u in urls if "://" in u or "@" in u]
    return bool(remotes) and not any(is_own_remote(u) for u in remotes)


def git_repo_dir(opts: str, cwd: str) -> str:
    match = re.search(r"-C\s+(\S+)", opts or "")
    if not match:
        return cwd
    path = match.group(1).strip("'\"")
    return path if os.path.isabs(path) else os.path.join(cwd, path)


def unpushed_content(repo_dir: str) -> str:
    """Messages and added lines of commits that aren't on any remote yet."""
    log = git(["log", "--format=%B", "-p", "--no-color", "HEAD", "--not", "--remotes"], repo_dir)
    keep = [
        line for line in log.splitlines()
        if not line.startswith(("-", "diff --git", "index ", "@@"))
    ]
    return "\n".join(keep)[: 2 * MAX_FILE_BYTES]


def forge_target_external(command: str, cwd: str) -> bool:
    """Whether a gh/glab command targets a repository not owned by OWNER."""
    match = re.search(r"(?:--repo|-R)[=\s]+(\S+)", command)
    if match:
        return not match.group(1).strip("'\"").lower().startswith(OWNER.lower() + "/")
    for url in URL.findall(command):
        if not is_own_remote(urlparse(url).path + "/"):
            return True
    return repo_is_external(cwd)


def check_shell(command: str, cwd: str) -> None:
    sent = command + "\n" + referenced_files(command, cwd)

    for match in GIT_WRITE.finditer(command):
        repo_dir = git_repo_dir(match.group("opts"), cwd)
        if not repo_is_external(repo_dir):
            continue
        found = find_private(sent)
        if found:
            block(found, f"this git {match.group('verb')} for an external repository")
        if match.group("verb") == "push":
            found = find_private(unpushed_content(repo_dir))
            if found:
                block(found, "a commit you are about to push to an external repository")

    if FORGE_CLI.search(command) and forge_target_external(command, cwd):
        found = find_private(sent)
        if found:
            block(found, "this gh/glab command for an external repository")

    if HTTP_CLIENT.search(command):
        hosts = {(urlparse(u).hostname or "").lower() for u in URL.findall(command)}
        if hosts - INTERNAL_HOSTS:
            found = find_private(sent)
            if found:
                block(found, "this HTTP request to an external host")


ZERO_SHA = re.compile(r"^0+$")


def git_hook_main(mode: str, args) -> None:
    """Entry point for the commit-msg and pre-push git hooks."""
    if mode == "--scan-file":
        with open(args[0], encoding="utf-8", errors="replace") as f:
            found = find_private(f.read())
        where = "This commit message"
    else:
        content = []
        for line in sys.stdin.read().splitlines():
            parts = line.split()
            if len(parts) != 4 or ZERO_SHA.match(parts[1]):
                continue  # malformed, or deleting a remote branch
            local, remote = parts[1], parts[3]
            span = ["--not", "--remotes"] if ZERO_SHA.match(remote) else [f"^{remote}"]
            log = git(["log", "--format=%B", "-p", "--no-color", local, *span], os.getcwd())
            content.append(log)
        found = find_private("\n".join(
            line for line in "\n".join(content).splitlines()
            if not line.startswith(("-", "diff --git", "index ", "@@"))
        ))
        where = "A commit being pushed"
    if found:
        description, matched = found
        print(
            f"{where} contains {description} ({matched!r}). The Plane instance is private; "
            "remove the reference before sending this to an external repository.",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--scan-file", "--git-pre-push"):
        git_hook_main(sys.argv[1], sys.argv[2:])
    try:
        payload = json.loads(sys.stdin.read())
        tool = payload.get("tool_name") or ""
        tool_input = payload.get("tool_input") or {}
        cwd = payload.get("cwd") or os.getcwd()
    except (ValueError, AttributeError) as exc:
        print(f"block-private-tracker-refs: unreadable payload ({exc}); failing closed", file=sys.stderr)
        sys.exit(2)

    if tool in SHELL_TOOLS:
        command = tool_input.get("command") or ""
        if command.strip():
            check_shell(command, cwd)
        sys.exit(0)

    action = tool.rsplit("__", 1)[-1]
    is_browser = tool.startswith("mcp__") and action in BROWSER_ACTIONS and (
        "Browser" in tool or "chrome" in tool
    )
    is_email = tool.startswith("mcp__") and action in EMAIL_ACTIONS
    if is_browser or is_email:
        found = find_private(json.dumps(tool_input, ensure_ascii=False))
        if found:
            block(found, "text you are about to enter in a browser" if is_browser else "this email")

    sys.exit(0)


if __name__ == "__main__":
    main()
