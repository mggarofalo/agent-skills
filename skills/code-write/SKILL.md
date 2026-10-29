---
name: code-write
description: >
  Generate a new file with a low-cost, stateless worker when an exact neighboring reference
  file exists. Use for repetitive or pattern-matching code generation, never for debugging,
  architecture, safety-critical logic, or editing an existing file.
allowed-tools: Bash, Read
---

# Code write

This mode writes straight to disk. Before invoking it:

- Confirm the output path does not already exist.
- Choose one required reference file that demonstrates the exact local pattern.
- Put all behavioral requirements in the specification.

Then run:

```bash
python3 ~/.claude/agent-router/code_write.py --host claude --output <output> --reference <reference> --spec "<requirements>"
```

The worker has no tools and no resumable session. It returns only file contents; the script
strips a single accidental fence and atomically writes the result. Review or test the result
with the frontier model. Do not use this mode to modify an existing file.
