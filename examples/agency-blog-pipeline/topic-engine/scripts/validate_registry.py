#!/usr/bin/env python3
"""Mechanical validation of the topic registry.

Checks the things a script can check -- not whether a topic is a *good*
idea, which is the Topic Discovery Agent's and the human reviewer's job.

Usage:
    python scripts/validate_registry.py --engine .
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import LEDGER_COLUMNS, REQUIRED_TOPIC_KEYS, VALID_EVENTS, iter_topic_files, ledger_path, read_topic


def validate_topic_file(path: Path) -> list[str]:
    errors = []
    try:
        fm, body = read_topic(path)
    except ValueError as e:
        return [f"{path.name}: {e}"]

    for key in REQUIRED_TOPIC_KEYS:
        if key not in fm:
            errors.append(f"{path.name}: missing required frontmatter key '{key}'")

    if "topic_id" in fm and fm["topic_id"] != path.stem:
        errors.append(f"{path.name}: frontmatter topic_id {fm['topic_id']!r} does not match filename")

    if fm.get("status_at_birth") != "proposed":
        errors.append(f"{path.name}: status_at_birth must be 'proposed', got {fm.get('status_at_birth')!r}")

    keyword = fm.get("primary_keyword")
    if isinstance(keyword, str):
        if "http://" in keyword or "https://" in keyword:
            errors.append(f"{path.name}: primary_keyword must be a search phrase, not a URL")
        if len(keyword) > 200:
            errors.append(f"{path.name}: primary_keyword exceeds 200 characters")

    priority = fm.get("priority")
    if priority not in (1, 2, 3):
        errors.append(f"{path.name}: priority must be 1, 2, or 3, got {priority!r}")

    secondary = fm.get("secondary_keywords")
    if secondary is not None and not isinstance(secondary, list):
        errors.append(f"{path.name}: secondary_keywords must be a list")

    return errors


def validate_ledger(engine_dir: Path) -> list[str]:
    path = ledger_path(engine_dir)
    if not path.exists():
        return []
    errors = []
    import csv
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != LEDGER_COLUMNS:
            errors.append(f"ledger.csv: header is {reader.fieldnames}, expected {LEDGER_COLUMNS}")
            return errors
        for i, row in enumerate(reader, start=2):
            if row["event"] not in VALID_EVENTS:
                errors.append(f"ledger.csv:{i}: invalid event {row['event']!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=Path("."))
    args = parser.parse_args()

    errors: list[str] = []
    seen_ids: set[str] = set()
    for path in iter_topic_files(args.engine):
        errors.extend(validate_topic_file(path))
        try:
            fm, _ = read_topic(path)
            tid = fm.get("topic_id")
            if tid in seen_ids:
                errors.append(f"{path.name}: duplicate topic_id {tid!r}")
            seen_ids.add(tid)
        except ValueError:
            pass

    errors.extend(validate_ledger(args.engine))

    if errors:
        print(f"{len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK -- {len(seen_ids)} topic file(s), ledger valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
