# Codex hooks

These hooks use Codex's native lifecycle schema.

- `block-destructive-ops.py` checks `Bash` and `apply_patch` for destructive operations, protected credential paths, and guardrail self-modification.
- `enforce-worktree-paths.py` prevents `apply_patch` from targeting a primary checkout while Codex is working in another Git worktree.
- `session-end-export.py` refreshes Codex session recall after every completed turn, compaction,
  subagent, and session. Claude uses its own lifecycle hook. Concurrent Codex triggers coalesce
  behind one detached worker, which skips QMD work when no transcript chunk changed and limits
  embedding to the `Codex-sessions` collection.

The source configuration is `../config/hooks.json`. Run `python install-codex.py` from the repository root, then use `/hooks` to review and trust changed definitions.

Session recall uses `Stop` for per-turn freshness, `PostCompact` as a compaction checkpoint,
`SubagentStop` for child-thread coverage, and `SessionEnd` as a final fallback. The hook only launches
a detached worker. A non-blocking file lock coalesces overlapping events, and a pending marker makes
the lock holder run one more pass if another event arrives during export or embedding.

`route-large-reads.py` is the Codex entry point for the shared low-cost worker router. It
intercepts unbounded `cat`, `head`, `tail`, `less`, and `more` calls that would return more
than 350 lines, then denies the call with an exact `bulk_read.py` delegation command. The
cost guard fails open on malformed input; the destructive-operation guard remains authoritative.
