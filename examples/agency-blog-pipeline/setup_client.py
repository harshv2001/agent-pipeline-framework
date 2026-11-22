#!/usr/bin/env python3
"""Generate a fresh, empty instance of this example for a new client.

No AI involved -- this is deterministic string substitution and file
copying, on purpose: the mechanical "replace ClientA with the real
client everywhere" step should never depend on an LLM's reliability
(see examples/agency-blog-pipeline/README.md's "Adapting this for a real
client"). What this script does NOT do, because it genuinely needs
judgment: read the client's real site and write its voice/industry
profile, or propose topics -- that's the Topic Discovery Agent's job,
done in a Claude Code session (or any AI assistant chat -- see
WALKTHROUGH.md) after this script finishes.

What gets copied verbatim (already client-agnostic, reads
client-config.yaml at runtime): every script in topic-engine/scripts/ and
pipeline/<slug>-blog-pipeline/scripts/, the schema/templates/agent-role
files, tooling/build_status_report.py.

What gets rendered from a template (client-config.yaml/.tmpl, see
_templates/): config.yaml, engine.yaml, spec.md, logic.md -- the small
set of files that genuinely need this client's name baked into their
prose, done once, mechanically, here.

What gets created fresh and empty: the ten stage-store folders, the
registry, run-requests/, source-data/, sample-client-site/ (a placeholder
for you to fill with a real site export) -- no ClientA seed data is
carried over.

Usage:
    python setup_client.py --name "Acme Bookkeeping" --domain acme.com \\
        --service "Bookkeeping|bookkeeping|/services/bookkeeping" \\
        --service "Tax Prep|tax-prep|/services/tax-prep" \\
        --out ../../../acme-blog-pipeline
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = EXAMPLE_DIR / "_templates"

STAGES = [
    "00-source-manifest", "01-raw-metadata", "02-triage-decisions", "03-draft",
    "04-agent-review", "05-pending-human-review", "06-approved", "07-rejected",
    "08-executed", "09-audit-log",
]

DEFAULT_PALETTE = {"navy": "#1E2A38", "parchment": "#F8F6F2", "accent": "#3A7CA5"}

SAMPLE_SITE_PLACEHOLDER = """This folder is empty on purpose.

Put a real, static export of the client's actual site here before
running topic-engine/scripts/analyze_site.py -- server-rendered HTML
pages (index.html, about.html, services.html, blog/index.html, and the
existing blog posts). If the real site is JS-rendered, export its
rendered HTML first (e.g. "Save Page As" after it loads, or a static
build if one exists) rather than pointing analyze_site.py at the raw
JS source.

