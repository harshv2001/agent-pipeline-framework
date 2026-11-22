"""Shared helpers for the topic-engine example scripts.

Not a public API -- used by analyze_site.py, next_topic_id.py,
append_ledger.py, fold_ledger.py, export_topics_csv.py, and
validate_registry.py. Same conventions as the base framework's own
scripts/_common.py (PyYAML-only, UTF-8 everywhere) so this reads like one
codebase, not a separate one bolted on.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)

LEDGER_COLUMNS = ["ts", "topic_id", "event", "actor", "run_id", "detail"]
VALID_EVENTS = {"proposed", "approved", "rejected", "exported", "correction"}

REQUIRED_TOPIC_KEYS = [
    "topic_id", "title", "status_at_birth", "created_at", "produced_by",
    "supersedes", "track", "service_ref", "service_url", "primary_keyword",
    "search_intent_type", "working_title", "secondary_keywords",
    "coverage_status", "closest_existing_post", "priority", "source_basis",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("File has no valid --- delimited frontmatter block")
    fm_text, body = m.group(1), m.group(2)
    fm = yaml.safe_load(fm_text) or {}
    return fm, body


def render(frontmatter: dict, body: str) -> str:
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm_text}\n---\n{body}"


def read_topic(path: Path) -> tuple[dict, str]:
    return split_frontmatter(path.read_text(encoding="utf-8"))


def write_topic(path: Path, frontmatter: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(frontmatter, body), encoding="utf-8")


def topics_dir(engine_dir: Path) -> Path:
    return engine_dir / "registry" / "topics"


def ledger_path(engine_dir: Path) -> Path:
    return engine_dir / "registry" / "ledger.csv"


def registry_csv_path(engine_dir: Path) -> Path:
    return engine_dir / "registry" / "registry.csv"


def iter_topic_files(engine_dir: Path):
    d = topics_dir(engine_dir)
    if not d.exists():
        return
    yield from sorted(d.glob("TOP-*.md"))


def load_ledger_rows(engine_dir: Path) -> list[dict]:
    import csv
    path = ledger_path(engine_dir)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def derive_topic_status(rows_for_topic: list[dict]) -> str:
    """Latest non-`correction` event wins; `correction` rows never change
    status, they only annotate ledger history (schema/REGISTRY-SCHEMA.md).
    No rows at all shouldn't happen (every topic file gets a `proposed` row
    at creation) but falls back to `proposed` rather than raising."""
    meaningful = [r for r in rows_for_topic if r.get("event") != "correction"]
    if not meaningful:
        return "proposed"
    return meaningful[-1]["event"]


def latest_event_row(rows_for_topic: list[dict]) -> dict | None:
    return rows_for_topic[-1] if rows_for_topic else None
