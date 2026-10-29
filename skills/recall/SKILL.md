---
name: recall
description: Search and visualize past Claude Code and Codex session history. Three modes — temporal (browse by date), topic (semantic search), graph (visual map).
allowed-tools: Read, Glob, Grep, Bash, Write, WebFetch
user-invocable: true
argument-hint: "<mode> [query]  — modes: temporal, topic, graph"
---

# Session Recall

You help the user search and explore their past agent session history. Sessions are exported to markdown with YAML frontmatter:

- **Claude Code**: `~/.claude/obsidian/sessions/` (QMD collection `Claude-sessions`), ~64K-char chunks: `YYYY-MM-DD_<id8>.md`, then `YYYY-MM-DD_<id8>_part-NNN.md` — group chunks by `session_id`
- **Codex**: `~/.agent-history/codex-sessions/` (QMD collection `Codex-sessions`), bounded chunks named `YYYY-MM-DD_codex_<session-id>_chunk-NNNNN.md` with `agent: "codex"` — group chunks by `session_id`

Always say which harness (Claude / Codex) each result came from.

Parse the user's `/recall` invocation to determine the mode and query, then execute accordingly.

---

## Mode 1: Temporal — `/recall temporal <date-range>`

Browse sessions by date. The query is a natural language time reference.

### Steps

1. **Parse the date range** from the query:
   - "today" → today's date
   - "yesterday" → yesterday's date
   - "last week" → 7 days back from today
   - "last month" → 30 days back from today
   - "March 5" or "2026-03-05" → specific date
   - "March 1-7" → explicit range

2. **Glob session files** matching the date prefix pattern in both export dirs:
   ```
   ~/.claude/obsidian/sessions/YYYY-MM-DD_*.md
   ~/.agent-history/codex-sessions/YYYY-MM-DD_*.md
   ```
   For ranges, glob each date or use a broader pattern and filter.

3. **Read frontmatter** from each matching file. Extract: `date`, `project`, `git_branch`, `slug`, `files_touched`.

