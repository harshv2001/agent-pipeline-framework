#!/usr/bin/env python3
"""Resolve and close out a pipeline's per-run search/scope parameter.

Mechanical enforcement for a pipeline that declares `source.scope_source:
runtime` in config.yaml (docs/07-configuration-reference.md) instead of a
fixed literal `source.scope`. Such a pipeline's actual per-run value comes
from the oldest valid file in `pipelines/<name>/run-requests/pending/`
(templates/run-request.template.md), not from config.yaml directly.

This script is called by the orchestrator (base-framework/SKILL.md), never
by the Source Agent itself -- the Source Agent subagent has no
script-execution tool grant (base-framework/agents/source-agent.md), by the
same capability-minimization principle as every other role
(docs/04-agent-roles.md). The orchestrator peeks the value, dispatches the
Source Agent with it as this run's scope exactly as if it had come from
config.yaml, and -- only after the Source Agent has finished writing
01-raw-metadata records -- consumes the request so the same value can never
be silently reused for a later run.

Usage:
    # Read-only: print the oldest valid pending request's scope_value, or
    # NONE if nothing usable is pending. Expired or malformed requests
    # encountered along the way are retired as a side effect (each becomes
    # its own audit-log entry) unless --dry-run is also passed.
    python scripts/consume_run_request.py --pipeline pipelines/<name> --peek
    python scripts/consume_run_request.py --pipeline pipelines/<name> --peek --dry-run

    # After the Source Agent has finished using the peeked value: move that
    # exact request to run-requests/consumed/ and log the outcome.
    python scripts/consume_run_request.py --pipeline pipelines/<name> --consume <request_id> --outcome "items_discovered=3"

`NONE` from --peek means there is nothing to discover this run -- per
docs/05-execution-model.md, "Runtime-parameterized sources," the discovery
run ends there. It never falls back to a fixed guess or a prior run's
value.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import append_audit_log, load_yaml, now_iso, read_item, write_item

OUTCOME_EVENTS = {
    "expired": "run_request_expired",
    "invalid": "run_request_rejected",
    "done": "run_request_consumed",
}


def _pending_dir(pipeline_dir: Path) -> Path:
    return pipeline_dir / "run-requests" / "pending"


def _consumed_dir(pipeline_dir: Path) -> Path:
    return pipeline_dir / "run-requests" / "consumed"


def _require_runtime_scope(pipeline_dir: Path) -> None:
    config = load_yaml(pipeline_dir / "config.yaml")
    scope_source = (config.get("source") or {}).get("scope_source", "fixed")
    if scope_source != "runtime":
        raise SystemExit(
            f"error: {pipeline_dir}/config.yaml has source.scope_source="
            f"{scope_source!r}, not 'runtime' -- this script is only for a "
            f"pipeline that opted into a per-run scope value "
            f"(docs/07-configuration-reference.md)."
        )


def _validate_request(fm: dict, pipeline_name: str) -> list[str]:
    errors: list[str] = []
    if fm.get("pipeline") != pipeline_name:
        errors.append(f"declares pipeline {fm.get('pipeline')!r}, expected {pipeline_name!r}")
    if not fm.get("request_id"):
        errors.append("missing 'request_id'")
    scope_value = fm.get("scope_value")
    if not isinstance(scope_value, str) or not scope_value.strip():
        errors.append("missing a non-empty string 'scope_value'")
    return errors


def _retire(pipeline_dir: Path, path: Path, fm: dict, body: str, outcome: str, detail: str) -> Path:
    dest = _consumed_dir(pipeline_dir) / path.name
    fm = dict(fm)
    fm["consumed_at"] = now_iso()
    fm["consumed_by"] = "pipeline-runner"
    fm["outcome"] = outcome
    write_item(dest, fm, body)
    path.unlink()
    append_audit_log(pipeline_dir, {
        "timestamp": now_iso(),
        "item_id": "pipeline",
        "pipeline": pipeline_dir.name,
        "event": OUTCOME_EVENTS[outcome],
        "actor": "pipeline-runner",
        "detail": f"{fm.get('request_id', path.stem)}: {detail}",
        "ref": str(dest.relative_to(pipeline_dir)),
    })
    return dest


def peek(pipeline_dir: Path, dry_run: bool = False) -> str | None:
    """Return the oldest valid pending request's scope_value. Along the
    way, retire (unless dry_run) any request that's expired or malformed
    rather than silently skipping it -- every request gets exactly one
    outcome, logged."""
    _require_runtime_scope(pipeline_dir)
    pending = _pending_dir(pipeline_dir)
    if not pending.exists():
        return None

    now = now_iso()
    for path in sorted(pending.glob("*.md")):
        fm, body = read_item(path)
        expires_at = fm.get("expires_at")
        if expires_at and str(expires_at) < now:
            if not dry_run:
                _retire(pipeline_dir, path, fm, body, "expired",
                        f"expired at {expires_at}, never dispatched")
            continue
        errors = _validate_request(fm, pipeline_dir.name)
        if errors:
            if not dry_run:
                _retire(pipeline_dir, path, fm, body, "invalid", "; ".join(errors))
            continue
        return fm["scope_value"]
    return None


def consume(pipeline_dir: Path, request_id: str, outcome: str) -> Path:
    _require_runtime_scope(pipeline_dir)
    pending = _pending_dir(pipeline_dir)
    matches = (
        [p for p in pending.glob("*.md") if read_item(p)[0].get("request_id") == request_id]
        if pending.exists() else []
    )
    if not matches:
        raise SystemExit(f"error: no pending request with request_id {request_id!r} in {pending}")
    if len(matches) > 1:
        raise SystemExit(f"error: multiple pending requests share request_id {request_id!r}: {matches}")
    path = matches[0]
    fm, body = read_item(path)
    return _retire(pipeline_dir, path, fm, body, "done", outcome)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pipeline", required=True, type=Path, help="Path to the pipeline folder")
    parser.add_argument("--peek", action="store_true", help="Print the oldest valid pending request's scope_value, or NONE")
    parser.add_argument("--dry-run", action="store_true", help="With --peek: inspect without retiring expired/invalid requests")
    parser.add_argument("--consume", metavar="REQUEST_ID", help="Move this request to consumed/ and log the outcome")
    parser.add_argument("--outcome", default="", help="For --consume: one line describing what happened, e.g. 'items_discovered=3'")
    args = parser.parse_args()

    pipeline_dir = args.pipeline
    if not (pipeline_dir / "config.yaml").exists():
        print(f"error: {pipeline_dir} does not look like a pipeline folder (no config.yaml)", file=sys.stderr)
        return 1

    if args.peek:
        value = peek(pipeline_dir, dry_run=args.dry_run)
        print(value if value is not None else "NONE")
    elif args.consume:
        if not args.outcome:
            print("error: --consume requires --outcome", file=sys.stderr)
            return 1
        dest = consume(pipeline_dir, args.consume, args.outcome)
        print(f"Consumed -> {dest}")
    else:
        print("error: nothing to do — pass --peek or --consume", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