See ../../README.md ("Adapting this for a real client") and
../../WALKTHROUGH.md for the full sequence.
"""


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"could not derive a slug from {name!r} -- pass --slug explicitly")
    return slug


def parse_service(raw: str) -> dict:
    parts = raw.split("|")
    if len(parts) != 3:
        raise ValueError(f"--service must be 'Name|slug|/url', got: {raw!r}")
    name, slug, url = (p.strip() for p in parts)
    if not name or not slug or not url:
        raise ValueError(f"--service has an empty field: {raw!r}")
    return {"slug": slug, "name": name, "url": url}


def render(template_text: str, tokens: dict[str, str]) -> str:
    out = template_text
    for key, value in tokens.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if remaining:
        raise ValueError(f"template left unresolved placeholders: {sorted(set(remaining))}")
    return out


def write_client_config(out_dir: Path, name: str, slug: str, domain: str,
                         services: list[dict], palette: dict) -> None:
    lines = [
        "client:",
        f"  name: {name}",
        f"  slug: {slug}",
        f"  domain: {domain}",
        "",
        "services:",
    ]
    for s in services:
        lines += [f"  - slug: {s['slug']}", f"    name: {s['name']}", f"    url: {s['url']}"]
    lines += [
        "",
        "brand:",
        f'  navy: "{palette["navy"]}"',
        f'  parchment: "{palette["parchment"]}"',
        f'  accent: "{palette["accent"]}"',
        "",
    ]
    (out_dir / "client-config.yaml").write_text("\n".join(lines), encoding="utf-8")


def copy_tree_verbatim(src: Path, dst: Path, skip_names: set[str]) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in skip_names:
            continue
        if item.is_dir():
            copy_tree_verbatim(item, dst / item.name, skip_names)
        else:
            shutil.copy2(item, dst / item.name)


def touch_gitkeep(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / ".gitkeep").touch()


def build_topic_engine(out_dir: Path, tokens: dict[str, str]) -> None:
    src = EXAMPLE_DIR / "topic-engine"
    dst = out_dir / "topic-engine"

    copy_tree_verbatim(
        src / "scripts", dst / "scripts",
        skip_names={"__pycache__"},
    )
    copy_tree_verbatim(src / "schema", dst / "schema", skip_names=set())
    copy_tree_verbatim(src / "templates", dst / "templates", skip_names=set())
    copy_tree_verbatim(src / "agents", dst / "agents", skip_names=set())

    engine_yaml = render((TEMPLATES_DIR / "engine.yaml.tmpl").read_text(encoding="utf-8"), tokens)
    (dst / "config").mkdir(parents=True, exist_ok=True)
    (dst / "config" / "engine.yaml").write_text(engine_yaml, encoding="utf-8")

    touch_gitkeep(dst / "registry" / "topics")
    touch_gitkeep(dst / "site-profile")


def build_pipeline(out_dir: Path, tokens: dict[str, str]) -> None:
    src = EXAMPLE_DIR / "pipeline" / "clienta-blog-pipeline"
    dst = out_dir / "pipeline" / f"{tokens['CLIENT_SLUG']}-blog-pipeline"

    copy_tree_verbatim(src / "scripts", dst / "scripts", skip_names={"__pycache__"})
    # Copied from _templates/, NOT from this example's own tooling/ -- the live ClientA
    # instance's copy has its own hand-added KNOWN_COMMENTS entries (status-report.csv
    # comments are per-instance data, same category as the stage-store itself), which
    # must never carry over into a new client's starting copy.
    (dst / "tooling").mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATES_DIR / "build_status_report.py", dst / "tooling" / "build_status_report.py")
    copy_tree_verbatim(src / "agents", dst / "agents", skip_names=set())

    for name, tmpl in (("config.yaml", "pipeline-config.yaml.tmpl"),
                        ("spec.md", "pipeline-spec.md.tmpl"),
                        ("logic.md", "pipeline-logic.md.tmpl")):
        text = render((TEMPLATES_DIR / tmpl).read_text(encoding="utf-8"), tokens)
        (dst / name).write_text(text, encoding="utf-8")

    touch_gitkeep(dst / "source-data")
    for stage in STAGES:
        touch_gitkeep(dst / "stage-store" / stage)
    touch_gitkeep(dst / "run-requests" / "pending")
    touch_gitkeep(dst / "run-requests" / "consumed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="Client's display name, e.g. 'Acme Bookkeeping'")
    parser.add_argument("--slug", default=None, help="Lowercase token for folder/file names (default: derived from --name)")
    parser.add_argument("--domain", default="", help="Client's site domain, e.g. acme.com (informational)")
    parser.add_argument("--service", dest="services", action="append", default=[],
                         metavar="Name|slug|/url",
                         help="Repeat once per service the client offers. At least one required.")
    parser.add_argument("--navy", default=DEFAULT_PALETTE["navy"])
    parser.add_argument("--parchment", default=DEFAULT_PALETTE["parchment"])
    parser.add_argument("--accent", default=DEFAULT_PALETTE["accent"])
    parser.add_argument("--out", required=True, type=Path,
                         help="Destination directory for the new instance (must not exist yet)")
    parser.add_argument("--framework-root", type=Path, default=None,
                         help="Path to a clone of agent-pipeline-framework (the one with "
                              "scripts/advance_stage.py and base-framework/SKILL.md). If given, "
                              "the pipeline half is placed directly at <framework-root>/pipelines/"
                              "<slug>-blog-pipeline/ (with its own copy of client-config.yaml) so "
                              "it can use that clone's governance scripts immediately -- the usual "
                              "way a pipeline on this framework actually runs. If omitted, the "
                              "pipeline is written under --out instead and you move it yourself.")
    args = parser.parse_args()

    if not args.services:
        print("error: pass at least one --service \"Name|slug|/url\"", file=sys.stderr)
        return 1
    try:
        services = [parse_service(s) for s in args.services]
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    slug = args.slug or slugify(args.name)
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(f"error: slug must be lowercase, hyphenated (letters/digits/hyphens, "
              f"no leading/trailing/double hyphens), got {slug!r}", file=sys.stderr)
        return 1

    out_dir = args.out.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"error: {out_dir} already exists and is not empty -- refusing to overwrite", file=sys.stderr)
        return 1

    framework_root = None
    if args.framework_root is not None:
        framework_root = args.framework_root.resolve()
        if not (framework_root / "scripts" / "advance_stage.py").exists():
            print(f"error: {framework_root} doesn't look like a clone of agent-pipeline-framework "
                  f"(no scripts/advance_stage.py there)", file=sys.stderr)
            return 1
        pipeline_dest = framework_root / "pipelines" / f"{args.slug or slugify(args.name)}-blog-pipeline"
        if pipeline_dest.exists():
            print(f"error: {pipeline_dest} already exists -- refusing to overwrite", file=sys.stderr)
            return 1

    repo_root = EXAMPLE_DIR
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    if (repo_root / ".git").exists() and str(out_dir).startswith(str(repo_root)):
        print(f"warning: --out ({out_dir}) is inside this framework's own repository. "
              f"For a real client's data, put it somewhere else -- your agency's own "
              f"private repo, not this public template -- so client content never mixes "
              f"with this project's history.", file=sys.stderr)

    tokens = {"CLIENT_NAME": args.name, "CLIENT_SLUG": slug}
    palette = {"navy": args.navy, "parchment": args.parchment, "accent": args.accent}

    out_dir.mkdir(parents=True, exist_ok=True)
    write_client_config(out_dir, args.name, slug, args.domain, services, palette)
    build_topic_engine(out_dir, tokens)
    build_pipeline(out_dir, tokens)

    sample_site = out_dir / "sample-client-site"
    sample_site.mkdir(parents=True, exist_ok=True)
    (sample_site / "README.txt").write_text(SAMPLE_SITE_PLACEHOLDER, encoding="utf-8")

    pipeline_rel = f"pipeline/{slug}-blog-pipeline"
    if framework_root is not None:
        pipeline_dest = framework_root / "pipelines" / f"{slug}-blog-pipeline"
        shutil.move(str(out_dir / "pipeline" / f"{slug}-blog-pipeline"), str(pipeline_dest))
        (out_dir / "pipeline").rmdir()
        # The loader searches upward for client-config.yaml (_client_config.py), so a copy
        # inside the pipeline folder itself (not at pipelines/, which would shadow other
        # clients' configs) is enough -- the original under --out stays the source of truth.
        (pipeline_dest / "client-config.yaml").write_bytes((out_dir / "client-config.yaml").read_bytes())
        pipeline_rel = str(pipeline_dest)

    print(f"Created {out_dir}")
    if framework_root is not None:
        print(f"Moved the pipeline half to {pipeline_rel} (with its own client-config.yaml copy) "
              f"-- it can use {framework_root}'s scripts/advance_stage.py and base-framework/SKILL.md directly.")
    else:
        print(f"  topic-engine/ and {pipeline_rel}/, both reading client-config.yaml")
        print(f"  NOTE: {pipeline_rel}/ needs scripts/advance_stage.py, scripts/validate_stage_file.py, "
              f"and base-framework/SKILL.md to actually run a pipeline dispatch -- those live in a "
              f"clone of agent-pipeline-framework, not in this bundle. Move {pipeline_rel}/ into "
              f"such a clone's pipelines/ directory (copying client-config.yaml alongside it), or "
              f"re-run this script with --framework-root <path-to-that-clone> to do it for you.")
    print()
    print("Next steps (see WALKTHROUGH.md for the full version):")
    print(f"  1. Replace {sample_site}/ with a real export of {args.name}'s actual site.")
    print(f"  2. cd {out_dir / 'topic-engine'} && pip install -r scripts/requirements.txt")
    print( "  3. python scripts/analyze_site.py --engine .")
    print( "  4. Ask your AI assistant to act as the Topic Discovery Agent "
           "(agents/topic-discovery-agent.md) and write site-profile/site-profile.md, "
           "then propose topics.")
    print( "  5. Review and approve topics, then export:")
    print(f"     python scripts/export_topics_csv.py --engine . --out {pipeline_rel}/source-data/topics.csv --run-id EXP-1")
    print(f"     python scripts/export_brand_profile.py --engine . --out {pipeline_rel}/source-data/brand-profile.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
