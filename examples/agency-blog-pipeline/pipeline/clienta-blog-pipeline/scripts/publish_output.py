#!/usr/bin/env python3
"""Publisher Agent's action for this pipeline: stage one approved post.

Reads config.yaml's `output_mode` and writes to whichever destination
that selects (spec.md, "Output Destinations") -- this is the one script
that has to know about both modes; everything upstream of it (drafting,
review, approval) is identical either way.

- git_branch: create/reuse `stage/insights-{item_id}` in ./demo-site-repo
  (scripts/init_demo_site_repo.py sets that up), write the post as a page
  matching the fixture site's own shape, prepend its entry to
  blog/index.html, commit. Never touches `main`.
- local_files: write ./output/{item_id}/post.html + hero.svg + receipt.json.
  No git, no network -- hand these to whatever CMS the client runs.

Either way, this only ever reads an already-`06-approved` stage-store
record -- it never drafts or edits content, per
base-framework/agents/publisher-agent.md's own scope.

Usage:
    python scripts/publish_output.py --item-id TOP-0001
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

PIPELINE_DIR = Path(__file__).resolve().parent.parent
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)

PAGE_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} — ClientA</title>
</head>
<body>
<nav>Home | Services | About | Blog | Contact</nav>

<article>
<h1>{title}</h1>

{body}
</article>
</body>
</html>
"""

INDEX_LI_RE = re.compile(r'(<ul class="post-index">\s*\n)', re.IGNORECASE)


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("stage file has no valid --- delimited frontmatter block")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def load_config(pipeline_dir: Path) -> dict:
    return yaml.safe_load((pipeline_dir / "config.yaml").read_text(encoding="utf-8"))


def approved_record(pipeline_dir: Path, item_id: str) -> tuple[dict, str]:
    path = pipeline_dir / "stage-store" / "06-approved" / f"{item_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"no approved record for {item_id} at {path}")
    return split_frontmatter(path.read_text(encoding="utf-8"))


def what_was_drafted_section(body: str) -> str:
    """The 06-approved record's body is the carried-forward review packet
    (templates/review-packet.template.md), not the Content Agent's own
    context-pack-plus-draft layout -- the Human Liaison re-sections it
    under '## What was drafted' when packaging for review. Pull just that
    section, up to the next heading."""
    m = re.search(r"## What was drafted\s*\n(.*?)(?=\n## Agent review)", body, re.DOTALL)
    if not m:
        raise ValueError("approved record has no '## What was drafted' section -- "
                          "check it was packaged from templates/review-packet.template.md")
    return m.group(1).strip()


def post_body_html(section: str) -> str:
    """Strip any Backlink-edit subsection -- this is the publish-ready
    HTML the Content Agent wrote at draft time (base-framework/agents/
    content-agent.md Contract step 5): what's approved is exactly what
    ships, no re-rendering at publish time."""
    m = re.search(r"(.*?)(?=\n## Backlink edit|\Z)", section, re.DOTALL)
    return (m.group(1) if m else section).strip()


def backlink_edit(section: str) -> str | None:
    m = re.search(r"## Backlink edit\s*\n(.*?)\Z", section, re.DOTALL)
    return m.group(1).strip() if m else None


def slug_for(item_id: str) -> str:
    return item_id.lower()


