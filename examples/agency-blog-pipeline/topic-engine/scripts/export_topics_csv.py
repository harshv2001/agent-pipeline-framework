#!/usr/bin/env python3
"""Export every `approved` topic into the blog pipeline's source-data CSV.

This is the engine's one write into the pipeline, and it's the engine's
entire product for this example: the pipeline's `filesystem` source reads
this CSV, not the engine's own registry (same boundary
docs/11-topic-engine.md describes for a runtime-scope pipeline, adapted --
here the "inbox" is a CSV row, not a run-request file). Idempotent and
additive: existing rows in the destination CSV are kept byte-for-byte, a
topic already exported is skipped (its derived status is already
`exported`, not `approved`, once this has run for it once), and only
newly-approved topics are appended. That's what makes re-running the
topic engine later genuinely optional -- a pipeline run never needs to
wait on it, and a later engine run never disturbs rows the pipeline has
already started working from.

Usage:
    python scripts/export_topics_csv.py --engine . \\
        --out ../pipeline/clienta-blog-pipeline/source-data/clienta_topics.csv \\
        --actor "topic-discovery-agent v1" --run-id EXP-2026-1122
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from _common import derive_topic_status, iter_topic_files, load_ledger_rows, read_topic
from append_ledger import append_ledger

CSV_COLUMNS = [
    "ID", "Track", "Service Addressed", "Service URL",
    "High-Intent Search Query (Primary Keyword)", "Search Intent Type",
    "Working Post Title", "Secondary Keywords", "Coverage Status on Blog Index",
    "Closest Existing Post", "Recommended Action", "Priority", "Source Basis",
]


def topic_to_row(fm: dict) -> dict:
    closest = fm.get("closest_existing_post") or ""
    action = "Write new post; internal-link existing post" if closest else "Write new post"
    return {
        "ID": fm["topic_id"],
        "Track": fm.get("track", ""),
        "Service Addressed": fm.get("service_ref", ""),
        "Service URL": fm.get("service_url", ""),
        "High-Intent Search Query (Primary Keyword)": fm.get("primary_keyword", ""),
        "Search Intent Type": fm.get("search_intent_type", ""),
        "Working Post Title": fm.get("working_title", ""),
        "Secondary Keywords": "; ".join(fm.get("secondary_keywords") or []),
        "Coverage Status on Blog Index": fm.get("coverage_status", ""),
        "Closest Existing Post": closest,
        "Recommended Action": action,
        "Priority": fm.get("priority", ""),
        "Source Basis": fm.get("source_basis", ""),
    }


def read_existing_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    with out_path.open(encoding="utf-8-sig", newline="") as f:
        return {row["ID"] for row in csv.DictReader(f)}


def export_topics(engine_dir: Path, out_path: Path, actor: str, run_id: str) -> list[str]:
    ledger_rows = load_ledger_rows(engine_dir)
    rows_by_topic: dict[str, list[dict]] = {}
    for row in ledger_rows:
        rows_by_topic.setdefault(row["topic_id"], []).append(row)

    already_in_csv = read_existing_ids(out_path)
    new_rows = []
    exported_ids = []
    for path in iter_topic_files(engine_dir):
        fm, _ = read_topic(path)
        topic_id = fm["topic_id"]
        if topic_id in already_in_csv:
            continue
        if derive_topic_status(rows_by_topic.get(topic_id, [])) != "approved":
            continue
        new_rows.append(topic_to_row(fm))
        exported_ids.append(topic_id)

    if new_rows:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        existing_rows = []
        if out_path.exists():
            with out_path.open(encoding="utf-8-sig", newline="") as f:
                existing_rows = list(csv.DictReader(f))
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerows(new_rows)

        for topic_id in exported_ids:
            append_ledger(engine_dir, topic_id, "exported", actor, run_id,
                           detail=f"Exported to {out_path}")

    return exported_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True,
                         help="Path to the pipeline's source-data CSV")
    parser.add_argument("--actor", default="topic-discovery-agent v1")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    exported = export_topics(args.engine, args.out, args.actor, args.run_id)
    if exported:
        print(f"Exported {len(exported)} topic(s) to {args.out}: {', '.join(exported)}")
    else:
        print("No approved, not-yet-exported topics found -- nothing to export.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
