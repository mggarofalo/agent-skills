---
name: recall
description: Search and visualize past Claude Code session history. Three modes — temporal (browse by date), topic (semantic search), graph (visual map).
allowed-tools: Read, Glob, Grep, Bash, Write, WebFetch
user-invocable: true
argument-hint: "<mode> [query]  — modes: temporal, topic, graph"
---

# Session Recall

You help the user search and explore their past Claude Code session history. Sessions have been exported to markdown files at `~/.claude/obsidian/sessions/` with YAML frontmatter containing metadata.

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

2. **Glob session files** matching the date prefix pattern:
   ```
   ~/.claude/obsidian/sessions/YYYY-MM-DD_*.md
   ```
   For ranges, glob each date or use a broader pattern and filter.

3. **Read frontmatter** from each matching file. Extract: `date`, `project`, `git_branch`, `slug`, `files_touched`.

4. **Read the first `## User` section** from each file to generate a one-line summary (first 120 chars of the user's opening message).

5. **Present results as a table**:

   | Date | Project | Branch | Summary |
   |------|---------|--------|---------|
   | 2026-03-05 | Receipts | feat/auth | Implement authentication flow... |

   If many sessions, group by date with counts.

6. **Offer to dive deeper**: "Want me to read the full conversation from any of these sessions?"

---

## Mode 2: Topic — `/recall topic <query>`

Semantic search across session content. Requires QMD MCP server.

### Steps

1. **Check if QMD tools are available** (look for `qmd_search`, `qmd_deep_search`, or `qmd_vector_search` in available tools).

2. **If QMD is available**: Use `qmd_deep_search` with:
   - `query`: the user's search terms
   - `collection`: `claude-sessions` (if the tool supports collection filtering)

   Present results with:
   - Session date and project
   - Relevance score
   - Key excerpt (the matched passage)
   - File path for the user to reference

3. **If QMD is NOT available**: Fall back to Grep-based search:
   - `Grep` for the query terms across `~/.claude/obsidian/sessions/*.md`
   - Read frontmatter from matching files for metadata
   - Present results sorted by match count (most relevant first)

4. **Present as a ranked list**:
   ```
   1. **Receipts** (2026-03-05) — branch: feat/auth
      > "...implementing the authentication middleware with JWT tokens..."

   2. **ReceiptSync** (2026-03-02) — branch: main
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

2. **Scan session frontmatter** from `~/.claude/obsidian/sessions/*.md`:
   - For each session, extract: `session_id`, `date`, `project`, `git_branch`, `slug`, `files_touched`
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

4. **Read the graph template** from `~/Source/agent-skills/skills/recall/references/graph-template.html`.

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
   start ~/.claude/obsidian/graph.html    # Windows
   ```

8. **Report to user**: "Graph opened in browser with X sessions and Y files. Use the project and time filters in the top-left to explore."

---

## No-Mode / Help

If the user just says `/recall` without a mode, briefly describe the three modes and ask which they want:

> **Recall — search your Claude Code session history**
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
  > python ~/Source/agent-skills/skills/recall/export_sessions.py -v
  > ```"

- **QMD** (topic mode only): If QMD tools aren't available, fall back to Grep. Mention that QMD enables better semantic search — see `~/Source/agent-skills/skills/recall/references/SETUP.md`.

---

## YAML Frontmatter Reference

Each exported session markdown file has this frontmatter:

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
