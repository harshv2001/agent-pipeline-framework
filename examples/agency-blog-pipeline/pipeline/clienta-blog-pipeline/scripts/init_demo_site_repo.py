#!/usr/bin/env python3
"""Set up a local git repo standing in for ClientA's real site repo.

This example's default output mode (`output_mode: git_branch` in
config.yaml) commits staged posts to a branch of a site repo, exactly
like `pipelines/high-intent-csv-to-viksya-insights-blog` does against the
real `viksya-website` repo -- but this is a public, offline example, so
there's no real client repo and no GitHub credential to push with. This
script creates a throwaway local git repo at `./demo-site-repo/`, seeds
it with the `sample-client-site/` fixture as its `main` branch (standing
in for "what's already live"), and leaves it there for
`scripts/publish_output.py` to branch from.

`demo-site-repo/` is gitignored by this repository -- it's generated
local state, not something to commit. For a real engagement, skip this
script entirely and point `config.yaml`'s `connector_ref` at the client's
actual repo instead.

Usage:
    python scripts/init_demo_site_repo.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = PIPELINE_DIR / "demo-site-repo"
SAMPLE_SITE_DIR = PIPELINE_DIR / ".." / ".." / "sample-client-site"


def run_git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_DIR, check=True, capture_output=True, text=True)


def main() -> int:
    if REPO_DIR.exists():
        print(f"error: {REPO_DIR} already exists -- refusing to overwrite. "
              f"Delete it first if you want a fresh demo repo.", file=sys.stderr)
        return 1

    site_dir = SAMPLE_SITE_DIR.resolve()
    if not site_dir.exists():
        print(f"error: fixture site not found: {site_dir}", file=sys.stderr)
        return 1

    shutil.copytree(site_dir, REPO_DIR)
    run_git("init", "-b", "main")
    run_git("config", "user.email", "demo@example.invalid")
    run_git("config", "user.name", "agency-blog-pipeline example")
    run_git("add", "-A")
    run_git("commit", "-m", "Initial import: ClientA site fixture (standing in for 'already live')")

    print(f"Created {REPO_DIR} on branch 'main'.")
    print("This stands in for ClientA's real site repo -- scripts/publish_output.py "
          "will create a stage/insights-{item_id} branch here for each approved post.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
