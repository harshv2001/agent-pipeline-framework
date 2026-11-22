"""Regression tests for scripts/append_ledger.py and status derivation.

Run from this topic-engine folder:
    python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from append_ledger import append_ledger  # noqa: E402
from _common import derive_topic_status, ledger_path, load_ledger_rows  # noqa: E402


class TestAppendLedger(unittest.TestCase):
    def test_rejects_invalid_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            with self.assertRaises(ValueError):
                append_ledger(engine, "TOP-0001", "bogus-event", "actor", "run-1", "detail")

    def test_appends_without_truncating_prior_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            append_ledger(engine, "TOP-0001", "proposed", "agent", "run-1", "first")
            append_ledger(engine, "TOP-0002", "proposed", "agent", "run-1", "second")
            rows = load_ledger_rows(engine)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["topic_id"], "TOP-0001")
            self.assertEqual(rows[1]["topic_id"], "TOP-0002")

    def test_header_written_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            append_ledger(engine, "TOP-0001", "proposed", "agent", "run-1", "first")
            append_ledger(engine, "TOP-0001", "approved", "human", "run-2", "second")
            text = ledger_path(engine).read_text(encoding="utf-8")
            self.assertEqual(text.count("ts,topic_id,event,actor,run_id,detail"), 1)


class TestDeriveTopicStatus(unittest.TestCase):
    def test_no_rows_defaults_to_proposed(self):
        self.assertEqual(derive_topic_status([]), "proposed")

    def test_latest_non_correction_row_wins(self):
        rows = [
            {"event": "proposed"},
            {"event": "approved"},
            {"event": "correction"},  # never changes status
        ]
        self.assertEqual(derive_topic_status(rows), "approved")

    def test_rejected_then_correction_stays_rejected(self):
        rows = [{"event": "proposed"}, {"event": "rejected"}, {"event": "correction"}]
        self.assertEqual(derive_topic_status(rows), "rejected")

    def test_exported_is_terminal(self):
        rows = [{"event": "proposed"}, {"event": "approved"}, {"event": "exported"}]
        self.assertEqual(derive_topic_status(rows), "exported")


if __name__ == "__main__":
    unittest.main()
