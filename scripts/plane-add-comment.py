#!/usr/bin/env python3
"""Post a markdown comment on a Plane issue."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plane_helpers import require_project, run_plane


def main() -> None:
    parser = argparse.ArgumentParser(description="Post a markdown comment on a Plane issue.")
    parser.add_argument("uuid", help="Issue UUID")
    parser.add_argument("--body", help="Markdown comment body")
    parser.add_argument("--body-file", help="Read comment body from file instead of --body")
    parser.add_argument("-p", "--project", help="Project identifier (auto-detected from docs/plane.md if omitted)")
    args = parser.parse_args()

    if not args.body and not args.body_file:
        parser.error("Provide either --body or --body-file")

    project = require_project(args.project)

    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.is_file():
            print(f"Error: File not found: {args.body_file}", file=sys.stderr)
            sys.exit(1)
        body = body_path.read_text(encoding="utf-8")
    else:
        body = args.body

    run_plane(
        "comment", "add",
        "--work-item-id", args.uuid,
        "-p", project,
        "--comment", body,
    )

    print(f"Comment added to {args.uuid}")


if __name__ == "__main__":
    main()
