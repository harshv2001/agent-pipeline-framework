"""Shared loader for client-config.yaml -- the one place every
client-specific value (name, slug, domain, services, brand palette) lives.
Never hardcode one of these in a script; read it from here instead.

Not a public API -- used by generate_hero_svg.py, init_demo_site_repo.py,
and publish_output.py.

Searches upward from this pipeline folder for client-config.yaml rather
than assuming a fixed depth -- setup_client.py writes the bundle with
topic-engine/ and pipeline/<slug>-blog-pipeline/ as siblings two levels
below client-config.yaml, but this pipeline folder is meant to be moved
into a real framework checkout's pipelines/<slug>-blog-pipeline/ to use
scripts/advance_stage.py and base-framework/SKILL.md (see
WALKTHROUGH.md) -- at which point client-config.yaml may sit one level
up (copied alongside it) instead of two. Searching, rather than hardcoding
either depth, works for both layouts.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_MAX_SEARCH_LEVELS = 6


def client_config_path(pipeline_dir: Path) -> Path:
    here = pipeline_dir.resolve()
    for _ in range(_MAX_SEARCH_LEVELS):
        candidate = here / "client-config.yaml"
        if candidate.exists():
            return candidate
        if here.parent == here:
            break
        here = here.parent
    # Nothing found -- return the conventional bundle location so the
    # caller's error message points at the expected default.
    return pipeline_dir / ".." / ".." / "client-config.yaml"


def load_client_config(pipeline_dir: Path) -> dict:
    path = client_config_path(pipeline_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"No client-config.yaml found above {pipeline_dir} (searched up to "
            f"{_MAX_SEARCH_LEVELS} parent directories) -- every instance needs one "
            f"(setup_client.py writes it; if you moved this pipeline folder, copy "
            f"client-config.yaml alongside it or keep it somewhere above it)"
        )
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def service_by_slug(client_config: dict, slug: str) -> dict | None:
    for service in client_config.get("services") or []:
        if service.get("slug") == slug:
            return service
    return None
