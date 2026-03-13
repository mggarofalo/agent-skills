#!/usr/bin/env python3
"""Create a new Plane issue with markdown description."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plane_helpers import parse_json_output, require_project, run_plane


def resolve_label_ids(project: str, label_names: list[str]) -> list[str]:
    """Look up label IDs by name from the project's label list."""
    result = run_plane("label", "list", "-p", project, "-o", "json")
    labels = parse_json_output(result.stdout)
    if not isinstance(labels, list):
        labels = labels.get("results", []) if isinstance(labels, dict) else []

    name_to_id: dict[str, str] = {}
    for label in labels:
        if isinstance(label, dict):
            name_to_id[label.get("name", "").lower()] = label.get("id", "")

    ids: list[str] = []
    for name in label_names:
        lid = name_to_id.get(name.lower())
        if lid:
            ids.append(lid)
        else:
            print(f"Warning: Label '{name}' not found in project {project}. Skipping.", file=sys.stderr)

    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new Plane issue with markdown description.")
    parser.add_argument("--name", required=True, help="Issue title")
    parser.add_argument("--description", default="", help="Markdown description")
    parser.add_argument("--priority", default="medium", choices=["none", "urgent", "high", "medium", "low"], help="Priority (default: medium)")
    parser.add_argument("--state", default="Backlog", help='State name (default: "Backlog")')
    parser.add_argument("--labels", default="", help="Comma-separated label names")
    parser.add_argument("-p", "--project", help="Project identifier (auto-detected from docs/plane.md if omitted)")
    args = parser.parse_args()

    project = require_project(args.project)

    cmd: list[str] = [
        "issue", "create",
        "-p", project,
        "--name", args.name,
        "--priority", args.priority,
        "--state", args.state,
        "-o", "json",
    ]

    if args.description:
        cmd.extend(["--description", args.description])

    if args.labels:
        label_names = [l.strip() for l in args.labels.split(",") if l.strip()]
        if label_names:
            label_ids = resolve_label_ids(project, label_names)
            if label_ids:
                cmd.extend(["--labels", ",".join(label_ids)])

    result = run_plane(*cmd)
    data = parse_json_output(result.stdout)

    issue = data if isinstance(data, dict) else data[0] if data else {}
    seq_id = issue.get("sequence_id", issue.get("identifier", "unknown"))
    uuid = issue.get("id", "unknown")
    project_identifier = issue.get("project_detail", {}).get("identifier", project) if isinstance(issue.get("project_detail"), dict) else project

    # Build sequence display from project identifier + sequence_id
    if isinstance(seq_id, int):
        display_id = f"{project_identifier}-{seq_id}"
    else:
        display_id = str(seq_id)

    print(f"Created {display_id}: {args.name}")
    print(f"UUID: {uuid}")


if __name__ == "__main__":
    main()
