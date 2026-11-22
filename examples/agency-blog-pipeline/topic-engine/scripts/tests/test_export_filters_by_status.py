"""Regression tests for scripts/export_topics_csv.py.

Run from this topic-engine folder:
    python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from append_ledger import append_ledger  # noqa: E402
from export_topics_csv import export_topics  # noqa: E402
from _common import load_ledger_rows, write_topic  # noqa: E402


def make_topic(engine: Path, topic_id: str) -> None:
    write_topic(engine / "registry" / "topics" / f"{topic_id}.md", {
        "topic_id": topic_id,
        "title": f"Title for {topic_id}",
        "status_at_birth": "proposed",
        "created_at": "2026-11-22T00:00:00Z",
        "produced_by": "topic-discovery-agent v1",
        "supersedes": None,
        "track": "Bookkeeping",
        "service_ref": "bookkeeping",
        "service_url": "/services/bookkeeping",
        "primary_keyword": f"keyword for {topic_id}",
        "search_intent_type": "Definition",
        "working_title": f"Working title for {topic_id}",
        "secondary_keywords": ["a", "b"],
        "coverage_status": "Not covered",
        "closest_existing_post": None,
        "priority": 1,
        "source_basis": "test fixture",
    }, "## Why this is a gap\n\ntest\n")


class TestExportTopicsCsv(unittest.TestCase):
    def test_only_approved_topics_are_exported(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            out = engine / "out.csv"
            make_topic(engine, "TOP-0001")
            make_topic(engine, "TOP-0002")
            append_ledger(engine, "TOP-0001", "proposed", "agent", "r1", "x")
            append_ledger(engine, "TOP-0002", "proposed", "agent", "r1", "x")
            append_ledger(engine, "TOP-0001", "approved", "human", "r2", "x")
            append_ledger(engine, "TOP-0002", "rejected", "human", "r2", "x")

            exported = export_topics(engine, out, "agent", "r3")

            self.assertEqual(exported, ["TOP-0001"])
            with out.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r["ID"] for r in rows], ["TOP-0001"])

    def test_rerun_is_idempotent_and_additive(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            out = engine / "out.csv"
            make_topic(engine, "TOP-0001")
            append_ledger(engine, "TOP-0001", "proposed", "agent", "r1", "x")
            append_ledger(engine, "TOP-0001", "approved", "human", "r2", "x")

            first = export_topics(engine, out, "agent", "r3")
            self.assertEqual(first, ["TOP-0001"])

            # Re-running with nothing new approved exports nothing further,
            # and doesn't duplicate the existing row.
            second = export_topics(engine, out, "agent", "r4")
            self.assertEqual(second, [])
            with out.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)

            # A later-approved topic is added without disturbing the first row.
            make_topic(engine, "TOP-0002")
            append_ledger(engine, "TOP-0002", "proposed", "agent", "r4", "x")
            append_ledger(engine, "TOP-0002", "approved", "human", "r5", "x")
            third = export_topics(engine, out, "agent", "r6")
            self.assertEqual(third, ["TOP-0002"])
            with out.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r["ID"] for r in rows], ["TOP-0001", "TOP-0002"])

    def test_export_appends_exported_ledger_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            out = engine / "out.csv"
            make_topic(engine, "TOP-0001")
            append_ledger(engine, "TOP-0001", "proposed", "agent", "r1", "x")
            append_ledger(engine, "TOP-0001", "approved", "human", "r2", "x")

            export_topics(engine, out, "agent", "r3")

            events = [row["event"] for row in load_ledger_rows(engine) if row["topic_id"] == "TOP-0001"]
            self.assertEqual(events, ["proposed", "approved", "exported"])


if __name__ == "__main__":
    unittest.main()
