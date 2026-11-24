#!/usr/bin/env python3
"""Clean-checkout smoke test: generate a fresh client instance, run one
item through the whole governed pipeline using fixture content (no AI,
no credentials, no network), and confirm both the happy path and the
hash-verification failure path behave correctly.

This is what CI runs (.github/workflows/tests.yml) to prove the full
documented path -- setup_client.py -> one item through discovery,
drafting, review, approval, and publish -- actually works end to end,
not just that each script's own unit tests pass in isolation. The
site-analysis and drafting steps that genuinely need an LLM's judgment
are replaced here with small, fixed fixture content written directly;
that judgment itself is exercised by a human (or an AI assistant)
following WALKTHROUGH.md, not by this script, and the topic-engine's own
bootstrap is covered by its own unit tests, not re-tested here.

Writes only inside a temporary directory; never touches a real site, a
real git remote, or any credential. Exits non-zero on the first failure.

Usage:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import datetime
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DIR = REPO_ROOT / "examples" / "agency-blog-pipeline"


def run(cmd: list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def write_stage(pipeline_dir: Path, pipeline_name: str, stage: str, item_id: str,
                 extra_frontmatter: dict, body: str) -> Path:
    fm = {
        "item_id": item_id, "pipeline": pipeline_name, "stage": stage,
        "source_ref": "source-data/topics.csv#ID=SMK-0001", "produced_by": "smoke-test",
        "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "supersedes": None,
        **extra_frontmatter,
    }
    path = pipeline_dir / "stage-store" / stage / f"{item_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip() + "\n---\n" + body
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="smoke-") as tmp:
        instance_dir = Path(tmp) / "instance"

        # 1. setup_client.py generates a fresh instance -- no AI involved.
        r = run([sys.executable, str(EXAMPLE_DIR / "setup_client.py"),
                 "--name", "Smoke Test Co", "--domain", "smoketest.invalid",
                 "--service", "Widgets|widgets|/services/widgets",
                 "--out", str(instance_dir)])
        if r.returncode != 0:
            return fail("setup_client.py did not succeed")

        pipeline_dir = instance_dir / "pipeline" / "smoke-test-co-blog-pipeline"
        if not pipeline_dir.exists():
            return fail(f"expected pipeline dir not found: {pipeline_dir}")

        config_path = pipeline_dir / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        pipeline_name = config["pipeline_name"]

        # 2. Seed a fixture topic and brand profile directly into
        # source-data/ -- skips the topic-engine's own bootstrap, which is
        # covered by its own unit tests, not this smoke test.
        (pipeline_dir / "source-data").mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "source-data" / "topics.csv").write_text(
            "ID,Track,Service Addressed,Service URL,"
            "High-Intent Search Query (Primary Keyword),Search Intent Type,"
            "Working Post Title,Secondary Keywords,Coverage Status on Blog Index,"
            "Closest Existing Post,Recommended Action,Priority,Source Basis\n"
            "SMK-0001,Widgets,widgets,/services/widgets,"
            "what is a widget,Definition,"
            "What Is a Widget and Why Do Small Businesses Use One?,"
            "widgets explained,Not covered,,Write new post,1,Smoke test fixture\n",
            encoding="utf-8",
        )
        (pipeline_dir / "source-data" / "brand-profile.md").write_text(
            "---\nclient: Smoke Test Co\n---\n\n"
            "# Smoke Test Co -- Brand Profile\n\n## Industry\n\nWidgets.\n\n"
            "## Voice\n\nPlain and direct.\n\n"
            "## Services (for CTA/backlink accuracy)\n\n"
            "| service_ref | name | url |\n|---|---|---|\n"
            "| `widgets` | Widgets | `/services/widgets` |\n",
            encoding="utf-8",
        )

        # 3. Discovery + triage (fixture content, no judgment needed).
        write_stage(pipeline_dir, pipeline_name, "01-raw-metadata", "SMK-0001",
                    {"status": "recorded"}, "## Source item\n\nFixture row SMK-0001.\n")
        write_stage(pipeline_dir, pipeline_name, "02-triage-decisions", "SMK-0001",
                    {"status": "proceed"}, "## Verdict\n\n**proceed**\n")

        # 4. Draft -- hero image generated for real via the real script.
        hero_rel = "stage-store/03-draft/SMK-0001-hero.svg"
        r = run([sys.executable, str(pipeline_dir / "scripts" / "generate_hero_svg.py"),
                 "--title", "What Is a Widget?", "--service-ref", "widgets",
                 "--out", str(pipeline_dir / hero_rel)])
        if r.returncode != 0:
            return fail("generate_hero_svg.py did not succeed")

        draft_body = ("## Post body\n\n"
                      "<p>A widget is a small, general-purpose fixture used to test a pipeline.</p>\n")
        write_stage(pipeline_dir, pipeline_name, "03-draft", "SMK-0001",
                    {"status": "drafted", "manifest": [hero_rel]}, draft_body)

        # 5. Agent review (fixture pass verdict).
        write_stage(pipeline_dir, pipeline_name, "04-agent-review", "SMK-0001",
                    {"status": "pass"}, "## Verdict\n\n**pass**\n")

        # 6. Package for human review -- content_hash computed for real.
        packet_body = (
            "## What was found\n\nFixture row SMK-0001.\n\n"
            "## What was drafted\n\n"
            "<p>A widget is a small, general-purpose fixture used to test a pipeline.</p>\n\n"
            "## Agent review\n\n**Verdict**: pass\n\n"
            "## Your decision\n\nApprove or reject.\n"
        )
        content_hash = hashlib.sha256(packet_body.encode("utf-8")).hexdigest()
        write_stage(pipeline_dir, pipeline_name, "05-pending-human-review", "SMK-0001",
                    {"status": "pending", "content_hash": content_hash,
                     "working_title": "What Is a Widget?", "manifest": [hero_rel]},
                    packet_body)

        # 7. Approve + verify -- the real framework scripts.
        r = run([sys.executable, str(REPO_ROOT / "scripts" / "advance_stage.py"),
                 "--pipeline", str(pipeline_dir), "--approve", "SMK-0001", "--actor", "smoke-test"])
        if r.returncode != 0:
            return fail("--approve did not succeed")

        r = run([sys.executable, str(REPO_ROOT / "scripts" / "advance_stage.py"),
                 "--pipeline", str(pipeline_dir), "--verify-manifest", "SMK-0001"])
        if r.returncode != 0:
            return fail("--verify-manifest did not pass for an untouched item")

        # 8. Publish -- local_files mode, no git, no network.
        config["output_mode"] = "local_files"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        r = run([sys.executable, str(pipeline_dir / "scripts" / "publish_output.py"),
                 "--item-id", "SMK-0001"])
        if r.returncode != 0:
            return fail("publish_output.py did not succeed for an untouched item")

        post_file = pipeline_dir / "output" / "SMK-0001" / "post.html"
        receipt_file = pipeline_dir / "output" / "SMK-0001" / "receipt.json"
        if not post_file.exists() or not receipt_file.exists():
            return fail(f"expected output files not found: {post_file}, {receipt_file}")
        if "widget" not in post_file.read_text(encoding="utf-8").lower():
            return fail("published post does not contain expected content")
        print("OK: happy path -- setup, discovery, draft, review, approval, and publish all succeeded")

        # 9. Confirm the hash-verification failure path: tamper with the
        # approved record and confirm publish now refuses, with nothing written.
        approved_path = pipeline_dir / "stage-store" / "06-approved" / "SMK-0001.md"
        original = approved_path.read_text(encoding="utf-8")
        approved_path.write_text(original.replace("widget", "tampered-widget"), encoding="utf-8")
        shutil.rmtree(pipeline_dir / "output" / "SMK-0001")

        r = run([sys.executable, str(pipeline_dir / "scripts" / "publish_output.py"),
                 "--item-id", "SMK-0001"])
        if r.returncode == 0:
            return fail("publish_output.py should have refused a tampered approved record")
        if (pipeline_dir / "output" / "SMK-0001").exists():
            return fail("tampered publish attempt should not have written any output")
        print("OK: tampered-content path -- publish correctly refused, nothing written")

        # 10. Confirm the refusal was also logged as a policy violation,
        # automatically (docs/01-governance-rules.md, "What happens on a
        # rule violation") -- not left for a human to log by hand.
        audit_dir = pipeline_dir / "stage-store" / "09-audit-log"
        audit_text = "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(audit_dir.glob("*.md"))
        ) if audit_dir.exists() else ""
        if "event: violation" not in audit_text or "SMK-0001" not in audit_text:
            return fail("tampered publish attempt should have auto-logged an event: violation entry")
        print("OK: tampered-content path auto-logged a policy violation to the audit log")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
