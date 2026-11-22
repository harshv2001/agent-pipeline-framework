#!/usr/bin/env python3
"""Append one event row to registry/ledger.csv.

Append-only -- this never edits or deletes an existing row. A correction
to a prior row is a new row with event=correction, whose detail names the
run_id of the row it corrects (schema/REGISTRY-SCHEMA.md), same discipline
as this framework's own 09-audit-log (docs/01-governance-rules.md Rule 5).

Usage:
    python scripts/append_ledger.py --engine . --topic-id TOP-0001 \\
        --event proposed --actor "topic-discovery-agent v1" \\
        --run-id TDA-2026-1122 --detail "Bootstrap run: initial batch"
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from _common import LEDGER_COLUMNS, VALID_EVENTS, ledger_path, now_iso


def append_ledger(engine_dir: Path, topic_id: str, event: str, actor: str, run_id: str, detail: str) -> Path:
    if event not in VALID_EVENTS:
        raise ValueError(f"event must be one of {sorted(VALID_EVENTS)}, got {event!r}")
    path = ledger_path(engine_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "ts": now_iso(), "topic_id": topic_id, "event": event,
            "actor": actor, "run_id": run_id, "detail": detail,
        })
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", type=Path, default=Path("."))
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--event", required=True, choices=sorted(VALID_EVENTS))
    parser.add_argument("--actor", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--detail", required=True)
    args = parser.parse_args()

    path = append_ledger(args.engine, args.topic_id, args.event, args.actor, args.run_id, args.detail)
    print(f"Appended {args.event!r} for {args.topic_id} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
