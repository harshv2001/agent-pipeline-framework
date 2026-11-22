#!/usr/bin/env python3
"""Regenerate status-report.csv: every source-CSV row, cross-referenced
against the stage-store. Same discipline as
`pipelines/high-intent-csv-to-viksya-insights-blog/tooling/build_status_report.py`
in the private framework this example is modeled on, for the same
reason -- the stage-store alone doesn't show, in one skimmable place,
what happened to each topic.

Read-only against the stage-store itself; safe to run anytime. Run this
after any run that changes this pipeline's stage-store (spec.md, "Status
reporting -- mandatory after every run").

Usage:
    python tooling/build_status_report.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import yaml

PIPELINE_DIR = Path(__file__).resolve().parent.parent
SOURCE_CSV = PIPELINE_DIR / "source-data" / "clienta_topics.csv"
OUT_CSV = PIPELINE_DIR / "status-report.csv"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)

# One- or two-sentence, genuinely informative notes -- what happened, not
# just the new status (spec.md's own convention, copied from the Viksya
# pipeline this is modeled on). Add an entry here for every item whose
# status changes, same discipline either pipeline uses.
KNOWN_COMMENTS: dict[str, str] = {
    "TOP-0001": "Fully worked example for this repo: drafted, reviewed, approved, and "
                "staged to a demo git branch -- see stage-store/08-executed/TOP-0001.md.",
}


def split_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    return {} if not m else (yaml.safe_load(m.group(1)) or {})


def furthest_stage(pipeline_dir: Path, item_id: str) -> tuple[str, dict] | None:
    """(stage_name, frontmatter) for the furthest stage holding this
    item_id, checked in reverse pipeline order, or None if never discovered."""
    for stage in ("08-executed", "07-rejected", "06-approved", "05-pending-human-review",
                  "04-agent-review", "03-draft", "02-triage-decisions", "01-raw-metadata"):
        path = pipeline_dir / "stage-store" / stage / f"{item_id}.md"
        if path.exists():
            return stage, split_frontmatter(path.read_text(encoding="utf-8"))
    return None


def status_label(stage: str, fm: dict) -> str:
    if stage == "01-raw-metadata":
        return "Discovered"
    if stage == "02-triage-decisions":
        return {"discard": "Discarded", "escalate": "Escalated"}.get(fm.get("status"), "Triaged")
    if stage in ("03-draft", "04-agent-review"):
        return "Drafting"
    if stage == "05-pending-human-review":
        return "Pending human review"
    if stage == "06-approved":
        return "Approved, not yet published"
    if stage == "07-rejected":
        return "Rejected"
    if stage == "08-executed":
        return "Published" if fm.get("status") == "promoted" else "Staged (preview)"
    return "Not started"


def output_location(pipeline_dir: Path, item_id: str, fm: dict) -> str:
    if fm.get("output_mode") is None:
        # Pull it from the receipt's embedded JSON confirmation block, if present.
        path = pipeline_dir / "stage-store" / "08-executed" / f"{item_id}.md"
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if not m:
            return ""
        try:
            receipt = json.loads(m.group(1))
        except ValueError:
            return ""
    else:
        receipt = fm
    if receipt.get("output_mode") == "git_branch":
        return f"{receipt.get('branch', '')} ({receipt.get('post_file', '')})"
    if receipt.get("output_mode") == "local_files":
        return receipt.get("post_file", "")
    return ""


def build_report(pipeline_dir: Path) -> list[dict]:
    rows = []
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            item_id = row["ID"]
            found = furthest_stage(pipeline_dir, item_id)
            if found is None:
                status, loc = "Not started", ""
            else:
                stage, fm = found
                status = status_label(stage, fm)
                loc = output_location(pipeline_dir, item_id, fm) if stage == "08-executed" else ""
            rows.append({
                "ID": item_id,
                "Working Post Title": row.get("Working Post Title", ""),
                "Priority": row.get("Priority", ""),
                "Status": status,
                "Output Location": loc,
                "Comments": KNOWN_COMMENTS.get(item_id, ""),
            })
    return rows


def main() -> int:
    if not SOURCE_CSV.exists():
        print(f"error: {SOURCE_CSV} not found", file=sys.stderr)
        return 1

    rows = build_report(PIPELINE_DIR)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Working Post Title", "Priority",
                                                 "Status", "Output Location", "Comments"])
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["Status"]] = counts.get(row["Status"], 0) + 1
    print(f"Wrote {OUT_CSV} ({len(rows)} row(s))")
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
