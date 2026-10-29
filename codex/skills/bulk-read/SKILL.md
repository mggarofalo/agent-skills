---
name: bulk-read
description: >
  Delegate mechanical reading of files larger than 350 lines to a low-cost, ephemeral worker
  and return only source-located bullets. Use when a shell file read is blocked by the
  large-file router, or when summarizing or searching one or more large files.
---

# Bulk read

Run the router with the exact question and literal file paths:

```bash
python3 ~/.codex/agent-router/bulk_read.py --host codex --question "<question>" -- <file> [file ...]
```

Use the returned `path:line` bullets as context. Do not read the whole files again. Use a
targeted read of at most 350 lines when reasoning or an edit requires the exact source.

Split inputs across calls if the script reports that the 8 MiB request cap was exceeded.
