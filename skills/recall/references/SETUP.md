# Recall Skill — One-Time Setup

## 1. Export Sessions

Run the export script to convert JSONL session files to searchable markdown:

```bash
python3 ~/.claude/skills/recall/export_sessions.py -v
```

This creates markdown files in `~/.claude/obsidian/sessions/`, one per session.
Re-run after new sessions to incrementally export new/changed ones (idempotent).

## 2. Install QMD

[QMD](https://github.com/tobilu/qmd) is a local search engine that provides BM25 + semantic search over markdown files.

```bash
npm install -g @tobilu/qmd
```

## 3. Create QMD Collection

```bash
qmd collection add ~/.claude/obsidian/sessions --name Claude-sessions
```

Codex exports (`~/.agent-history/codex-sessions`) live in a separate `Codex-sessions` collection, created by the Codex-side recall setup. Topic mode searches both. Confirm with `qmd collection list`.

## 4. Build Embeddings

```bash
qmd embed
```

This generates vector embeddings for semantic search. Re-run after each export to index new sessions.

## 5. Configure MCP Server

Register QMD as a user-scope MCP server (stored in `~/.claude.json`, not `settings.json`):

```bash
claude mcp add --scope user qmd -- qmd mcp
```

## 6. Verify

Restart Claude Code and confirm QMD tools are available (they may be deferred — load with ToolSearch):
- `mcp__qmd__query` — typed `lex` / `vec` / `hyde` sub-queries across collections
- `mcp__qmd__get` / `mcp__qmd__multi_get` — read documents around a hit
- `mcp__qmd__status` — index health

## Maintenance

After new sessions accumulate, re-export and re-embed:

```bash
python3 ~/.claude/skills/recall/export_sessions.py -v
qmd embed
```

## Hosted mode (Memoria)

Hosted mode searches a [Memoria](https://github.com/mggarofalo/memoria) server instead of local QMD, and has the session-end hooks send transcripts to it. It is off until you turn it on, and local QMD stays the default. Without the config file below, nothing changes: the hooks do not read their input, open a connection or write anything new.

### What you need

- **The `memoria` CLI on your PATH**, logged in: `memoria auth login --api-url https://memoria.example.com`. Search needs a key with the `read` scope and push needs `ingest`, each for the collections below.
- **The collections opened to ingest** on the server, empty when ingest first uses them.
- **History moved first.** Push sends only sessions that change after you turn it on. Older ones are for `memoria migrate`, as Memoria's `docs/migration.md` describes.

### Turn it on

Write `~/.config/agent-skills/memoria.json` (under `$XDG_CONFIG_HOME` if that is set; `AGENT_SKILLS_MEMORIA_CONFIG` names another file):

```json
{
  "url": "https://memoria.example.com",
  "push": true,
  "search": "memoria",
  "since": "2026-11-01T00:00:00Z"
}
```

| Field | Default | Meaning |
|---|---|---|
| `push` | off | `true` sends transcripts at session end. Any other value is off. |
| `search` | `qmd` | `"memoria"` makes `/recall topic` search the server. |
| `url` | the CLI profile's server | The server. Plain http is refused except to loopback or a private address, as the CLI does; `allow_insecure_http: true` overrides that. |
| `profile` | `MEMORIA_PROFILE`, then the CLI's active profile, then `default` | The CLI profile whose keyring login is used. |
| `collections` | `{"claude": "claude-sessions", "codex": "codex-sessions"}` | Where each harness's sessions go and are searched. A second machine can use its own. |
| `since` | when this file was first seen with `push` on | Transcripts last changed before this are not sent. Set it to the time of your last `memoria migrate push`, so nothing changed since then is missed. |
| `timeout` | `60` | Seconds allowed for one upload. |
| `budget` | `300` | Seconds one run may spend sending. The rest wait for the next run. |
| `max_session_bytes` | `268435456` (256 MiB) | The server's `Memoria:Ingest:MaxSessionBytes`. A transcript larger than this is held, not sent. Set it to the server's value if that is higher. |
| `cli` | `memoria` on PATH | The CLI recall runs. |

`push` and `search` are separate, so you can send for a while before you search there.

### What push does

- **At `SessionEnd` only**, in the hook's detached worker, after the local export and before the QMD refresh. The hook itself still returns at once. The local export and QMD keep working, so local QMD stays a way back.
- **Raw transcripts**, to `POST /v1/ingest/session`: Claude Code with `format=claude`, its `sessionId` and `projectDirectory`; Codex rollouts with `format=codex`. The server renders and redacts them. Nothing is sent anywhere but `url`.
- **Re-sending replaces.** The server knows a session by its id and project folder, and orders copies by `updated`, the transcript's modification time. A session that grows is sent again in full and replaces what was stored.
- **The key** is `MEMORIA_API_KEY`, or else the CLI's keyring login for the profile, read from Credential Manager, the macOS Keychain or the Secret Service. A keyring key is sent only to the server it was saved for. The CLI's unencrypted file backend is not read.

### The spool

Each changed transcript gets one entry in `~/.claude/memoria-push/spool/` (Codex: `~/.codex/memoria-push/spool/`), keyed by its path, so a session changed twice is still one entry. An entry leaves only when the server accepts it.

- **Server unreachable, busy, rate limiting or refusing the key:** the run stops, keeps every entry, and keeps a copy of the transcript beside its entry in case the original is cleaned up. The next session end tries again.
- **A refusal sending again cannot fix,** such as 409 `session_shrank` or `path_owned`, or a body too large: the entry is held, not dropped. Every run logs it as `NEEDS ATTENTION` until the transcript changes, which sends it again, or you delete the entry yourself. Memoria's `docs/migration.md` says what each of these means.
- **A transcript over `max_session_bytes`** is held the same way before anything is read or sent, and no copy of it is kept. The server would refuse it whole, and sending it anyway can end in a broken connection, which would read as an outage and be tried on every run. It stays local, as the only copy. Raising the server's limit, and `max_session_bytes` with it, lets it go on the next run, even if the transcript has not changed. The size checked is the whole file's, so one that ends in half a line can be held a little before the server's limit.

Everything is logged with a `memoria:` prefix in `~/.claude/logs/session-end-export.log` (Codex: `~/.codex/logs/session-end-export.log`).

### Turn it off

Set `push` to `false`, or `search` to `qmd`, or delete the file. Entries left in the spool are sent when push is turned back on.
