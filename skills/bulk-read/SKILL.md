---
name: bulk-read
description: >
  Delegate mechanical reading of files larger than 350 lines to a low-cost, stateless
  worker and return only source-located bullets. Use when a Read or shell file read is
  blocked by the large-file router, or when summarizing/searching one or more large files.
allowed-tools: Bash
---

# Bulk read

Run the router with the exact question and literal file paths:

```bash
python3 ~/.claude/agent-router/bulk_read.py --host claude --question "<question>" -- <file> [file ...]
```

Use the returned `path:line` bullets as context. Do not read the whole files again. A targeted
`Read` is allowed when reasoning or an edit requires an exact section; always supply both
`offset` and a `limit` no greater than 350.

Split inputs across calls if the script reports that the 8 MiB request cap was exceeded.
