---
name: recall
description: Search and visualize past Claude Code and Codex session history by date, topic, project, branch, or files touched.
---

# Session recall

Search Claude exports under `~/.claude/obsidian/sessions` and Codex exports under `~/.agent-history/codex-sessions`. The export helper refreshes both without modifying either product's source transcripts.

Codex exports refresh incrementally after every completed turn, compaction, subagent, and session.
The exporter preserves every persisted user/assistant message from the append-only rollout in
deterministic, bounded chunks, so context compaction does not replace the searchable transcript and
QMD only re-embeds the final/new chunk as a conversation grows. Forks and subagents remain separate
documents with `root_thread_id`, `parent_thread_id`, and `forked_from_id` metadata instead of
duplicating ancestor text. Concurrent refreshes coalesce and QMD work is skipped when nothing changed.

If exports are missing or stale, run `python scripts/export_sessions.py` from this skill directory.
Use `--verify` to compare every source transcript with its export and `--verify-qmd` to confirm index
coverage. Do not read authentication files or modify product databases. For semantic search, use the
`Claude-sessions` and `Codex-sessions` QMD collections together.

## Export guarantees and limits

- Every persisted, non-empty `response_item` message with role `user` or `assistant` is exported in
  source order. Each bounded chunk carries its source message range, count, turn IDs, and SHA-256
  digest; `--verify` also compares the exact rendered bytes against the source.
- Indexed chunks contain only stable lineage and chunk-local metadata. Session-global counters stay
  in the incremental state cache so later compactions or tool calls never rewrite earlier chunks.
- Auto-compaction is append-only in Codex rollouts. Original visible messages remain exportable;
  encrypted compaction state is intentionally opaque and is not treated as transcript text.
- Resumed root threads update the same document. Forks and subagents use separate documents linked
  to their root and parent thread IDs, ensuring each persisted message is indexed once. Active and
  archived rollout directories are both included.
- Stop-family hooks launch the refresh asynchronously. A crash before a hook or during QMD work is
  recovered by the next trigger; exports and the index are therefore eventually consistent, not
  transactionally simultaneous with the Codex UI.

## Temporal mode

Resolve the requested date or range using the current timezone. Search matching files, read frontmatter plus the opening user request, and return a compact table with date, agent, project, branch, and summary. Offer to open the most relevant full sessions.

## Topic mode

Prefer an available semantic-search connector when it indexes the shared session collection. Otherwise use `rg` across exported Markdown, rank by meaningful match count and recency, and inspect context around the strongest hits.

Avoid searching only for a skill name because embedded skill instructions can outrank real usage. Search symptoms, decisions, errors, filenames, and domain terms. Report paths and short paraphrased excerpts.

## Graph mode

For a requested project or time range, read exported frontmatter and build a session-to-file graph using `references/graph-template.html`. Write the generated HTML to `~/.agent-history/graph.html` and open it with the platform's normal browser command. Report session and file counts.

## Export format

Each session file should include `session_id`, `agent`, `date`, `start_time`, `end_time`, `project`, `git_branch`, and `files_touched` when the source exposes them. Missing metadata is acceptable; never invent it.

Treat transcript formats as unstable. When a source record cannot be parsed, skip it with a diagnostic rather than corrupting existing exports.
