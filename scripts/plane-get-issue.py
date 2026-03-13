#!/usr/bin/env python3
"""Fetch a Plane issue by sequence ID and output a formatted summary."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plane_helpers import html_to_text, parse_acceptance_criteria, parse_json_output, require_project, run_plane


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a Plane issue by sequence ID.")
    parser.add_argument("sequence_id", help="Issue sequence ID (e.g., RECEIPTS-370)")
    parser.add_argument("-p", "--project", help="Project identifier (auto-detected from docs/plane.md if omitted)")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    project = require_project(args.project)

    result = run_plane(
        "issue", "get-by-sequence-id",
        "--identifier", args.sequence_id,
        "-p", project,
        "--expand", "state,labels,assignees,project",
        "-o", "json",
    )

    data = parse_json_output(result.stdout)

    if args.json_output:
        print(json.dumps(data, indent=2))
        return

    # Handle both single-issue and list responses
    issue = data if isinstance(data, dict) else data[0] if data else None
    if not issue:
        print(f"Error: No issue found for {args.sequence_id}", file=sys.stderr)
        sys.exit(1)

    uuid = issue.get("id", "unknown")
    title = issue.get("name", "Untitled")
    seq = args.sequence_id

    # State
    state = issue.get("state", {})
    state_name = state.get("name", "Unknown") if isinstance(state, dict) else str(state)

    # Priority
    priority_map = {"urgent": "urgent", "high": "high", "medium": "medium", "low": "low", "none": "none"}
    priority = issue.get("priority", "none")
    if isinstance(priority, int):
        priority = {0: "none", 1: "urgent", 2: "high", 3: "medium", 4: "low"}.get(priority, "none")
    priority = priority_map.get(str(priority).lower(), str(priority))

    # Labels
    labels_data = issue.get("labels", [])
    if isinstance(labels_data, list):
        label_names = [l.get("name", str(l)) if isinstance(l, dict) else str(l) for l in labels_data]
    else:
        label_names = []

    # Assignees
    assignees_data = issue.get("assignees", [])
    if isinstance(assignees_data, list):
        assignee_names = [a.get("display_name", a.get("name", str(a))) if isinstance(a, dict) else str(a) for a in assignees_data]
    else:
        assignee_names = []

    # Output formatted summary
    print(f"UUID: {uuid}")
    print(f"Sequence: {seq}")
    print(f"Title: {title}")
    print(f"State: {state_name}")
    print(f"Priority: {priority}")
    if label_names:
        print(f"Labels: {', '.join(label_names)}")
    if assignee_names:
        print(f"Assignees: {', '.join(assignee_names)}")

    # Description
    desc_html = issue.get("description_html", "")
    desc_text = html_to_text(desc_html) if desc_html else issue.get("description", "")
    if desc_text:
        print(f"\n## Description\n{desc_text}")

    # Acceptance criteria
    if desc_html:
        criteria = parse_acceptance_criteria(desc_html)
        if criteria:
            print("\n## Acceptance Criteria")
            for c in criteria:
                print(f"- [ ] {c}")


if __name__ == "__main__":
    main()
