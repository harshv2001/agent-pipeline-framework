#!/usr/bin/env python3
"""Next sequential TOP-#### id. Never reused, even for a rejected topic
(schema/REGISTRY-SCHEMA.md, "Identifiers").

Usage:
    python scripts/next_topic_id.py --engine .
"""
from __future__ import annotations

import argparse
from pathlib import Path

from _common import topics_dir


def next_topic_id(engine_dir: Path) -> str:
    max_n = 0
    for path in topics_dir(engine_dir).glob("TOP-*.md") if topics_dir(engine_dir).exists() else []:
        try:
            n = int(path.stem.split("-")[1])
        except (IndexError, ValueError):
            continue
        max_n = max(max_n, n)
    return f"TOP-{max_n + 1:04d}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=Path("."))
    args = parser.parse_args()
    print(next_topic_id(args.engine))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
