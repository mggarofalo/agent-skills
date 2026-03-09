# Recall Skill — One-Time Setup

## 1. Export Sessions

Run the export script to convert JSONL session files to searchable markdown:

```bash
python ~/Source/agent-skills/skills/recall/export_sessions.py -v
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
qmd collection add ~/.claude/obsidian/sessions --name claude-sessions
```

## 4. Build Embeddings

```bash
qmd embed
```

This generates vector embeddings for semantic search. Re-run after each export to index new sessions.

## 5. Configure MCP Server

Add QMD as an MCP server in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp"]
    }
  }
}
```

## 6. Verify

Restart Claude Code and confirm QMD tools are available:
- `qmd_search` — BM25 keyword search
- `qmd_vector_search` — semantic search
- `qmd_deep_search` — hybrid (BM25 + semantic + rerank)

## Maintenance

After new sessions accumulate, re-export and re-embed:

```bash
python ~/Source/agent-skills/skills/recall/export_sessions.py -v
qmd embed
```
