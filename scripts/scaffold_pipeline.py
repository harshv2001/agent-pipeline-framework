#!/usr/bin/env python3
"""Scaffold a new pipeline from the base templates.

Usage:
    python scripts/scaffold_pipeline.py <pipeline-name>

Creates pipelines/<pipeline-name>/ with spec.md, logic.md, and config.yaml
copied from templates/ (placeholders filled in with the pipeline name), an
empty agents/ folder for role overrides, and the ten stage-store folders
from docs/03-stage-store-model.md. Refuses to overwrite an existing
pipeline folder.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import STAGES, repo_root

PLACEHOLDER = "<replace-with-folder-name>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Pipeline name — lowercase, hyphenated (docs/09-directory-layout.md)")
    args = parser.parse_args()

    name = args.name
    if not name or name != name.lower() or " " in name:
        print(f"error: pipeline name should be lowercase and hyphenated, got: {name!r}", file=sys.stderr)
        return 1

    root = repo_root()
    templates = root / "templates"
    dest = root / "pipelines" / name

    if dest.exists():
        print(f"error: {dest} already exists — refusing to overwrite", file=sys.stderr)
        return 1

    dest.mkdir(parents=True)
    (dest / "agents").mkdir()
    (dest / "agents" / ".gitkeep").touch()

    for stage in STAGES:
        stage_dir = dest / "stage-store" / stage
        stage_dir.mkdir(parents=True)
        (stage_dir / ".gitkeep").touch()

    # Scaffolded for every pipeline, used only if config.yaml's
    # source.scope_source is later set to 'runtime' (docs/07-configuration-
    # reference.md). Harmless and empty otherwise.
    for sub in ("pending", "consumed"):
        rr_dir = dest / "run-requests" / sub
        rr_dir.mkdir(parents=True)
        (rr_dir / ".gitkeep").touch()

    mapping = {
        "pipeline-spec.template.md": "spec.md",
        "logic.template.md": "logic.md",
        "config.template.yaml": "config.yaml",
    }
    for template_name, out_name in mapping.items():
        src = templates / template_name
        text = src.read_text(encoding="utf-8").replace(PLACEHOLDER, name)
        (dest / out_name).write_text(text, encoding="utf-8")

    print(f"Scaffolded {dest}")
    print("Next steps (docs/10-building-a-new-pipeline.md):")
    print(f"  1. Write the purpose and declare source/output in {dest / 'spec.md'}")
    print(f"  2. Write the decision rules in {dest / 'logic.md'}")
    print(f"  3. Fill in connector details in {dest / 'config.yaml'}")
    print(f"  4. python scripts/validate_stage_file.py --config {dest / 'config.yaml'}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