4. **Read the first `## User` section** from each file to generate a one-line summary (first 120 chars of the user's opening message).

5. **Present results as a table**:

   | Date | Agent | Project | Branch | Summary |
   |------|-------|---------|--------|---------|
   | 2026-03-05 | Claude | Receipts | feat/auth | Implement authentication flow... |

   Missing metadata (e.g. Codex chunks often have an empty `git_branch` and no `files_touched`) is fine — leave the cell blank; never invent it.

   If many sessions, group by date with counts.

6. **Offer to dive deeper**: "Want me to read the full conversation from any of these sessions?"

---

## Mode 2: Topic — `/recall topic <query>`

Semantic search across session content. Requires QMD MCP server.

### Steps

1. **Check if QMD tools are available** — look for `mcp__qmd__query`, `mcp__qmd__get`, `mcp__qmd__multi_get`, and `mcp__qmd__status`. These are MCP tools and may be **deferred**: if you see the names listed but cannot call them, load their schemas first with a single `ToolSearch` call:
   ```
   ToolSearch query: "select:mcp__qmd__query,mcp__qmd__get,mcp__qmd__multi_get,mcp__qmd__status"
   ```
   Deferred-but-loadable counts as available. Do not fall back to Grep just because the schemas were not loaded yet.

2. **If QMD is available**: call `mcp__qmd__query`. It takes typed sub-queries, not a plain query string:
   - `searches`: an array of `{type, query}` objects. `lex` is BM25 keyword matching (supports `"quoted phrases"` and `-negation`), `vec` is semantic, `hyde` is a hypothetical answer passage. The **first sub-query carries 2× weight**, so lead with your strongest signal.
   - `collections`: `["Claude-sessions", "Codex-sessions"]` by default — note the plural; it is an array, and names are case-sensitive. Narrow to one only when the user asks about a single harness.
   - `intent`: one line of context disambiguating the search. Always pass this.
   - `limit` / `minScore`: optional. `minScore: 0.5` filters weak hits.

   For best recall, combine a `lex` and a `vec` sub-query:
   ```json
   {
     "searches": [
       {"type": "lex", "query": "\"connection pool\" timeout -redis"},
       {"type": "vec", "query": "why do database connections time out under load"}
     ],
     "collections": ["Claude-sessions", "Codex-sessions"],
     "intent": "debugging DB connection exhaustion in the Receipts API"
   }
   ```

   Each result carries a `line` field pointing at the best match. To read context around a hit, call `mcp__qmd__get` with `fromLine` set to roughly 20 lines before it.

   **Caveat on transcript search:** sessions embed the full text of any skill they invoked (and Codex sessions embed `AGENTS.md`), so a query naming a skill will rank that boilerplate above real usage. Search for errors, decisions, filenames, and domain terms rather than skill or tool names.

   Present results with:
   - Harness (Claude / Codex, from the collection or `agent` field)
   - Session date and project
   - Relevance score
   - Key excerpt (the matched passage)
   - File path for the user to reference

3. **If QMD MCP is NOT available**: if the `qmd` CLI is installed, use `qmd query "<query>" -c Claude-sessions -c Codex-sessions`. Otherwise fall back to Grep-based search:
   - `Grep` for the query terms across `~/.claude/obsidian/sessions/*.md` and `~/.agent-history/codex-sessions/*.md`
   - Read frontmatter from matching files for metadata
   - Present results sorted by match count (most relevant first)

4. **Present as a ranked list**:
   ```
   1. **Receipts** (2026-03-05, Claude) — branch: feat/auth
      > "...implementing the authentication middleware with JWT tokens..."

   2. **ReceiptSync** (2026-03-02, Codex) — branch: main
      > "...auth token refresh logic in the sync service..."
   ```

5. **Offer follow-up**: "Want me to read the full session for any of these?"

---

## Mode 3: Graph — `/recall graph [query]`

Generate an interactive force-directed graph visualization of sessions and the files they touched.

### Steps

1. **Determine scope**:
   - `/recall graph` → all sessions
   - `/recall graph <project>` → filter to that project
   - `/recall graph last month` → filter by time range

2. **Scan session frontmatter** from `~/.claude/obsidian/sessions/*.md` (Codex exports carry no `files_touched`, so they add no file edges):
   - For each session, extract: `session_id`, `date`, `project`, `git_branch`, `slug`, `files_touched` (any may be missing or empty — skip, don't invent)
   - Apply any project/time filters

3. **Build graph data**:
   ```python
   nodes = []
   links = []
   file_nodes = {}  # deduplicate files across sessions

   for session in sessions:
       # Session node
       nodes.append({
           "id": f"s_{session_id_short}",
           "type": "session",
           "label": f"{project} {date}",
           "date": date,
           "project": project,
           "branch": branch,
           "slug": slug
       })

       # File nodes + edges
       for filepath in files_touched:
           file_id = f"f_{hash(filepath)}"
           if file_id not in file_nodes:
               file_nodes[file_id] = {
                   "id": file_id,
                   "type": "file",
                   "label": basename(filepath)
               }
           links.append({"source": session_node_id, "target": file_id})
   ```

4. **Read the graph template** from `~/.claude/skills/recall/references/graph-template.html`.

5. **Inject data** by replacing the `/* DATA_PLACEHOLDER */` marker:
   ```
   const DATA = /* DATA_PLACEHOLDER */ { nodes: [...], links: [...] } /* END_DATA */;
   ```
   Replace everything between `/* DATA_PLACEHOLDER */` and `/* END_DATA */` (inclusive of the markers) with the JSON data object.

6. **Write the HTML** to a temp file:
   ```
   ~/.claude/obsidian/graph.html
   ```

7. **Open in browser**:
   ```bash
   open ~/.claude/obsidian/graph.html    # macOS; xdg-open on Linux
   ```

8. **Report to user**: "Graph opened in browser with X sessions and Y files. Use the project and time filters in the top-left to explore."

---

## No-Mode / Help

If the user just says `/recall` without a mode, briefly describe the three modes and ask which they want:

> **Recall — search your Claude Code and Codex session history**
>
> - `/recall temporal last week` — browse sessions by date
> - `/recall topic authentication` — semantic search across sessions
> - `/recall graph` — visual map of sessions and files
>
> Which mode would you like?

---

## Prerequisites

- **Export script**: Sessions must be exported first. If `~/.claude/obsidian/sessions/` is empty or doesn't exist, tell the user:
  > "No exported sessions found. Run the export first:
  > ```bash
  > python3 ~/.claude/skills/recall/export_sessions.py -v
  > ```"

  Codex exports under `~/.agent-history/codex-sessions/` are refreshed by the Codex-side exporter (`codex/skills/recall/scripts/export_sessions.py` in the agent-skills repo), not by this script.

- **QMD** (topic mode only): If QMD tools aren't available, fall back to the `qmd` CLI, then Grep. Mention that QMD enables better semantic search — see `~/.claude/skills/recall/references/SETUP.md`.

---

## YAML Frontmatter Reference

Each exported Claude chunk has this frontmatter, plus `chunk_index`, `message_start` and `message_count`. `start_time`/`end_time` and `files_touched` cover only that chunk; union them across a session's chunks (Codex chunks add `agent`, `cwd`, lineage IDs, and chunk ranges, and omit `slug`/`files_touched`). Any field may be empty when the source lacked it:

```yaml
---
session_id: "uuid"
slug: "adjective-verbing-noun"
date: "YYYY-MM-DD"
start_time: "ISO-8601"
end_time: "ISO-8601"
project: "ProjectName"
git_branch: "branch-name"
files_touched:
  - "path/to/file.cs"
tags:
  - "project/ProjectName"
  - "branch/branch-name"
---
```
