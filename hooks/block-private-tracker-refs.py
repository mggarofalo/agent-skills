"""Claude Code PreToolUse hook: keep a private issue tracker out of external work.

The tracker (a self-hosted Plane instance) is private. Its hostname, links
and work-item IDs (KEY-123) must never reach anything outside this machine:
upstream issues, comments, merge requests, commit messages, emails, and any
repository on a public forge, including your own.

The private values themselves live in a local file that is never committed,
so this public script carries only the mechanism:

    ~/.claude/private-tracker.json   (override with PRIVATE_TRACKER_CONFIG)
    {"hosts": ["tracker.example"], "project_keys": ["ACME", "OPS"],
     "own_namespaces": ["your-github-user"]}

The hook denies an outward-facing tool call when its content mentions one of
those hosts or a KEY-<n> ID for one of those keys, everywhere, your own
public repos included. Destinations outside your own namespaces (upstream
projects, email, browser typing) additionally reject the tracker's name
followed by issue(s), work item(s), project(s), ticket(s) or CLI (see
TRACKER_PHRASE), which would reveal that a private tracker exists. Your own
repos may still discuss the tracker product itself, e.g. a skill for its
CLI. Outward-facing means:

- git commit/tag/notes/push, gh, glab: in any repository that has a remote.
  A push is also checked against the messages and added lines of commits not
  yet on any remote. Repositories without a remote are local-only and exempt.
- curl/wget/Invoke-RestMethod/Invoke-WebRequest: when any URL in the command
  points at a host other than the tracker or localhost.
- Browser text entry (form_input, typing, javascript, batches) in the
  built-in browser and Claude in Chrome. The page URL isn't in the payload,
  so this applies on every site; edit the tracker with its CLI instead.
- Email: send, reply, forward and draft tools.

Files passed by reference (git commit -F, gh --body-file, curl -d @file) are
read and checked too. Matching is case-insensitive; the bare word "plane" is
not a match, because image formats legitimately talk about color planes.

Fails closed: exit 2 on a payload it can't parse, and a deny for any
outward-facing call while the config file is missing or invalid.

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
from pathlib import Path
from urllib.parse import urlparse

CONFIG_PATH = Path(
    os.environ.get("PRIVATE_TRACKER_CONFIG") or Path.home() / ".claude" / "private-tracker.json"
)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
TRACKER_PHRASE = re.compile(
    r"\bplane\s+(?:issues?|work[- ]?items?|projects?|tickets?|cli)\b", re.I
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
KEY_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
MAX_FILE_BYTES = 1 << 20
ZERO_SHA = re.compile(r"^0+$")


class ConfigError(Exception):
    pass


class Config:
    """The private values, read from the local config file."""

    def __init__(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.hosts = {h.strip().lower() for h in data["hosts"] if h.strip()}
            keys = [k.strip() for k in data["project_keys"] if k.strip()]
            self.owners = {o.strip().lower() for o in data.get("own_namespaces", []) if o.strip()}
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ConfigError(f"{path}: {exc}") from exc
        if not self.hosts or not all(KEY_SHAPE.match(k) for k in keys):
            raise ConfigError(f"{path}: needs a non-empty 'hosts' list and alphanumeric 'project_keys'")
        # Hosts and IDs are private everywhere; the phrase only matters outside your namespaces.
        self.strict = [("the private tracker host", re.compile("|".join(map(re.escape, self.hosts)), re.I))]
        if keys:
            self.strict.append(
                ("a private work-item ID", re.compile(r"\b(?:%s)-\d+\b" % "|".join(keys), re.I))
            )
        self.external = self.strict + [("a reference to the private tracker", TRACKER_PHRASE)]

    def owns_remote(self, url: str) -> bool:
        return any(re.search(r"[/:]%s/" % re.escape(o), url, re.I) for o in self.owners)

    def owns_repo(self, repo_dir: str) -> bool:
        urls = [u for u in git(["remote", "-v"], repo_dir).split() if "://" in u or "@" in u]
        return bool(urls) and all(self.owns_remote(u) for u in urls)

    def patterns_for_forge(self, command: str, cwd: str):
        match = re.search(r"(?:--repo|-R)[=\s]+(\S+)", command)
        if match:
            owner = match.group(1).strip("'\"").split("/", 1)[0].lower()
            return self.strict if owner in self.owners else self.external
        return self.strict if self.owns_repo(cwd) else self.external


def load_config() -> Config:
    return Config(CONFIG_PATH)


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


def find_private(text: str, patterns):
    """Return (description, matched text) for the first private reference, or None."""
    for description, pattern in patterns:
        match = pattern.search(text)
        if match:
            return description, match.group(0)
    return None


def block(found, where: str) -> None:
    description, matched = found
    deny(
        f"BLOCKED: {where} contains {description} ({matched!r}). The issue tracker is "
        "private: never mention it, its links, or its work-item IDs in commits, PRs, "
        "issues, comments or email that leave this machine, even in your own repos. "
        "Remove the reference and retry; keep cross-references on the tracker side."
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


def has_remote(repo_dir: str) -> bool:
    return bool(git(["remote"], repo_dir).strip())


def git_repo_dir(opts: str, cwd: str) -> str:
    match = re.search(r"-C\s+(\S+)", opts or "")
    if not match:
        return cwd
    path = match.group(1).strip("'\"")
    return path if os.path.isabs(path) else os.path.join(cwd, path)


def added_content(log: str) -> str:
    """Commit messages and added lines from `git log -p` output."""
    keep = [
        line for line in log.splitlines()
        if not line.startswith(("-", "diff --git", "index ", "@@"))
    ]
    return "\n".join(keep)[: 2 * MAX_FILE_BYTES]


def unpushed_content(repo_dir: str) -> str:
    """Messages and added lines of commits that aren't on any remote yet."""
    return added_content(
        git(["log", "--format=%B", "-p", "--no-color", "HEAD", "--not", "--remotes"], repo_dir)
    )


