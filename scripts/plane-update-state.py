#!/usr/bin/env python3
"""Update a Plane issue's state by name."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plane_helpers import require_project, run_plane


def main() -> None:
    parser = argparse.ArgumentParser(description="Update a Plane issue's state by name.")
    parser.add_argument("uuid", help="Issue UUID")
    parser.add_argument("state", help='State name (e.g., "Done", "In Progress")')
    parser.add_argument("-p", "--project", help="Project identifier (auto-detected from docs/plane.md if omitted)")
    args = parser.parse_args()

    project = require_project(args.project)

    run_plane(
        "issue", "update",
        "--work-item-id", args.uuid,
        "-p", project,
        "--state", args.state,
    )

    print(f"Updated {args.uuid} → {args.state}")


if __name__ == "__main__":
    main()
