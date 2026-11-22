#!/usr/bin/env python3
"""Generate a dependency-free placeholder hero image (SVG) for one post.

Exists so this example runs end-to-end with nothing but Python and no
paid image-generation API key (agents/content-agent.md, "Hero image").
Renders a simple geometric 1600x900 banner in ClientA's palette
(source-data/clienta_brand_profile.md) — no literal logo, no
photorealistic imagery, just the title, a service tag, and a few
rectangles/circles as abstract motifs.

For a real engagement, replace this script's output with real image
generation -- this is a placeholder, not a design recommendation.

Usage:
    python scripts/generate_hero_svg.py --title "..." --service-ref cash-flow-forecasting --out path/to/hero.svg
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

NAVY = "#1B2A41"
PARCHMENT = "#F7F4EE"
TEAL = "#2E8B7B"

SERVICE_LABELS = {
    "bookkeeping": "Monthly Bookkeeping",
    "cash-flow-forecasting": "Cash Flow Forecasting",
    "fractional-cfo": "Fractional CFO Advisory",
}


def wrap_title(title: str, width: int = 26) -> list[str]:
    return textwrap.wrap(title, width=width)[:3]  # at most 3 lines, keeps text inside the frame


def render_svg(title: str, service_ref: str) -> str:
    lines = wrap_title(title)
    label = SERVICE_LABELS.get(service_ref, service_ref)
    line_height = 64
    start_y = 450 - (len(lines) - 1) * line_height // 2

    text_elements = "\n".join(
        f'  <text x="120" y="{start_y + i * line_height}" font-family="Georgia, serif" '
        f'font-size="54" font-weight="bold" fill="{NAVY}">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )

    return f"""<svg viewBox="0 0 1600 900" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="1600" height="900" fill="{PARCHMENT}"/>
  <rect x="0" y="0" width="1600" height="16" fill="{TEAL}"/>
  <rect x="0" y="884" width="1600" height="16" fill="{TEAL}"/>
  <circle cx="1420" cy="180" r="140" fill="{NAVY}" opacity="0.08"/>
  <circle cx="1500" cy="700" r="100" fill="{TEAL}" opacity="0.15"/>
  <rect x="120" y="120" width="90" height="10" fill="{TEAL}"/>
  <text x="120" y="90" font-family="Helvetica, Arial, sans-serif" font-size="28"
        letter-spacing="2" fill="{TEAL}">{escape(label.upper())}</text>
{text_elements}
  <text x="120" y="800" font-family="Helvetica, Arial, sans-serif" font-size="24"
        fill="{NAVY}" opacity="0.6">ClientA</text>
</svg>
"""


def escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", required=True)
    parser.add_argument("--service-ref", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    svg = render_svg(args.title, args.service_ref)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(svg, encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