def is_outward_shell(command: str, cwd: str, tracker_hosts) -> bool:
    if FORGE_CLI.search(command):
        return True
    if HTTP_CLIENT.search(command):
        hosts = {(urlparse(u).hostname or "").lower() for u in URL.findall(command)}
        if hosts - LOCAL_HOSTS - tracker_hosts:
            return True
    for match in GIT_WRITE.finditer(command):
        if has_remote(git_repo_dir(match.group("opts"), cwd)):
            return True
    return False


def check_shell(command: str, cwd: str, config: Config) -> None:
    sent = command + "\n" + referenced_files(command, cwd)

    for match in GIT_WRITE.finditer(command):
        repo_dir = git_repo_dir(match.group("opts"), cwd)
        if not has_remote(repo_dir):
            continue
        patterns = config.strict if config.owns_repo(repo_dir) else config.external
        found = find_private(sent, patterns)
        if found:
            block(found, f"this git {match.group('verb')}")
        if match.group("verb") == "push":
            found = find_private(unpushed_content(repo_dir), patterns)
            if found:
                block(found, "a commit you are about to push")

    if FORGE_CLI.search(command):
        found = find_private(sent, config.patterns_for_forge(command, cwd))
        if found:
            block(found, "this gh/glab command")

    if HTTP_CLIENT.search(command):
        hosts = {(urlparse(u).hostname or "").lower() for u in URL.findall(command)}
        if hosts - LOCAL_HOSTS - config.hosts:
            found = find_private(sent, config.external)
            if found:
                block(found, "this HTTP request to an external host")


def git_hook_main(mode: str, args) -> None:
    """Entry point for the commit-msg and pre-push git hooks."""
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"private-tracker guard: config unusable ({exc}); refusing", file=sys.stderr)
        sys.exit(1)
    # Git hooks are installed in clones of external projects: apply every check.
    patterns = config.strict if config.owns_repo(os.getcwd()) else config.external
    if mode == "--scan-file":
        with open(args[0], encoding="utf-8", errors="replace") as f:
            found = find_private(f.read(), patterns)
        where = "This commit message"
    else:
        logs = []
        for line in sys.stdin.read().splitlines():
            parts = line.split()
            if len(parts) != 4 or ZERO_SHA.match(parts[1]):
                continue  # malformed, or deleting a remote branch
            local, remote = parts[1], parts[3]
            span = ["--not", "--remotes"] if ZERO_SHA.match(remote) else [f"^{remote}"]
            logs.append(git(["log", "--format=%B", "-p", "--no-color", local, *span], os.getcwd()))
        found = find_private(added_content("\n".join(logs)), patterns)
        where = "A commit being pushed"
    if found:
        description, matched = found
        print(
            f"{where} contains {description} ({matched!r}). The issue tracker is private; "
            "remove the reference before this leaves the machine.",
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

    action = tool.rsplit("__", 1)[-1]
    is_browser = tool.startswith("mcp__") and action in BROWSER_ACTIONS and (
        "Browser" in tool or "chrome" in tool
    )
    is_email = tool.startswith("mcp__") and action in EMAIL_ACTIONS
    command = (tool_input.get("command") or "") if tool in SHELL_TOOLS else ""
    if not (is_browser or is_email or command.strip()):
        sys.exit(0)

    try:
        config = load_config()
    except ConfigError as exc:
        if is_browser or is_email or is_outward_shell(command, cwd, set()):
            deny(
                f"BLOCKED: the private-tracker guard has no usable config ({exc}), so it "
                "can't check outward-facing actions. Create it with your tracker's hosts "
                'and project keys: {"hosts": [...], "project_keys": [...]}.'
            )
        sys.exit(0)

    if command.strip():
        check_shell(command, cwd, config)
    else:
        found = find_private(json.dumps(tool_input, ensure_ascii=False), config.external)
        if found:
            block(found, "text you are about to enter in a browser" if is_browser else "this email")
    sys.exit(0)


if __name__ == "__main__":
    main()
