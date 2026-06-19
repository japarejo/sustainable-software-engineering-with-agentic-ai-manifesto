#!/usr/bin/env python3
"""Recount signatories in SIGNATORIES.md and (re)write the badge JSON files.

Robust against CRLF line endings and empty placeholder rows. Used by both the
push-triggered badge workflow and the auto-signing workflow.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SIGNATORIES = Path("SIGNATORIES.md")

INDIVIDUAL_HEADING = "# 👤 Individual Signatories"
ORGANIZATION_HEADING = "# 🏢 Organizational Signatories"

SEPARATOR_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")


def cells(row: str) -> list[str]:
    """Split a markdown table row into trimmed cell values."""
    parts = row.split("|")
    # Drop the empty strings produced before the first and after the last pipe.
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def count_after_heading(lines: list[str], heading: str, name_col: int) -> int:
    """Count non-empty data rows of the first markdown table after `heading`.

    `name_col` is the 0-based index of the column that must be non-empty for a
    row to count (the Name / Organization column).
    """
    in_section = False
    in_table = False
    header_seen = False
    count = 0
    for raw in lines:
        line = raw.rstrip("\r")
        if not in_section:
            if line.strip() == heading:
                in_section = True
            continue
        stripped = line.strip()
        if not in_table:
            if stripped.startswith("|"):
                in_table = True
            else:
                continue
        # Inside the table now.
        if not stripped.startswith("|"):
            break  # table ended (blank line, comment marker, next heading, ...)
        if SEPARATOR_RE.match(stripped):
            continue
        if not header_seen:
            header_seen = True  # first non-separator row is the header
            continue
        values = cells(stripped)
        if len(values) <= name_col:
            continue
        if values[name_col] == "":
            continue
        count += 1
    return count


def main() -> int:
    text = SIGNATORIES.read_text(encoding="utf-8")
    lines = text.split("\n")

    individuals = count_after_heading(lines, INDIVIDUAL_HEADING, name_col=1)
    organizations = count_after_heading(lines, ORGANIZATION_HEADING, name_col=1)
    total = individuals + organizations

    badges = {
        "signatories-individuals.json": {
            "label": "Individuals",
            "message": str(individuals),
            "color": "blue",
        },
        "signatories-organizations.json": {
            "label": "Organizations",
            "message": str(organizations),
            "color": "blue",
        },
        "signatories-total.json": {
            "label": "Signatories",
            "message": str(total),
            "color": "blue",
        },
    }
    for filename, payload in badges.items():
        Path(filename).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    print(f"individuals={individuals} organizations={organizations} total={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
