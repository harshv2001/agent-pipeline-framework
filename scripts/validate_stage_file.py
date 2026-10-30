#!/usr/bin/env python3
"""Validate a pipeline's config.yaml, and/or a single stage-store file's
frontmatter, against the governance rules in docs/01-governance-rules.md
and the schema in docs/03-stage-store-model.md.

Usage:
    python scripts/validate_stage_file.py --config pipelines/<name>/config.yaml
    python scripts/validate_stage_file.py --file pipelines/<name>/stage-store/01-raw-metadata/<item_id>.md

Exits non-zero and prints every problem found if validation fails. This is
meant to be run by base-framework/SKILL.md before any run, not only by
hand.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import STAGES, load_yaml, split_frontmatter

REQUIRED_FRONTMATTER_KEYS = {
    "item_id", "pipeline", "stage", "status", "source_ref", "produced_by",
    "created_at", "supersedes",
}

# Matches leftover template placeholders like <pipeline-name> or
# <replace-with-connector-ref>. Bounded length and no nested angle brackets
# or newlines so it doesn't false-positive on real content that happens to
# contain a "<" (a code sample, a comparison operator written out, HTML in
# a draft). This is a heuristic, not a parser — see validate_pipeline()'s
# docstring for what it does and doesn't catch.
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,120}>")

# Files that are legitimately empty scaffolding, not unfinished authoring.
PLACEHOLDER_SKIP_NAMES = {".gitkeep"}


def validate_config(config: dict) -> list[str]:
    errors: list[str] = []

    if not config.get("pipeline_name"):
        errors.append("config: missing pipeline_name")
    if not config.get("extends_version"):
        errors.append("config: missing extends_version")

    source = config.get("source") or {}
    if not source:
        errors.append("source: missing entirely")
    else:
        if source.get("access") != "read_only":
            errors.append(
                f"source: access must be 'read_only' (docs/01-governance-rules.md Rule 1), got {source.get('access')!r}"
            )
        for field in ("connector_type", "connector_ref", "scope"):
            if not source.get(field):
                errors.append(f"source: missing '{field}'")
        scope_source = source.get("scope_source", "fixed")
        if scope_source not in ("fixed", "runtime"):
            errors.append(
                f"source: scope_source must be 'fixed' or 'runtime' if set, got {scope_source!r} "
                "(docs/07-configuration-reference.md)"
            )

    destinations = config.get("output_destinations") or []
    if not destinations:
        errors.append("output_destinations: must declare at least one")
    for i, dest in enumerate(destinations):
        label = dest.get("name", f"#{i}")
        if dest.get("access") != "write":
            errors.append(f"output_destinations[{label}]: access must be 'write', got {dest.get('access')!r}")
        if not dest.get("action_scope"):
            errors.append(
                f"output_destinations[{label}]: missing action_scope — blanket write access is not permitted "
                "(docs/08-connectors-and-tooling.md)"
            )
        for field in ("connector_type", "connector_ref"):
            if not dest.get(field):
                errors.append(f"output_destinations[{label}]: missing '{field}'")

    decision = config.get("decision") or {}
    if decision.get("escalate_on_ambiguous") is not True:
        errors.append(
            "decision: escalate_on_ambiguous must be true — this is fixed, not configurable "
            "(docs/02-inheritance-model.md)"
        )
    cycles = decision.get("max_review_cycles")
    if not isinstance(cycles, int) or cycles < 1:
        errors.append("decision: max_review_cycles must be a positive integer")

    return errors


def validate_stage_file(frontmatter: dict) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FRONTMATTER_KEYS - frontmatter.keys()
    if missing:
        errors.append(f"frontmatter: missing required keys: {sorted(missing)}")
    stage = frontmatter.get("stage")
    if stage not in STAGES:
        errors.append(f"frontmatter: stage {stage!r} is not one of the ten base stages: {STAGES}")
    return errors


def find_placeholders(path: Path) -> list[str]:
    """Scan one text file line by line for unresolved template placeholders
    (leftover `<...>` markers from templates/*.template.md that a pipeline
    author never replaced). Returns one message per match, in
    `path:line: unresolved placeholder '<...>'` form.

    This is a heuristic regex scan, not a template-aware diff against the
    original `.template.md` — it flags anything shaped like a placeholder,
    so a pipeline that genuinely needs to write literal angle-bracket text
    (a code sample, a generic-type example) may need to rephrase it. That
    trade-off is deliberate: `spec.md`/`logic.md`/`config.yaml`/agent
    overrides are author-written prose and config, not free-form content,
    so a false positive there is rare and cheap to fix, while a missed
    placeholder is the exact silent-authoring-gap this check exists to
    catch.
    """
    errors: list[str] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for m in PLACEHOLDER_RE.finditer(line):
            errors.append(f"{path}:{i}: unresolved placeholder {m.group(0)!r}")
    return errors


def validate_pipeline(pipeline_dir: Path) -> list[str]:
    """Full pre-run check for one pipelines/<name>/ directory: config.yaml
    schema validation plus a placeholder sweep over every file a pipeline
    author is expected to have filled in by hand (spec.md, logic.md,
    config.yaml, and any agents/*.md role overrides). Does NOT walk the
    stage-store — those files are agent-produced, not author-authored, so a
    literal `<...>` there is either legitimate content or a separate bug,
    not a template leftover.
    """
    errors: list[str] = []

    config_path = pipeline_dir / "config.yaml"
    spec_path = pipeline_dir / "spec.md"
    logic_path = pipeline_dir / "logic.md"

    if not config_path.exists():
        errors.append(f"pipeline: {config_path} does not exist")
    else:
        errors += [f"[{config_path}] {e}" for e in validate_config(load_yaml(config_path))]

    if not spec_path.exists():
        errors.append(f"pipeline: {spec_path} does not exist")
    if not logic_path.exists():
        errors.append(f"pipeline: {logic_path} does not exist")

    authored_files = [p for p in (config_path, spec_path, logic_path) if p.exists()]
    agents_dir = pipeline_dir / "agents"
    if agents_dir.is_dir():
        authored_files += sorted(
            p for p in agents_dir.glob("*.md") if p.name not in PLACEHOLDER_SKIP_NAMES
        )

    for f in authored_files:
        if f.name in PLACEHOLDER_SKIP_NAMES:
            continue
        errors += find_placeholders(f)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Path to a pipeline's config.yaml")
    parser.add_argument("--file", type=Path, help="Path to a single stage-store markdown file")
    parser.add_argument(
        "--pipeline", type=Path,
        help="Path to a pipelines/<name>/ directory — runs config validation plus a "
             "leftover-template-placeholder sweep over config.yaml, spec.md, logic.md, "
             "and agents/*.md. This is what base-framework/SKILL.md runs before any run.",
    )
    args = parser.parse_args()

    if not args.config and not args.file and not args.pipeline:
        parser.error("pass --config, --file, --pipeline, or some combination")

    all_errors: list[str] = []

    if args.config:
        if not args.config.exists():
            all_errors.append(f"config: {args.config} does not exist")
        else:
            all_errors += [f"[{args.config}] {e}" for e in validate_config(load_yaml(args.config))]

    if args.file:
        if not args.file.exists():
            all_errors.append(f"file: {args.file} does not exist")
        else:
            fm, _ = split_frontmatter(args.file.read_text(encoding="utf-8"))
            all_errors += [f"[{args.file}] {e}" for e in validate_stage_file(fm)]

    if args.pipeline:
        if not args.pipeline.exists():
            all_errors.append(f"pipeline: {args.pipeline} does not exist")
        else:
            all_errors += validate_pipeline(args.pipeline)

    if all_errors:
        print("Validation FAILED:")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
