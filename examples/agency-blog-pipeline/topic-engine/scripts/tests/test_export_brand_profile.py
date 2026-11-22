"""Regression tests for scripts/export_brand_profile.py.

Run from this topic-engine folder:
    python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from export_brand_profile import build_brand_profile_md, extract_section  # noqa: E402

SITE_PROFILE_MD = """---
client: Acme
---

# Acme — Site Profile

## Industry

Widget manufacturing for small retailers.

## Voice and personality

- Direct, no fluff.
- Prefer "built to last" over "premium quality."

## Services (ground topics in these)

| service_ref | name | url |
|---|---|---|
| widgets | Widgets | /services/widgets |

## Existing blog coverage

None yet.
"""


class TestExtractSection(unittest.TestCase):
    def test_extracts_industry_up_to_next_heading(self):
        text = extract_section(SITE_PROFILE_MD, "Industry")
        self.assertEqual(text, "Widget manufacturing for small retailers.")

    def test_extracts_voice_up_to_next_heading(self):
        text = extract_section(SITE_PROFILE_MD, "Voice and personality")
        self.assertIn('Prefer "built to last"', text)
        self.assertNotIn("Services (ground topics", text)

    def test_missing_heading_raises(self):
        with self.assertRaises(ValueError):
            extract_section(SITE_PROFILE_MD, "Nonexistent Heading")


class TestBuildBrandProfileMd(unittest.TestCase):
    def test_includes_client_name_services_and_palette(self):
        md = build_brand_profile_md(
            client={"name": "Acme"},
            services=[{"slug": "widgets", "name": "Widgets", "url": "/services/widgets"}],
            brand={"navy": "#000000", "parchment": "#FFFFFF", "accent": "#123456"},
            industry="Widget manufacturing.",
            voice="Direct, no fluff.",
            site_profile_ref="topic-engine/site-profile/site-profile.md",
        )
        self.assertIn("client: Acme", md)
        self.assertIn("Widget manufacturing.", md)
        self.assertIn("Direct, no fluff.", md)
        self.assertIn("`widgets`", md)
        self.assertIn("#000000", md)
        self.assertIn("#123456", md)


if __name__ == "__main__":
    unittest.main()
