"""Shared utilities for Plane CLI wrapper scripts."""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


def detect_project(cwd: Path | None = None) -> str | None:
    """Read docs/plane.md in cwd to find the project identifier."""
    if cwd is None:
        cwd = Path.cwd()
    plane_md = cwd / "docs" / "plane.md"
    if not plane_md.is_file():
        return None
    text = plane_md.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = re.match(r"^\s*(?:\*\*)?(?:Identifier|Project)(?:\*\*)?:\s*(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip().strip("`")
    return None


def require_project(args_project: str | None, cwd: Path | None = None) -> str:
    """Return the project identifier from args or auto-detect; exit on failure."""
    if args_project:
        return args_project
    project = detect_project(cwd)
    if project is None:
        print(
            "Error: Could not determine project. Provide --project or create docs/plane.md "
            "with an 'Identifier: <ID>' line.",
            file=sys.stderr,
        )
        sys.exit(3)
    return project


def run_plane(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the plane CLI with standard error handling."""
    cmd = ["plane", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print("Error: 'plane' CLI not found. Install it or add it to PATH.", file=sys.stderr)
        sys.exit(2)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "unauthorized" in stderr.lower() or "401" in stderr:
            print(
                f"Error: Authentication failed. Run 'plane auth login' to re-authenticate.\n{stderr}",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"Error: plane {' '.join(args)} failed (exit {result.returncode}):\n{stderr}", file=sys.stderr)
        sys.exit(1)

    return result


class _TextExtractor(HTMLParser):
    """Strip HTML tags, preserving text content."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []

    def handle_data(self, data: str) -> None:
        self._pieces.append(data)

    def get_text(self) -> str:
        return "".join(self._pieces)


def html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    if not html:
        return ""
    extractor = _TextExtractor()
    extractor.feed(html)
    return extractor.get_text().strip()


def parse_acceptance_criteria(html: str) -> list[str]:
    """Extract checklist items from description HTML.

    Looks for patterns like:
    - <li> elements with checkbox-style content
    - Lines starting with '- [ ]' or '- [x]' after HTML stripping
    """
    text = html_to_text(html)
    criteria: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^[-*]\s*\[[ xX]?\]\s*(.+)", line)
        if m:
            criteria.append(m.group(1).strip())
    return criteria


def parse_json_output(text: str) -> dict | list:
    """Parse JSON from plane CLI output, handling potential non-JSON prefix lines."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some CLI versions print status lines before JSON; find the first { or [
        for i, ch in enumerate(text):
            if ch in "{[":
                try:
                    return json.loads(text[i:])
                except json.JSONDecodeError:
                    continue
        print(f"Error: Could not parse JSON from plane output:\n{text[:500]}", file=sys.stderr)
        sys.exit(1)
