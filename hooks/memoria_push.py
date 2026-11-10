"""Send session transcripts to a Memoria server, through an offline spool.

Off unless the config file (see config_path) holds `"push": true`. With no such
file nothing here reads stdin, opens a socket or writes a file.

The session-end hooks call it from their detached worker, never from the hook
process itself, so a slow or unreachable server cannot hold up a session.

- **What is sent.** Raw transcripts, to `POST /v1/ingest/session`: Claude Code
  with `format=claude`, Codex with `format=codex`. The server renders and
  redacts them; nothing is rendered or redacted here, and nothing is sent
  anywhere but the configured server.
- **Idempotent.** The server knows a session by its id (and, for Claude Code,
  its project folder), and orders copies by `updated`, so sending a session
  again replaces it rather than adding a second copy.
- **The spool.** A changed transcript gets one entry under `<state>/spool`, keyed
  by its path, so a re-export overwrites rather than duplicates. An entry leaves
  the spool only once the server has accepted it. If the server cannot be
  reached, the entry stays, a copy of the transcript is kept beside it in case
  the original is cleaned up, and the next session end tries again.
- **Refusals are kept, not dropped.** A refusal that sending again cannot fix,
  such as 409 `session_shrank`, holds the entry and logs it on every run until
  the transcript changes or someone deletes the entry.
- **Too large is held, not tried.** A transcript over `max_session_bytes`, the
  server's limit on one session upload (256 MiB unless the config says
  otherwise), is held the same way without being read or sent: the server would
  refuse it whole, and sending it anyway can end in a broken connection, which
  would look like a server worth trying again.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote, urlencode, urlsplit

CONFIG_ENV = "AGENT_SKILLS_MEMORIA_CONFIG"
KEY_ENV = "MEMORIA_API_KEY"
URL_ENV = "MEMORIA_URL"
PROFILE_ENV = "MEMORIA_PROFILE"
INSECURE_ENV = "MEMORIA_ALLOW_INSECURE_HTTP"
KEYRING_SERVICE = "memoria-cli"  # the memoria CLI's keyring service name
DEFAULT_COLLECTIONS = {"claude": "claude-sessions", "codex": "codex-sessions"}
DEFAULT_TIMEOUT = 60.0  # seconds per request
DEFAULT_BUDGET = 300.0  # seconds per run, so one run cannot hold the worker for long
# The server's default Memoria:Ingest:MaxSessionBytes. It refuses a larger upload whole, so one is never sent.
DEFAULT_MAX_SESSION_BYTES = 256 * 1024 * 1024
STATE_VERSION = 1
CWD_PROBE_BYTES = 256 * 1024
UUID_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.IGNORECASE)
KEYRING_TIMEOUT = 10

Log = Callable[[str], None]


class ConfigError(Exception):
    """The config asks for push but cannot be used as it stands."""


class CredentialError(Exception):
    """No usable key. Messages never include a key."""


# --- configuration -----------------------------------------------------------


def _config_root() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", "")
    return Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    return _config_root() / "agent-skills" / "memoria.json"


def read_config() -> Optional[dict]:
    """The config as a dict, or None when there is no file."""
    path = config_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error}") from None
    try:
        data = json.loads(text)
    except ValueError as error:
        raise ConfigError(f"{path} is not valid JSON: {error}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must hold a JSON object")
    return data


def push_enabled() -> bool:
    """Cheap check for the hook process. Never raises.

    A config file that exists but cannot be read counts as on, so the worker gets
    to log why. No file, or a path that is not a file, is off.
    """
    try:
        if not config_path().is_file():
            return False
    except OSError:
        return False
    try:
        data = read_config()
    except ConfigError:
        return True
    return bool(data) and data.get("push") is True


@dataclass
class Settings:
    url: str
    origin: str
    profile: str
    collections: dict = field(default_factory=lambda: dict(DEFAULT_COLLECTIONS))
    since: Optional[float] = None
    timeout: float = DEFAULT_TIMEOUT
    budget: float = DEFAULT_BUDGET
    max_session_bytes: int = DEFAULT_MAX_SESSION_BYTES
    config_mtime: float = 0.0


def _cli_config() -> dict:
    """The memoria CLI's own config.json: active profile and server URLs, no keys."""
    try:
        data = json.loads((_config_root() / "memoria" / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _number(data: dict, name: str, default: float) -> float:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{name} must be a positive number of seconds")
    return float(value)


def _bytes(data: dict, name: str, default: int) -> int:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{name} must be a positive whole number of bytes")
    return value


def parse_time(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ConfigError(f"since must be an ISO date or timestamp, not {value!r}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def load_settings() -> Optional[Settings]:
    """Settings when push is on, None when it is off. Raises ConfigError."""
    data = read_config()
    if not data or data.get("push") is not True:
        return None
    cli = _cli_config()
    profile = data.get("profile") or os.environ.get(PROFILE_ENV) or cli.get("active_profile") or "default"
    if not isinstance(profile, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", profile):
        raise ConfigError("profile must be a memoria CLI profile name")
    profiles = cli.get("profiles") if isinstance(cli.get("profiles"), dict) else {}
    profile_url = (profiles.get(profile) or {}).get("api_url") if isinstance(profiles.get(profile), dict) else None
    url = data.get("url") or os.environ.get(URL_ENV) or profile_url
    if not url or not isinstance(url, str):
        raise ConfigError("push is on but names no server: set \"url\", or run 'memoria auth login --api-url <url>'")
    allow_insecure = data.get("allow_insecure_http") is True or os.environ.get(INSECURE_ENV) == "1"
    origin = check_url(url, allow_insecure)
    collections = dict(DEFAULT_COLLECTIONS)
    custom = data.get("collections", {})
    if not isinstance(custom, dict) or not all(isinstance(v, str) and v for v in custom.values()):
        raise ConfigError("collections must map claude and codex to collection names")
    collections.update(custom)
    since = data.get("since")
    try:
        config_mtime = config_path().stat().st_mtime
    except OSError:
        config_mtime = time.time()
    parts = urlsplit(url)
    url = f"{parts.scheme.lower()}://{parts.netloc}{parts.path}"  # check_url refused a query or fragment
    return Settings(
        url=url.rstrip("/"),
        origin=origin,
        profile=profile,
        collections=collections,
        since=parse_time(since) if since else None,
        timeout=_number(data, "timeout", DEFAULT_TIMEOUT),
        budget=_number(data, "budget", DEFAULT_BUDGET),
        max_session_bytes=_bytes(data, "max_session_bytes", DEFAULT_MAX_SESSION_BYTES),
        config_mtime=config_mtime,
    )


def origin_of(url: str) -> str:
    """scheme://host:port, as the memoria CLI records it beside a stored key."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port or {"http": 80, "https": 443}.get(scheme)
    host_part = f"[{host}]" if ":" in host else host
    return f"{scheme}://{host_part}:{port}"


def check_url(url: str, allow_insecure: bool) -> str:
    """Refuse a URL the memoria CLI would refuse to send a key to. Returns its origin."""
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 - raises on a bad port
    except ValueError:
        raise ConfigError("url is not a valid URL") from None
    host = parts.hostname or ""
    if parts.scheme not in ("http", "https") or not host:
        raise ConfigError("url must be an http or https URL with a host")
    if not host.isascii():
        raise ConfigError("url must use the xn-- form of an internationalized host name")
    if parts.username or parts.password:
        raise ConfigError("url must not hold credentials")
    if parts.query or parts.fragment:
        raise ConfigError("url must not have a query or fragment")
    if parts.scheme == "http" and not allow_insecure and not _http_allowed(host):
        raise ConfigError("refusing plain http to a host name or public address: the key could be read in transit")
    return origin_of(url)


def _http_allowed(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if address.is_link_local:
        return False
    return address.is_loopback or address.is_private


# --- the key -----------------------------------------------------------------


def normalize_key(raw: str) -> str:
    key = raw.lstrip("﻿").strip()
    if not 8 <= len(key) <= 4096 or any(not 0x20 < ord(c) < 0x7F for c in key):
        raise CredentialError("the API key is not in a form that can be sent")
    return key


def resolve_key(settings: Settings) -> str:
    """MEMORIA_API_KEY, then the memoria CLI's keyring login for this profile.

    A keyring key goes only to the server it was saved for, as with the CLI.
    The CLI's unencrypted file backend is not read.
    """
    raw = os.environ.get(KEY_ENV)
    if raw:
        return normalize_key(raw)
    value = keyring_get(f"{settings.profile}/api-key")
    if value is None:
        raise CredentialError(
            f"no key for profile {settings.profile!r}: run 'memoria auth login --api-url {settings.url}', "
            f"or set {KEY_ENV}"
        )
    try:
        entry = json.loads(value)
        origin, key = entry["origin"], entry["key"]
    except (ValueError, TypeError, KeyError):
        raise CredentialError("the keyring entry is not in the form the memoria CLI writes") from None
    if origin != settings.origin:
        raise CredentialError(
            f"the key stored for profile {settings.profile!r} was saved for another server, not {settings.origin}"
        )
    return normalize_key(key)


def keyring_get(name: str) -> Optional[str]:
    """Read one entry the memoria CLI wrote. None when there is no entry."""
    if os.name == "nt":
        return _windows_credential(f"{KEYRING_SERVICE}:{name}")
    if sys.platform == "darwin":
        return _run_keyring(["/usr/bin/security", "find-generic-password", "-s", KEYRING_SERVICE, "-a", name, "-w"],
                            not_found=(44,))
    bus = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if bus and not (runtime and bus.startswith(f"unix:path={runtime.rstrip('/')}/")):
        raise CredentialError("refusing a session bus outside this user's runtime directory")
    return _run_keyring(["secret-tool", "lookup", "service", KEYRING_SERVICE, "username", name], not_found=(1,))


def _run_keyring(command: list, not_found: tuple) -> Optional[str]:
    import subprocess

    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=KEYRING_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CredentialError(f"cannot read the keyring with {command[0]}: {type(error).__name__}") from None
    if result.returncode in not_found and not result.stdout.strip():
        return None
    if result.returncode != 0:
        raise CredentialError(f"{command[0]} failed with exit {result.returncode}")
    return result.stdout.strip()


def _windows_credential(target: str) -> Optional[str]:
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    pointer = ctypes.POINTER(CREDENTIAL)()
    if not advapi.CredReadW(target, 1, 0, ctypes.byref(pointer)):  # 1 = CRED_TYPE_GENERIC
        error = ctypes.get_last_error()
        if error == 1168:  # ERROR_NOT_FOUND
            return None
        raise CredentialError(f"Credential Manager refused the read (error {error})")
    try:
        credential = pointer.contents
        return ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize).decode("utf-8")
    finally:
        advapi.CredFree(pointer)


# --- transcripts -------------------------------------------------------------


@dataclass
class Source:
    fmt: str  # "claude" or "codex"
    path: Path
    session_id: str
    project_directory: Optional[str] = None


def claude_sources(projects_dir: Path) -> list:
    """Top-level transcripts, the same files the Claude exporter reads."""
    if not projects_dir.is_dir():
        return []
    return [
        Source("claude", path, path.stem, path.parent.name)
        for project in sorted(projects_dir.iterdir()) if project.is_dir()
        for path in sorted(project.glob("*.jsonl"))
    ]


def codex_sources(codex_home: Path) -> list:
    """Rollouts under sessions/ and archived_sessions/, the same files the Codex exporter reads."""
    sources = []
    for directory in (codex_home / "sessions", codex_home / "archived_sessions"):
        if directory.is_dir():
            for path in sorted(directory.rglob("*.jsonl")):
                match = UUID_RE.search(path.stem)
                sources.append(Source("codex", path, match.group(1) if match else path.stem))
    return sources


def read_hook_input(timeout: float = 1.0) -> dict:
    """The hook's JSON on stdin, or {} if none arrives in time."""
    box: dict = {}

    def read() -> None:
        try:
            box["text"] = sys.stdin.read()
        except (OSError, ValueError):
            pass

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    reader.join(timeout)
    try:
        value = json.loads(box.get("text") or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


# --- spool and state ---------------------------------------------------------


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _write_json(path: Path, value: Any) -> None:
    _atomic_write(path, json.dumps(value, indent=1, sort_keys=True).encode("utf-8"))


def _read_json(path: Path) -> Optional[dict]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def entry_key(source: Source) -> str:
    digest = hashlib.sha256(str(source.path).encode("utf-8")).hexdigest()[:12]
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", source.session_id)[:80]
    return f"{source.fmt}-{safe}-{digest}"


def load_state(state_dir: Path, settings: Settings) -> dict:
    """What was sent to this server. A different server starts over."""
    state = _read_json(state_dir / "state.json")
    if state and state.get("version") == STATE_VERSION and state.get("origin") == settings.origin:
        return state
    # Sessions last changed before push was turned on are left to `memoria migrate`.
    baseline = min(settings.config_mtime or time.time(), time.time())
    return {"version": STATE_VERSION, "origin": settings.origin, "since": baseline, "sent": {}}


def enqueue(state_dir: Path, state: dict, settings: Settings, sources: list) -> int:
    """Spool every transcript that changed since it was last accepted. Returns how many were added."""
    since = settings.since if settings.since is not None else state["since"]
    spool = state_dir / "spool"
    added = 0
    for source in sources:
        try:
            stat = source.path.stat()
        except OSError:
            continue
        if stat.st_mtime < since:
            continue
        version = [stat.st_size, stat.st_mtime_ns]
        if state["sent"].get(str(source.path)) == version:
            continue
        path = spool / f"{entry_key(source)}.json"
        existing = _read_json(path) or {}
        if [existing.get("size"), existing.get("mtime_ns")] == version:
            continue  # already waiting, or held, at this version
        _write_json(path, {
            "format": source.fmt,
            "session_id": source.session_id,
            "project_directory": source.project_directory,
            "path": str(source.path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "attempts": existing.get("attempts", 0),
            "snapshot": existing.get("snapshot"),
            "held": None,
            "last_error": existing.get("last_error"),
        })
        added += 1
    return added


def _read_body(entry: dict, snapshot_path: Path) -> Optional[tuple]:
    """(body, size, mtime_ns, from_snapshot), or None if neither the transcript nor a copy exists.

    A transcript still being written can end in half a line, so the body stops at
    the last newline. The rest goes next time, as the file will have changed.
    """
    path = Path(entry["path"])
    try:
        stat = path.stat()
        with path.open("rb") as handle:
            body = handle.read(stat.st_size)
        from_snapshot = False
        size, mtime_ns = stat.st_size, stat.st_mtime_ns
    except OSError:
        snapshot = entry.get("snapshot")
        if not snapshot:
            return None
        try:
            body = snapshot_path.read_bytes()
        except OSError:
            return None
        from_snapshot = True
        size, mtime_ns = snapshot["size"], snapshot["mtime_ns"]
    end = body.rfind(b"\n")
    return (body[: end + 1] if end >= 0 else b""), size, mtime_ns, from_snapshot


def _size_to_send(entry: dict) -> Optional[int]:
    """How large the body would be: the transcript's size, or its kept copy's once it is gone. None when neither is there."""
    try:
        return Path(entry["path"]).stat().st_size
    except OSError:
        snapshot = entry.get("snapshot") or {}
        size = snapshot.get("size")
        return size if isinstance(size, int) and not isinstance(size, bool) else None


def too_large(settings: Settings, entry: dict) -> Optional[str]:
    """Why an entry cannot be sent, or None when it fits the server's limit on one session upload."""
    size = _size_to_send(entry)
    if size is None or size <= settings.max_session_bytes:
        return None
    return (f"its transcript is {size} bytes, over the server's {settings.max_session_bytes} byte limit on one "
            "session upload, so the server cannot take it and it was not sent. If the server's "
            f"Memoria:Ingest:MaxSessionBytes is higher, set max_session_bytes in {config_path()} to match")


def iso_utc(mtime_ns: int) -> str:
    moment = datetime.fromtimestamp(mtime_ns / 1e9, tz=timezone.utc)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


# --- sending -----------------------------------------------------------------


@dataclass
class Reply:
    status: Optional[int]  # None when the server could not be reached
    payload: Optional[dict] = None
    error: str = ""


def send(settings: Settings, key: str, entry: dict, body: bytes, mtime_ns: int) -> Reply:
    import http.client
    import urllib.error
    import urllib.request

    params = {
        "collection": settings.collections[entry["format"]],
        "format": entry["format"],
        "sessionId": entry["session_id"],
        "updated": iso_utc(mtime_ns),
    }
    if entry.get("project_directory"):
        params["projectDirectory"] = entry["project_directory"]
    url = f"{settings.url}/v1/ingest/session?{urlencode(params, quote_via=quote)}"
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/x-ndjson",
        "Accept": "application/json",
        "User-Agent": "agent-skills-session-push",
    })
    request.add_unredirected_header("Authorization", f"Bearer {key}")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):  # a redirect could carry the key elsewhere
            return None

    handlers: list = [NoRedirect()]
    if urlsplit(url).scheme.lower() == "http":
        handlers.append(urllib.request.ProxyHandler({}))  # plain http never goes through a proxy
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(request, timeout=settings.timeout) as response:
            return Reply(response.status, _payload(response.read()))
    except urllib.error.HTTPError as error:
        try:
            raw = error.read()
        except OSError:
            raw = b""
        return Reply(error.code, _payload(raw))
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as error:
        reason = getattr(error, "reason", error)
        return Reply(None, error=f"{type(reason).__name__}: {reason}"[:300])


def _payload(raw: bytes) -> Optional[dict]:
    try:
        value = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


DONE, RETRY, HOLD, STOP = "done", "retry", "hold", "stop"
# Refusals about one session, which sending again as it is cannot fix.
SESSION_REFUSALS = {"session_shrank", "path_owned", "lost_content", "session_id_mismatch",
                    "document_too_large", "payload_too_large"}
# Refusals about the collection, which every session would get alike.
COLLECTION_REFUSALS = {"ingest_not_enabled", "collection_not_empty"}


def classify(reply: Reply) -> tuple:
    """(outcome, reason). STOP keeps this and every later entry for the next run."""
    status, payload = reply.status, reply.payload or {}
    code = payload.get("code") or ""
    if status is None:
        return STOP, f"unreachable ({reply.error})"
    if status == 202:
        return DONE, "stored"
    if status == 207:
        if payload.get("retryable"):
            return RETRY, "partly stored; the server asked for it again"
        return HOLD, "partly stored, and the server says sending it again will not finish it"
    if status == 409 and code == "stale_version":
        return DONE, "the server already holds this version or a newer one"
    if status == 409 and code in ("ingest_in_progress", "deleted_during_upload"):
        return RETRY, f"the server asked for it again ({code})"
    if status in (401, 403):
        return STOP, f"the server refused the key ({status} {code})".strip()
    if status == 429:
        return STOP, "rate limited"
    if status == 408 or status >= 500:
        return STOP, f"server unavailable ({status} {code})".strip()
    if code in COLLECTION_REFUSALS:
        return STOP, f"the collection cannot take it ({status} {code})"
    if code in SESSION_REFUSALS or status in (409, 413, 422):
        # About this session alone: holding it lets the others go on.
        return HOLD, f"refused: {status} {code}".strip()
    # Anything else, such as a 404 or a 400 about the request, would refuse every
    # session alike: keep them all and say so, rather than holding each one.
    return STOP, f"refused: {status} {code}; check the url and collections in {config_path()}".strip()


def run(settings: Settings, sources: list, state_dir: Path, log: Log) -> dict:
    """Spool what changed, then send what the spool holds, within the run's budget."""
    state = load_state(state_dir, settings)
    enqueue(state_dir, state, settings, sources)
    _write_json(state_dir / "state.json", state)
    spool = state_dir / "spool"
    entries = []
    for path in sorted(spool.glob("*.json")) if spool.is_dir() else []:
        entry = _read_json(path)
        if entry and entry.get("path") and entry.get("format") in settings.collections:
            entries.append((path, entry))
    summary = {"sent": 0, "held": 0, "waiting": 0}
    if not entries:
        return summary
    # Oldest first, but an entry that keeps failing goes behind the rest, so one
    # session the server cannot take (too large, too slow) does not block the others.
    entries.sort(key=lambda item: (item[1].get("attempts") or 0, item[1].get("mtime_ns") or 0))
    pending = [(p, e) for p, e in entries if not e.get("held")]
    for path, entry in entries:
        if entry.get("held"):
            summary["held"] += 1
            log(f"memoria: NEEDS ATTENTION {entry['format']} session {entry['session_id']}: {entry['held']}. "
                f"Not sent again until its transcript changes; the entry is {path}")
    if not pending:
        return summary
    try:
        key = resolve_key(settings)
    except CredentialError as error:
        summary["waiting"] = len(pending)
        log(f"memoria: {error}; {len(pending)} session(s) wait in the spool")
        _keep_copies(settings, pending, log)
        return summary
    deadline = time.monotonic() + settings.budget
    for index, (path, entry) in enumerate(pending):
        if time.monotonic() > deadline:
            summary["waiting"] += len(pending) - index
            log(f"memoria: run budget spent; {len(pending) - index} session(s) wait for the next run")
            _keep_copies(settings, pending[index:], log)
            break
        outcome = _send_entry(settings, key, path, entry, state, log)
        if outcome == DONE:
            summary["sent"] += 1
        elif outcome == HOLD:
            summary["held"] += 1
        else:
            summary["waiting"] += 1
        if outcome == STOP:
            summary["waiting"] += len(pending) - index - 1
            _keep_copies(settings, pending[index + 1:], log)
            break
    _write_json(state_dir / "state.json", state)
    log("memoria: " + json.dumps(summary))
    return summary


def _keep_copies(settings: Settings, entries: list, log: Log) -> None:
    """Copy each untried transcript beside its entry, once per version, so a
    transcript cleaned up during a long outage can still be sent later. One too
    large to send is not copied: it will be held, so a copy would only fill the disk."""
    for path, entry in entries:
        snapshot = entry.get("snapshot") or {}
        if [snapshot.get("size"), snapshot.get("mtime_ns")] == [entry.get("size"), entry.get("mtime_ns")]:
            continue
        if too_large(settings, entry):
            continue
        try:
            read = _read_body({**entry, "snapshot": None}, path.with_suffix(".jsonl"))
            if read is None or not read[0]:
                continue
            body, size, mtime_ns, _ = read
            _atomic_write(path.with_suffix(".jsonl"), body)
            entry["snapshot"] = {"size": size, "mtime_ns": mtime_ns}
            _write_json(path, entry)
        except OSError as error:
            log(f"memoria: could not keep a copy of {entry['format']} session {entry['session_id']}: {error}")


def _send_entry(settings: Settings, key: str, path: Path, entry: dict, state: dict, log: Log) -> str:
    label = f"{entry['format']} session {entry['session_id']}"
    snapshot_path = path.with_suffix(".jsonl")
    oversized = too_large(settings, entry)
    if oversized:
        entry["held"] = entry["last_error"] = oversized
        _write_json(path, entry)
        log(f"memoria: NEEDS ATTENTION {label}: {oversized}. Kept in the spool at {path}")
        return HOLD
    read = _read_body(entry, snapshot_path)
    if read is None:
        entry["held"] = "its transcript is gone and no copy was kept"
        _write_json(path, entry)
        log(f"memoria: NEEDS ATTENTION {label}: {entry['held']}")
        return HOLD
    body, size, mtime_ns, from_snapshot = read
    if not body:
        return RETRY  # nothing complete to send yet
    if entry["format"] == "claude" and b'"cwd"' not in body[:CWD_PROBE_BYTES]:
        log(f"memoria: {label} has no cwd, so the server cannot match its project folder; "
            "it will be stored beside any migrated export of it")
    outcome, reason = classify(send(settings, key, entry, body, mtime_ns))
    if outcome == DONE:
        state["sent"][entry["path"]] = [size, mtime_ns]
        path.unlink(missing_ok=True)
        snapshot_path.unlink(missing_ok=True)
        log(f"memoria: sent {label}: {reason}")
        return DONE
    entry["last_error"] = reason
    if outcome == HOLD:
        entry["held"] = reason
        log(f"memoria: NEEDS ATTENTION {label}: {reason}. Kept in the spool at {path}")
    else:
        entry["attempts"] = entry.get("attempts", 0) + 1
        if not from_snapshot:  # keep a copy, in case the transcript is cleaned up before the next try
            _atomic_write(snapshot_path, body)
            entry["snapshot"] = {"size": size, "mtime_ns": mtime_ns}
        log(f"memoria: kept {label} for the next run: {reason}")
    _write_json(path, entry)
    return outcome
