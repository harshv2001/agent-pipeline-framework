#!/usr/bin/env python3
"""Mechanical site-structure extraction for the topic-engine's bootstrap run.

Reads the client's site -- by default the bundled `sample-client-site/`
fixture; point `--site` at a real export/crawl of a live client site to
use this for an actual engagement -- and writes a deterministic
`site-profile/site-facts.json`: page titles and headings, each page's
plain-text content, the service/product list with slugs, and the existing
blog index.

This script does no judgment -- no tone, voice, personality, or industry
inference. It only extracts what's mechanically present on the page. The
Topic Discovery Agent (agents/topic-discovery-agent.md) reads this JSON
plus the raw pages to do the actual qualitative read and writes
`site-profile/site-profile.md` itself -- the same split the rest of this
framework uses between scripts (mechanical) and agents (judgment).

Uses a small regex-based extractor, not a full HTML parser or a browser
render. That's good enough for the bundled fixture and for most simple,
server-rendered marketing sites -- it is not a guarantee against
malformed or JS-rendered HTML. For a real client site with either
problem, export its rendered HTML first (e.g. "View Source" after the
page settles, or a static-export build) rather than pointing this
directly at the live, JS-heavy page.

Usage:
    python scripts/analyze_site.py --engine . --site ../sample-client-site
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HEADING_RE = re.compile(r"<h([12])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SERVICE_SECTION_RE = re.compile(
    r'<section\s+id="([^"]+)"[^>]*>\s*<h2>\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>\s*</h2>',
    re.IGNORECASE | re.DOTALL,
)
POST_INDEX_LINK_RE = re.compile(
    r'<li>\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>\s*</li>', re.IGNORECASE | re.DOTALL
)


def strip_tags(raw_html: str) -> str:
    text = TAG_RE.sub(" ", raw_html)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_title(html: str) -> str | None:
    m = TITLE_RE.search(html)
    return strip_tags(m.group(1)) if m else None


def extract_headings(html: str) -> list[dict]:
    return [{"level": int(level), "text": strip_tags(text)} for level, text in HEADING_RE.findall(html)]


def extract_body_text(html: str) -> str:
    # Drop <nav>...</nav> -- it's the same on every page and adds no signal.
    html = re.sub(r"<nav[^>]*>.*?</nav>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    return strip_tags(html)


def analyze_page(path: Path) -> dict:
    html = path.read_text(encoding="utf-8")
    return {
        "path": path.name,
        "title": extract_title(html),
        "headings": extract_headings(html),
        "text": extract_body_text(html),
        "word_count": len(extract_body_text(html).split()),
    }


def extract_services(services_html: str) -> list[dict]:
    return [
        {"slug": slug, "url": url, "name": strip_tags(name)}
        for slug, url, name in SERVICE_SECTION_RE.findall(services_html)
    ]


def extract_existing_posts(blog_index_html: str) -> list[dict]:
    return [
        {"url": url, "title": strip_tags(title)}
        for url, title in POST_INDEX_LINK_RE.findall(blog_index_html)
    ]


def analyze_site(site_dir: Path) -> dict:
    pages = []
    for name in ("index.html", "about.html", "services.html"):
        p = site_dir / name
        if p.exists():
            pages.append(analyze_page(p))

    services_path = site_dir / "services.html"
    services = extract_services(services_path.read_text(encoding="utf-8")) if services_path.exists() else []

    blog_index_path = site_dir / "blog" / "index.html"
    existing_posts = (
        extract_existing_posts(blog_index_path.read_text(encoding="utf-8"))
        if blog_index_path.exists() else []
    )

    return {"site_source": str(site_dir), "pages": pages, "services": services, "existing_posts": existing_posts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", type=Path, default=Path("."), help="Path to this topic-engine folder")
    parser.add_argument("--site", type=Path, default=None,
                         help="Path to the client site to read (default: ../sample-client-site, relative to --engine)")
    args = parser.parse_args()

    engine_dir = args.engine
    site_dir = args.site if args.site is not None else (engine_dir / ".." / "sample-client-site")
    site_dir = site_dir.resolve()

    if not site_dir.exists():
        print(f"error: site directory not found: {site_dir}", file=sys.stderr)
        return 1

    facts = analyze_site(site_dir)
    out_dir = engine_dir / "site-profile"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "site-facts.json"
    out_path.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"  {len(facts['pages'])} page(s), {len(facts['services'])} service(s), "
          f"{len(facts['existing_posts'])} existing post(s)")
    print("Next: have the Topic Discovery Agent read this file plus the raw pages "
          "and write site-profile/site-profile.md (qualitative read -- this script makes none).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
