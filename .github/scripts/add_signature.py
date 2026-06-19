#!/usr/bin/env python3
"""Parse a Signature Request issue form and append the signatory to SIGNATORIES.md.

Reads the issue body from the ISSUE_BODY environment variable (passed safely as
an env var to avoid shell injection) and writes the outcome to GITHUB_OUTPUT so
the workflow can comment on / close the issue.

Outputs:
  status     = added | invalid
  category   = individual | organization | ""
  name       = signatory name (for the thank-you comment)
  number     = assigned signature number
  reason     = human-readable reason when status=invalid
"""
from __future__ import annotations

import datetime as _dt
import os
import re
from pathlib import Path

SIGNATORIES = Path("SIGNATORIES.md")

INDIVIDUAL_MARKER = "<!-- INDIVIDUAL_SIGNATORIES_END -->"
ORGANIZATION_MARKER = "<!-- ORGANIZATION_SIGNATORIES_END -->"

NO_RESPONSE = "_No response_"
HEADING_RE = re.compile(r"^###\s+(.*\S)\s*$")
SEPARATOR_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")


def parse_issue_body(body: str) -> dict[str, str]:
    """Turn a GitHub issue-form body into a {label: value} mapping."""
    fields: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current is not None:
            value = "\n".join(buffer).strip()
            fields[current] = value

    for raw in body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        m = HEADING_RE.match(raw)
        if m:
            flush()
            current = m.group(1).strip()
            buffer = []
        else:
            buffer.append(raw)
    flush()
    return fields


def clean(value: str) -> str:
    """Normalise a field value for safe insertion into a markdown table cell."""
    if value is None:
        return ""
    value = value.strip()
    if value == NO_RESPONSE:
        return ""
    # Collapse newlines and escape pipes so the table is not broken.
    value = " ".join(value.split())
    value = value.replace("|", r"\|")
    return value


def count_rows_before_marker(lines: list[str], marker: str) -> int:
    """Count existing data rows of the table that ends at `marker`."""
    try:
        marker_idx = next(i for i, l in enumerate(lines) if l.strip() == marker)
    except StopIteration:
        raise SystemExit(f"Insertion marker not found: {marker}")
    count = 0
    header_seen = False
    for line in lines[:marker_idx]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            # Reset on each non-table block so we only count the last table.
            header_seen = False
            count = 0
            continue
        if SEPARATOR_RE.match(stripped):
            continue
        if not header_seen:
            header_seen = True
            continue
        count += 1
    return count, marker_idx


def write_output(**kwargs: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    payload = "".join(f"{k}={v}\n" for k, v in kwargs.items())
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(payload)
    print(payload, end="")


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    today = os.environ.get("SIGN_DATE") or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")

    fields = parse_issue_body(body)

    name = clean(fields.get("Full Name", ""))
    role = clean(fields.get("Role / Title", ""))
    affiliation = clean(fields.get("Affiliation", ""))
    country = clean(fields.get("Country", ""))
    signing_as = clean(fields.get("Signing As", ""))
    org_name = clean(fields.get("Organization name (only if signing as an organization)", ""))

    if not name:
        write_output(status="invalid", category="", name="", number="",
                     reason="Full Name is missing — please resubmit the form with your name.")
        return 0

    is_org = signing_as.lower().startswith("organization")

    text = SIGNATORIES.read_text(encoding="utf-8")
    lines = text.split("\n")

    if is_org:
        organization = org_name or affiliation
        if not organization:
            write_output(status="invalid", category="organization", name=name, number="",
                         reason="Organization name is missing — please add it and resubmit.")
            return 0
        existing, marker_idx = count_rows_before_marker(lines, ORGANIZATION_MARKER)
        number = existing + 1
        representative = name if not role else f"{name} ({role})"
        row = f"| {number} | {organization} | Organization | {country} | {representative} | {today} |"
        category = "organization"
    else:
        existing, marker_idx = count_rows_before_marker(lines, INDIVIDUAL_MARKER)
        number = existing + 1
        row = f"| {number} | {name} | {role} | {affiliation} | {country} | {today} |"
        category = "individual"

    lines.insert(marker_idx, row)
    SIGNATORIES.write_text("\n".join(lines), encoding="utf-8")

    write_output(status="added", category=category, name=name, number=str(number), reason="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
