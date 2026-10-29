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
