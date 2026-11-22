"""Regression tests for scripts/next_topic_id.py.

Run from this topic-engine folder:
    python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from next_topic_id import next_topic_id  # noqa: E402


class TestNextTopicId(unittest.TestCase):
    def test_empty_registry_starts_at_0001(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            self.assertEqual(next_topic_id(engine), "TOP-0001")

    def test_increments_past_highest_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            topics = engine / "registry" / "topics"
            topics.mkdir(parents=True)
            (topics / "TOP-0001.md").write_text("x", encoding="utf-8")
            (topics / "TOP-0003.md").write_text("x", encoding="utf-8")
            # A gap (TOP-0002 rejected and never reused) must not be filled --
            # ids are never reused, per schema/REGISTRY-SCHEMA.md.
            self.assertEqual(next_topic_id(engine), "TOP-0004")

    def test_ignores_non_matching_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp)
            topics = engine / "registry" / "topics"
            topics.mkdir(parents=True)
            (topics / "TOP-0001.md").write_text("x", encoding="utf-8")
            (topics / "README.md").write_text("x", encoding="utf-8")
            self.assertEqual(next_topic_id(engine), "TOP-0002")


if __name__ == "__main__":
    unittest.main()
