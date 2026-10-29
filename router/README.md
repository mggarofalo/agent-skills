# Low-cost worker router

Shared implementation for the Claude Code and Codex `bulk-read` and `code-write` workflows.

- `read_guard.py` is the enforced `PreToolUse` layer. It blocks unbounded reads of files over
  350 lines and returns an exact `bulk_read.py` command.
- `bulk_read.py` numbers and tags file contents, sends the question and files to a low-cost
  worker, and accepts only `path:line` bullets.
- `code_write.py` requires a specification and reference file, accepts only file content, and
  atomically creates a new output file.
- `worker.py` contains the host adapters. Claude runs Haiku with tools disabled and local
  session persistence off. Codex runs Luna at low effort in an ephemeral read-only session.

The scripts do not write delegated inputs to disk or create resumable local worker sessions.
They still send those inputs to the selected model provider, whose service-side retention is
governed by the account's applicable data controls.

Environment overrides:

| Variable | Default |
|---|---|
| `AGENT_ROUTER_LINE_THRESHOLD` | `350` |
| `AGENT_ROUTER_MAX_INPUT_BYTES` | `8388608` |
| `AGENT_ROUTER_CLAUDE_MODEL` | `haiku` |
| `AGENT_ROUTER_CODEX_MODEL` | `gpt-5.6-luna` |
