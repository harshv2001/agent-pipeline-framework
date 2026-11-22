#!/usr/bin/env python3
"""Regenerate registry/registry.csv from the topic files plus the ledger.

Generated, never hand-edited (schema/REGISTRY-SCHEMA.md) -- a full view of
every topic regardless of status, for a human to skim in a spreadsheet.
Run this after any ledger change (a proposal, an approval, a rejection, an
export) before considering that step done.

Usage:
    python scripts/fold_ledger.py --engine .
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from _common import (
    derive_topic_status, iter_topic_files, latest_event_row,
    load_ledger_rows, read_topic, registry_csv_path,
)

REGISTRY_COLUMNS = [
    "topic_id", "title", "track", "service_ref", "service_url",
    "primary_keyword", "search_intent_type", "priority", "coverage_status",
    "closest_existing_post", "topic_status", "last_event_ts", "last_event", "detail",
]


def fold_ledger(engine_dir: Path) -> list[dict]:
    ledger_rows = load_ledger_rows(engine_dir)
    rows_by_topic: dict[str, list[dict]] = {}
    for row in ledger_rows:
        rows_by_topic.setdefault(row["topic_id"], []).append(row)

    out_rows = []
    for path in iter_topic_files(engine_dir):
        fm, _ = read_topic(path)
        topic_id = fm["topic_id"]
        topic_rows = rows_by_topic.get(topic_id, [])
        status = derive_topic_status(topic_rows)
        latest = latest_event_row(topic_rows)
        out_rows.append({
            "topic_id": topic_id,
            "title": fm.get("title", ""),
            "track": fm.get("track", ""),
            "service_ref": fm.get("service_ref", ""),
            "service_url": fm.get("service_url", ""),
            "primary_keyword": fm.get("primary_keyword", ""),
            "search_intent_type": fm.get("search_intent_type", ""),
            "priority": fm.get("priority", ""),
            "coverage_status": fm.get("coverage_status", ""),
            "closest_existing_post": fm.get("closest_existing_post") or "",
            "topic_status": status,
            "last_event_ts": latest["ts"] if latest else "",
            "last_event": latest["event"] if latest else "",
            "detail": latest["detail"] if latest else "",
        })
    return out_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=Path("."))
    args = parser.parse_args()

    rows = fold_ledger(args.engine)
    out_path = registry_csv_path(args.engine)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {out_path} ({len(rows)} topic(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