def publish_local_files(pipeline_dir: Path, item_id: str, fm: dict, html: str, backlink: str | None) -> dict:
    out_dir = pipeline_dir / "output" / item_id
    out_dir.mkdir(parents=True, exist_ok=True)

    title = fm.get("working_title") or fm.get("title") or item_id
    (out_dir / "post.html").write_text(PAGE_SHELL.format(title=title, body=html), encoding="utf-8")

    hero_src = pipeline_dir / fm.get("manifest", [None])[0] if fm.get("manifest") else None
    hero_dest = None
    if hero_src and hero_src.exists():
        hero_dest = out_dir / hero_src.name
        shutil.copy(hero_src, hero_dest)

    receipt = {
        "item_id": item_id,
        "status": "staged",
        "output_mode": "local_files",
        "post_file": str(out_dir / "post.html"),
        "hero_image": str(hero_dest) if hero_dest else None,
        "backlink_edit_pending": backlink,  # text proposed for the older post -- not auto-applied, see note below
    }
    if backlink:
        (out_dir / "backlink-edit.txt").write_text(backlink, encoding="utf-8")
        receipt["backlink_edit_note"] = (
            "This script never edits an existing post automatically -- a one-sentence "
            "insertion into unstructured prose is not safe to place unattended. Apply "
            "backlink-edit.txt's text to the older post by hand (or extend this script "
            "for your real CMS once you know its content format)."
        )
    (out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo_dir, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def publish_git_branch(pipeline_dir: Path, item_id: str, fm: dict, html: str, backlink: str | None) -> dict:
    repo_dir = pipeline_dir / "demo-site-repo"
    if not repo_dir.exists():
        raise FileNotFoundError(
            f"{repo_dir} doesn't exist -- run scripts/init_demo_site_repo.py first "
            f"(or switch config.yaml's output_mode to local_files)"
        )

    branch = f"stage/insights-{item_id.lower()}"
    existing_branches = run_git(repo_dir, "branch", "--list", branch)
    run_git(repo_dir, "checkout", "main")
    if existing_branches:
        run_git(repo_dir, "checkout", branch)
    else:
        run_git(repo_dir, "checkout", "-b", branch)

    title = fm.get("working_title") or fm.get("title") or item_id
    slug = slug_for(item_id)
    post_path = repo_dir / "blog" / f"{slug}.html"
    post_path.write_text(PAGE_SHELL.format(title=title, body=html), encoding="utf-8")

    hero_dest = None
    manifest = fm.get("manifest") or []
    if manifest:
        hero_src = pipeline_dir / manifest[0]
        if hero_src.exists():
            hero_dest = repo_dir / "blog" / hero_src.name
            shutil.copy(hero_src, hero_dest)

    # Prepend an index entry, same precedent as the Viksya pipelines' insights.njk insertion.
    index_path = repo_dir / "blog" / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    new_li = f'<li><a href="/blog/{slug}">{title}</a></li>\n'
    index_html = INDEX_LI_RE.sub(lambda m: m.group(1) + new_li, index_html, count=1)
    index_path.write_text(index_html, encoding="utf-8")

    backlink_note = None
    if backlink:
        backlink_path = repo_dir / "blog" / f"{slug}-backlink-edit.txt"
        backlink_path.write_text(backlink, encoding="utf-8")
        backlink_note = (
            f"Proposed edit for the older post this topic names as its Closest Existing "
            f"Post, written to blog/{slug}-backlink-edit.txt on this same branch -- not "
            f"auto-applied (a one-sentence insertion into unstructured prose isn't safe "
            f"to place unattended). Apply it by hand on this branch before merging, or "
            f"extend this script for your real CMS's content format."
        )

    run_git(repo_dir, "add", "-A")
    run_git(repo_dir, "commit", "-m", f"Stage {item_id}: {title}")

    return {
        "item_id": item_id,
        "status": "staged",
        "output_mode": "git_branch",
        "branch": branch,
        "post_file": f"blog/{slug}.html",
        "hero_image": f"blog/{hero_dest.name}" if hero_dest else None,
        "backlink_edit_pending": backlink,
        "backlink_edit_note": backlink_note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--pipeline", type=Path, default=PIPELINE_DIR)
    args = parser.parse_args()

    config = load_config(args.pipeline)
    output_mode = config.get("output_mode", "git_branch")

    fm, body = approved_record(args.pipeline, args.item_id)
    section = what_was_drafted_section(body)
    html = post_body_html(section)
    backlink = backlink_edit(section)

    if output_mode == "local_files":
        receipt = publish_local_files(args.pipeline, args.item_id, fm, html, backlink)
    elif output_mode == "git_branch":
        receipt = publish_git_branch(args.pipeline, args.item_id, fm, html, backlink)
    else:
        print(f"error: unknown output_mode {output_mode!r}", file=sys.stderr)
        return 1

    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
