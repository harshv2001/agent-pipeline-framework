#!/usr/bin/env python3
"""Move one item forward a stage, recording the transition to the audit log.

This is the mechanical enforcement of docs/01-governance-rules.md Rule 2
(nothing skips a stage) and Rule 4 (approved content cannot be silently
altered before publish). It is the only script that should ever move a
stage-store file — never move or edit these files by hand except the
specific, documented case of flipping a review packet's `status` field for
scripts/advance_stage.py --sync to pick up (docs/06-review-and-notification.md).

Usage:
    # Human review decisions
    python scripts/advance_stage.py --pipeline pipelines/<name> --approve <item_id>
    python scripts/advance_stage.py --pipeline pipelines/<name> --reject <item_id> --reason "..."

    # Human read the packet, likes the direction, wants changes first --
    # not a plain approve or reject. Rejects with feedback into 07-rejected
    # (still terminal -- see docs/03-stage-store-model.md) and opens a new
    # versioned 03-draft record (<item_id>-v2, -v3, ...) in one step, ready
    # for a fresh Content Agent / Agent Reviewer / Human Liaison pass:
    python scripts/advance_stage.py --pipeline pipelines/<name> --revise <item_id> --actor "human (Harsh)" --reason "more depth; confirm subheadings; less AI-slop phrasing"

    # Pick up status edits made by hand directly in 05-pending-human-review files
    python scripts/advance_stage.py --pipeline pipelines/<name> --sync

    # Generic stage transition (used by base-framework/SKILL.md between agent
    # dispatches). Every one of these transitions produces NEW content --
    # the dispatched role (Content Agent, Agent Reviewer, Human Liaison,
    # Publisher Agent) writes the destination stage-store file itself
    # first, exactly as docs/05-execution-model.md describes it. This
    # script's job here is only to validate that write and append the
    # audit-log entry (base-framework/agents/archivist-agent.md) -- it does
    # NOT overwrite what the role just wrote:
    python scripts/advance_stage.py --pipeline pipelines/<name> --move <item_id> --from 02-triage-decisions --to 03-draft --actor "content-agent v1" --detail "drafted"

    # Same, but let this script write the new content instead of writing
    # the destination file yourself first -- pass the new body as a file
    # (avoids shell-quoting multi-paragraph content):
    python scripts/advance_stage.py --pipeline pipelines/<name> --move <item_id> --from 02-triage-decisions --to 03-draft --actor "content-agent v1" --detail "drafted" --body-file /tmp/draft-body.md

    # Rare: a transition that must copy the prior stage's body forward
    # UNCHANGED (this is what --approve and --reject do internally; only
    # pass --carry-forward by hand for a pipeline-specific transition that
    # genuinely needs that exact semantics, not as a substitute for writing
    # or supplying real new content):
    python scripts/advance_stage.py --pipeline pipelines/<name> --move <item_id> --from 04-agent-review --to 05-pending-human-review --actor "human-liaison v1" --detail "packaged for review" --carry-forward

    # Log-only event, no file move (failures, policy violations)
    python scripts/advance_stage.py --pipeline pipelines/<name> --event violation --item-id <item_id> --detail "..." --actor "publisher-agent v1"

    # The human-review queue (05-pending-human-review) holds ONLY items
    # awaiting a decision: --approve/--reject (and --sync, which calls them)
    # move the packet out of 05 once it has been carried into 06/07. List
    # the queue, and clear any leftover copies from before that was true:
    python scripts/advance_stage.py --pipeline pipelines/<name> --pending
    python scripts/advance_stage.py --pipeline pipelines/<name> --cleanup-queue --dry-run
    python scripts/advance_stage.py --pipeline pipelines/<name> --cleanup-queue --actor "human (Harsh)"

    # Remove 04-agent-review scratch records left by an extra, same-run
    # automated review cycle that bypassed this script entirely (no audit
    # entry, no 03-draft counterpart) -- verified safe first: only removes
    # one whose real item already resolved at 06/07/08 elsewhere.
    python scripts/advance_stage.py --pipeline pipelines/<name> --cleanup-orphaned-reviews --dry-run
    python scripts/advance_stage.py --pipeline pipelines/<name> --cleanup-orphaned-reviews --actor "human (Harsh)"

    # End-of-run check (base-framework/SKILL.md, discovery run step 9, run
    # this before committing): fails if any item discovered this run was
    # left at 02/03/04 instead of reaching a final-or-waiting status
    # (discard, 05 pending, 06, 07, or 08). Exit code 1 if anything is stuck.
    python scripts/advance_stage.py --pipeline pipelines/<name> --check-completeness

    # Publish-time hash verification (base-framework/agents/publisher-
    # agent.md, Contract step 1): re-hashes the approved body plus any
    # manifest-listed files (images, rendered pages -- templates/review-
    # packet.template.md) against the hash locked at approval. Run this
    # before taking the declared publish action; refuse to publish on FAIL.
    python scripts/advance_stage.py --pipeline pipelines/<name> --verify-manifest <item_id>

    # After the human merges an item's staging branch to production (an act
    # outside this pipeline's declared output scope), record it so the 08
    # receipt stops saying 'staged':
    python scripts/advance_stage.py --pipeline pipelines/<name> --promote <item_id> --actor "human (Harsh)" --detail "merged stage/... into main (ff, a1b2c3d -> d4e5f6a); live at https://..." --ref "main@d4e5f6a"

NOTE: content_hash is computed here as the SHA-256 of the full review
packet body at the moment of approval, and that value is what
docs/01-governance-rules.md Rule 4 treats as authoritative going forward
(base-framework/agents/publisher-agent.md re-hashes against it). A
human-liaison-authored content_hash earlier in the packet is for the human
reviewer's own visual confirmation before approving, not the locked value.
Pipelines with stricter needs should extend this to hash only the fenced
draft section rather than the whole body.

NOTE: --move has three mutually exclusive ways to get the destination
file's content, matching the three usage examples above -- (1) the default:
the destination file already exists on disk, written directly by the role
that produced it, and this script only validates and logs; (2) --body-file:
this script writes the given file's content as the new body; (3)
--carry-forward: this script copies the FROM-stage file's body forward
unchanged, the same mechanism --approve and --reject use. Earlier versions
of this script always did (3) unconditionally, which silently clobbered
freshly authored content on every content-producing transition (draft,
agent-review, human-review, executed) with a stale copy of the previous
stage's body -- callers had to write those stage files directly and
hand-append matching audit-log entries to work around it. That workaround
should no longer be necessary; use the default (1) for any transition
where the role already wrote its own output, which is the normal case.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import (
    ALLOWED_TRANSITIONS,
    QUEUE_STAGE,
    append_audit_log,
    check_completeness,
    cleanup_orphaned_reviews,
    manifest_hash,
    next_version_id,
    now_iso,
    queue_report,
    read_item,
    rewrite_frontmatter,
    sha256_hex,
    stage_file,
    write_item,
)

EVENT_BY_TARGET_STAGE = {
    "02-triage-decisions": "decided",
    "03-draft": "drafted",
    "04-agent-review": "agent_reviewed",
    "05-pending-human-review": "packaged_for_review",
    "06-approved": "approved",
    "07-rejected": "rejected",
    "08-executed": "published",
}


def _carry_forward_frontmatter(src_path: Path, pipeline_dir: Path, to_stage: str,
                                actor: str, extra_frontmatter: dict | None) -> dict:
    fm, _ = read_item(src_path)
    fm = dict(fm)
    fm["stage"] = to_stage
    fm["produced_by"] = actor
    fm["created_at"] = now_iso()
    fm["prior_stage_ref"] = str(src_path.relative_to(pipeline_dir))
    if extra_frontmatter:
        fm.update(extra_frontmatter)
    return fm


def move(pipeline_dir: Path, item_id: str, from_stage: str, to_stage: str,
         actor: str, detail: str, extra_frontmatter: dict | None = None,
         body_file: Path | str | None = None, carry_forward: bool = False) -> Path:
    if to_stage not in ALLOWED_TRANSITIONS.get(from_stage, []):
        raise SystemExit(
            f"error: transition {from_stage} -> {to_stage} is not permitted "
            f"(docs/01-governance-rules.md Rule 2). Allowed from {from_stage}: "
            f"{ALLOWED_TRANSITIONS.get(from_stage, [])}"
        )
    if carry_forward and body_file:
        raise SystemExit("error: --carry-forward and --body-file are mutually exclusive")

    src_path = pipeline_dir / "stage-store" / from_stage / f"{item_id}.md"
    if not src_path.exists():
        raise SystemExit(f"error: {src_path} does not exist")

    dest_path = pipeline_dir / "stage-store" / to_stage / f"{item_id}.md"

    if carry_forward:
        # The prior stage's body moves forward byte-for-byte unchanged --
        # correct only for a genuine carry-forward transition (--approve,
        # --reject, or a pipeline-specific transition that explicitly asks
        # for this). docs/03-stage-store-model.md documents 06-approved and
        # 07-rejected as immutable once written, so refuse to clobber an
        # existing destination rather than silently re-deciding an item.
        if dest_path.exists():
            raise SystemExit(
                f"error: {dest_path} already exists -- {to_stage} is "
                f"immutable once written (docs/03-stage-store-model.md); "
                f"this item has already been moved there."
            )
        _, body = read_item(src_path)
        fm = _carry_forward_frontmatter(src_path, pipeline_dir, to_stage, actor, extra_frontmatter)
        write_item(dest_path, fm, body)
    elif body_file:
        # New content supplied explicitly -- this script performs the write.
        body = Path(body_file).read_text(encoding="utf-8")
        fm = _carry_forward_frontmatter(src_path, pipeline_dir, to_stage, actor, extra_frontmatter)
        write_item(dest_path, fm, body)
    else:
        # Default case, and the normal one for every content-producing
        # transition (draft, agent-review, human-review, executed): the
        # dispatched role has already written dest_path directly with its
        # own new content (docs/05-execution-model.md). This script's job
        # is to validate that write and record the transition -- NEVER to
        # overwrite freshly authored content with a mechanical copy of the
        # previous stage's body. That silent clobber was a real bug in an
        # earlier version of this function; if you hit the error below,
        # write the destination file first (recommended), or pass
        # --body-file, or pass --carry-forward if this transition really is
        # meant to copy the prior stage's body unchanged.
        if not dest_path.exists():
            raise SystemExit(
                f"error: {dest_path} does not exist. The transition "
                f"{from_stage} -> {to_stage} produces new content, so either "
                f"write it there first, pass --body-file <path>, or pass "
                f"--carry-forward if this transition is genuinely meant to "
                f"copy {src_path}'s body forward unchanged."
            )
        fm, _ = read_item(dest_path)
        if fm.get("item_id") != item_id:
            raise SystemExit(
                f"error: {dest_path} exists but its item_id "
                f"({fm.get('item_id')!r}) does not match {item_id!r}"
            )
        if fm.get("stage") != to_stage:
            raise SystemExit(
                f"error: {dest_path} exists but its 'stage' field is "
                f"{fm.get('stage')!r}, expected {to_stage!r}"
            )
        # File is left exactly as the dispatched role wrote it.

    # 05-pending-human-review is a queue: once the packet has been carried
    # into its next stage (and only then -- the destination write above
    # either succeeded or raised), consume it so the queue holds only items
    # still awaiting a decision. Every other stage keeps its record.
    if from_stage == QUEUE_STAGE:
        src_path.unlink()

    append_audit_log(pipeline_dir, {
        "timestamp": now_iso(),
        "item_id": item_id,
        "pipeline": pipeline_dir.name,
        "event": EVENT_BY_TARGET_STAGE.get(to_stage, "moved"),
        "actor": actor,
        "detail": detail,
        "ref": str(dest_path.relative_to(pipeline_dir)),
    })

    return dest_path


def approve(pipeline_dir: Path, item_id: str, actor: str) -> Path:
    src_path = pipeline_dir / "stage-store" / "05-pending-human-review" / f"{item_id}.md"
    if not src_path.exists():
        raise SystemExit(f"error: {src_path} does not exist")
    fm, body = read_item(src_path)
    locked_hash = sha256_hex(body)
    extra_frontmatter = {"status": "approved", "content_hash": locked_hash}
    manifest = fm.get("manifest")
    if manifest:
        extra_frontmatter["manifest"] = manifest
        extra_frontmatter["manifest_hash"] = manifest_hash(pipeline_dir, body, manifest)
    return move(
        pipeline_dir, item_id, "05-pending-human-review", "06-approved",
        actor=actor, detail="approved by human review",
        extra_frontmatter=extra_frontmatter,
        carry_forward=True,
    )


def verify_manifest(pipeline_dir: Path, item_id: str) -> tuple[bool, str]:
    """Re-hash a 06-approved item's body plus its declared manifest files
    against the hash locked at approval time (docs/01-governance-rules.md
    Rule 4). The Publisher Agent runs this before taking its declared
    action (base-framework/agents/publisher-agent.md, Contract step 1) --
    this is the script-enforced half of that contract step; the mismatch
    message is what it logs via `--event failure` and refuses to publish on.

    Returns (ok, message). An item with no locked `manifest_hash` (an older
    approval, or a pipeline that never declared a manifest) is reported ok
    with a note that only the body text was ever covered -- this script
    never fails an item for a gap that predates this check existing."""
    path = stage_file(pipeline_dir, "06-approved", item_id)
    if not path.exists():
        raise SystemExit(f"error: {path} does not exist -- only a 06-approved item can be verified")
    fm, body = read_item(path)
    locked = fm.get("manifest_hash")
    if not locked:
        return True, f"{item_id}: no manifest_hash locked -- only content_hash (body text) is covered"
    current = manifest_hash(pipeline_dir, body, fm.get("manifest"))
    if current == locked:
        return True, f"{item_id}: manifest hash matches ({len(fm.get('manifest') or [])} file(s) plus body)"
    return False, f"{item_id}: MANIFEST MISMATCH -- locked {locked[:16]}... but current state hashes to {current[:16]}..."


def reject(pipeline_dir: Path, item_id: str, actor: str, reason: str) -> Path:
    return move(
        pipeline_dir, item_id, "05-pending-human-review", "07-rejected",
        actor=actor, detail=f"rejected: {reason}",
        extra_frontmatter={"status": "rejected", "reason": reason},
        carry_forward=True,
    )


def revise(pipeline_dir: Path, item_id: str, actor: str, reason: str,
           from_stage: str = "05-pending-human-review") -> tuple[Path, Path]:
    """The common real-world case --approve/--reject don't cover: a human
    reads a 05-pending-human-review packet, likes the direction, but wants
    changes before approving or rejecting outright.

    This is rejected-with-feedback (docs/06-review-and-notification.md,
    "Rejection is not a dead end"), done as one step: the packet is
    rejected into 07-rejected as usual (terminal, kept for audit, per
    docs/03-stage-store-model.md -- nothing here changes that), marked
    `revision: true` so it reads as feedback rather than a final no, and a
    new versioned 03-draft record is created in the same call, `supersedes`
    pointing back at the rejection, ready for a fresh Content Agent /
    Agent Reviewer / Human Liaison pass under its own item_id (still
    bounded by max_review_cycles same as any other revision loop).

    `from_stage` defaults to the usual pre-approval case but also accepts
    "06-approved" (added 2026-10-30, scripts/_common.py's
    ALLOWED_TRANSITIONS) for a human who changes their mind after approving
    but before publish -- nothing external has happened yet, so this is
    still a same-day correction, not an undo of a real action. The detail
    text below says which case this was, so the audit log reads honestly
    either way."""
    case_note = (" (reconsidered after approval, before publish)"
                 if from_stage == "06-approved" else "")
    rejected_path = move(
        pipeline_dir, item_id, from_stage, "07-rejected",
        actor=actor, detail=f"rejected with feedback (revise){case_note}: {reason}",
        extra_frontmatter={"status": "rejected", "reason": reason, "revision": True},
        carry_forward=True,
    )
    _, body = read_item(rejected_path)
    new_item_id = next_version_id(pipeline_dir, item_id)
    draft_path = stage_file(pipeline_dir, "03-draft", new_item_id)
    if draft_path.exists():
        raise SystemExit(f"error: {draft_path} already exists")
    when = now_iso()
    write_item(draft_path, {
        "item_id": new_item_id,
        "pipeline": pipeline_dir.name,
        "stage": "03-draft",
        "status": "needs_revision",
        "produced_by": actor,
        "created_at": when,
        "prior_stage_ref": str(rejected_path.relative_to(pipeline_dir)),
        "supersedes": str(rejected_path.relative_to(pipeline_dir)),
        "revision_reason": reason,
    }, body)
    append_audit_log(pipeline_dir, {
        "timestamp": when,
        "item_id": new_item_id,
        "pipeline": pipeline_dir.name,
        "event": "revision_requested",
        "actor": actor,
        "detail": reason,
        "ref": str(draft_path.relative_to(pipeline_dir)),
    })
    return rejected_path, draft_path


def sync(pipeline_dir: Path, actor: str) -> list[Path]:
    """Pick up status edits made by hand in 05-pending-human-review files."""
    results = []
    review_dir = pipeline_dir / "stage-store" / QUEUE_STAGE
    if not review_dir.exists():
        return results
    stale_ids = {item_id for item_id, _ in queue_report(pipeline_dir)["stale"]}
    for path in sorted(review_dir.glob("*.md")):
        fm, _ = read_item(path)
        status = fm.get("status")
        item_id = fm.get("item_id") or path.stem
        if item_id in stale_ids:
            # Already decided and carried forward; approving again would hit
            # the immutability refusal and abort the whole sync. Leave it
            # for --cleanup-queue and say so.
            print(f"warning: skipping {item_id}: already at a later stage "
                  f"(leftover copy -- run --cleanup-queue)", file=sys.stderr)
            continue
        if status == "approved":
            results.append(approve(pipeline_dir, item_id, actor))
        elif status == "rejected":
            reason = fm.get("reason", "no reason given")
            results.append(reject(pipeline_dir, item_id, actor, reason))
    return results


def cleanup_queue(pipeline_dir: Path, actor: str, dry_run: bool = False) -> tuple[list[str], list[str]]:
    """Remove leftover 05-pending-human-review copies of items that were
    already approved/rejected (the pre-fix behavior of --approve/--reject,
    or a hand-written transition, left the source in place).

    Safe by construction: a 05 file is removed only if its body is
    byte-identical to the carried-forward 06-approved/07-rejected record --
    i.e. nothing in it exists nowhere else. Anything that differs, or whose
    decided record can't be found at 06/07, is reported and left alone for
    a human. Each removal is audited (event 'correction')."""
    removed: list[str] = []
    skipped: list[str] = []
    for item_id, later in queue_report(pipeline_dir)["stale"]:
        src = stage_file(pipeline_dir, QUEUE_STAGE, item_id)
        carried = next(
            (s for s in ("06-approved", "07-rejected")
             if stage_file(pipeline_dir, s, item_id).exists()),
            None,
        )
        if carried is None:
            skipped.append(f"{item_id}: found at {later} but no 06-approved/07-rejected record to verify against")
            continue
        _, src_body = read_item(src)
        _, carried_body = read_item(stage_file(pipeline_dir, carried, item_id))
        if src_body != carried_body:
            skipped.append(f"{item_id}: 05 body differs from {carried} -- not removed, needs a human look")
            continue
        if dry_run:
            removed.append(item_id)
            continue
        src.unlink()
        append_audit_log(pipeline_dir, {
            "timestamp": now_iso(),
            "item_id": item_id,
            "pipeline": pipeline_dir.name,
            "event": "correction",
            "actor": actor,
            "detail": (f"Housekeeping: removed leftover 05-pending-human-review copy; its body is "
                       f"byte-identical to the {carried} record (sha256 {sha256_hex(src_body)[:16]}...), "
                       f"so nothing was lost. The item is already at {later}."),
            "ref": str(stage_file(pipeline_dir, carried, item_id).relative_to(pipeline_dir)),
        })
        removed.append(item_id)
    return removed, skipped


def promote(pipeline_dir: Path, item_id: str, actor: str, detail: str, ref: str = "") -> Path:
    """Record that a staged item was promoted to production.

    Promotion (merging the staging branch to main) is a human action outside
    this pipeline's own declared output scope, so it has no agent of its
    own -- but the 08-executed receipt must not keep saying 'staged'
    afterward. This is the one sanctioned in-place edit of a stage-store
    record: only the receipt's `status` (monotonic staged -> promoted, never
    back), with `status_history` and the audit log recording who and when.
    The body is never touched. Idempotent in the safe direction: refuses if
    already promoted."""
    path = stage_file(pipeline_dir, "08-executed", item_id)
    if not path.exists():
        raise SystemExit(f"error: {path} does not exist -- only an executed (staged) item can be promoted")
    fm, _ = read_item(path)
    if fm.get("status") == "promoted":
        raise SystemExit(f"error: {item_id} is already promoted (see its status_history); nothing to do")
    if fm.get("status") != "staged":
        raise SystemExit(f"error: {path} has status {fm.get('status')!r}; only 'staged' can be promoted")
    when = now_iso()
    history = list(fm.get("status_history") or [{"status": "staged", "at": str(fm.get("created_at"))}])
    history.append({"status": "promoted", "at": when, "by": actor})
    fm["status"] = "promoted"
    fm["status_history"] = history
    if ref:
        fm["promotion_ref"] = ref
    rewrite_frontmatter(path, fm)  # frontmatter only; the body's bytes are untouched
    append_audit_log(pipeline_dir, {
        "timestamp": when,
        "item_id": item_id,
        "pipeline": pipeline_dir.name,
        "event": "promoted",
        "actor": actor,
        "detail": detail,
        "ref": str(path.relative_to(pipeline_dir)),
    })
    return path


def log_event(pipeline_dir: Path, item_id: str, event: str, actor: str, detail: str) -> None:
    append_audit_log(pipeline_dir, {
        "timestamp": now_iso(),
        "item_id": item_id,
        "pipeline": pipeline_dir.name,
        "event": event,
        "actor": actor,
        "detail": detail,
        "ref": "",
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pipeline", required=True, type=Path, help="Path to the pipeline folder")
    parser.add_argument("--approve", metavar="ITEM_ID")
    parser.add_argument("--reject", metavar="ITEM_ID")
    parser.add_argument("--revise", metavar="ITEM_ID",
                         help="Reject-with-feedback: move the packet to 07-rejected (terminal, "
                              "marked as feedback not a final no) and create a new versioned "
                              "03-draft record for the next attempt, in one step. Requires --reason. "
                              "Defaults to reading from 05-pending-human-review; pass "
                              "--from-stage 06-approved for a post-approval, pre-publish change of mind.")
    parser.add_argument("--from-stage", dest="revise_from_stage", default="05-pending-human-review",
                         help="With --revise only: source stage to revise from "
                              "(default 05-pending-human-review; also accepts 06-approved).")
    parser.add_argument("--reason", default="")
    parser.add_argument("--sync", action="store_true", help="Apply status edits made by hand in 05-pending-human-review")
    parser.add_argument("--move", metavar="ITEM_ID")
    parser.add_argument("--from", dest="from_stage")
    parser.add_argument("--to", dest="to_stage")
    parser.add_argument("--body-file", dest="body_file", metavar="PATH",
                         help="For --move: write this file's content as the destination's new body")
    parser.add_argument("--carry-forward", dest="carry_forward", action="store_true",
                         help="For --move: copy the FROM-stage body forward unchanged (what --approve/--reject do internally)")
    parser.add_argument("--event", choices=["failure", "violation", "correction"])
    parser.add_argument("--item-id", dest="item_id_for_event")
    parser.add_argument("--detail", default="")
    parser.add_argument("--actor", default="human")
    parser.add_argument("--pending", action="store_true",
                         help="List the human-review queue: genuinely pending items, and any leftover copies")
    parser.add_argument("--check-completeness", dest="check_completeness", action="store_true",
                         help="Fail (exit 1) if any item was left at 02/03/04 instead of a "
                              "final-or-waiting status. Run at the end of every discovery run.")
    parser.add_argument("--verify-manifest", metavar="ITEM_ID",
                         help="Re-hash a 06-approved item's body plus its declared manifest "
                              "files against the hash locked at approval. Run before publishing "
                              "(base-framework/agents/publisher-agent.md, Contract step 1).")
    parser.add_argument("--cleanup-queue", dest="cleanup_queue", action="store_true",
                         help="Remove leftover 05 copies of items already at 06/07/08 (verified byte-identical first)")
    parser.add_argument("--cleanup-orphaned-reviews", dest="cleanup_orphaned_reviews", action="store_true",
                         help="Remove 04-agent-review scratch records from an extra same-run "
                              "review cycle that never went through this script, verified "
                              "safe first (their real item already resolved at 06/07/08)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                         help="With --cleanup-queue or --cleanup-orphaned-reviews: show what "
                              "would be removed, change nothing")
    parser.add_argument("--promote", metavar="ITEM_ID",
                         help="Record that a staged item was promoted to production (08 status staged -> promoted)")
    parser.add_argument("--ref", default="", help="For --promote: commit/URL evidence, e.g. 'main@58bd26b'")
    args = parser.parse_args()

    pipeline_dir = args.pipeline
    if not (pipeline_dir / "config.yaml").exists():
        print(f"error: {pipeline_dir} does not look like a pipeline folder (no config.yaml)", file=sys.stderr)
        return 1

    if args.verify_manifest:
        ok, message = verify_manifest(pipeline_dir, args.verify_manifest)
        print(("OK: " if ok else "FAIL: ") + message)
        return 0 if ok else 1

    if args.check_completeness:
        stuck = check_completeness(pipeline_dir)
        if not stuck:
            print("OK: every item has reached a final-or-waiting status")
            return 0
        print(f"STUCK ({len(stuck)}):")
        for item_id, stage, reason in stuck:
            print(f"  {item_id} @ {stage}: {reason}")
        return 1

    if args.pending:
        report = queue_report(pipeline_dir)
        print(f"pending ({len(report['pending'])}): {', '.join(report['pending']) or '-'}")
        if report["undecided_sync"]:
            print(f"decided by hand, awaiting --sync ({len(report['undecided_sync'])}): {', '.join(report['undecided_sync'])}")
        if report["stale"]:
            print(f"WARNING leftover copies, already decided ({len(report['stale'])}): "
                  + ", ".join(f"{i}@{s}" for i, s in report["stale"]) + "  -> run --cleanup-queue")
        return 0

    if args.cleanup_queue:
        removed, skipped = cleanup_queue(pipeline_dir, args.actor, dry_run=args.dry_run)
        verb = "Would remove" if args.dry_run else "Removed"
        print(f"{verb} {len(removed)} leftover 05 copy(ies)" + (": " + ", ".join(removed) if removed else ""))
        for s in skipped:
            print(f"  not removed: {s}")
        return 1 if skipped else 0

    if args.cleanup_orphaned_reviews:
        removed, skipped = cleanup_orphaned_reviews(pipeline_dir, args.actor, dry_run=args.dry_run)
        verb = "Would remove" if args.dry_run else "Removed"
        print(f"{verb} {len(removed)} orphaned review-cycle record(s)"
              + (": " + ", ".join(removed) if removed else ""))
        for s in skipped:
            print(f"  not removed: {s}")
        return 1 if skipped else 0

    if args.promote:
        if not args.detail:
            print("error: --promote requires --detail (what was merged, where, verified how)", file=sys.stderr)
            return 1
        path = promote(pipeline_dir, args.promote, args.actor, args.detail, ref=args.ref)
        print(f"Promoted -> {path}")
        return 0

    if args.approve:
        if not args.actor or args.actor == "human":
            args.actor = "human"
        path = approve(pipeline_dir, args.approve, args.actor)
        print(f"Approved -> {path}")
    elif args.reject:
        if not args.reason:
            print("error: --reject requires --reason", file=sys.stderr)
            return 1
        path = reject(pipeline_dir, args.reject, args.actor, args.reason)
        print(f"Rejected -> {path}")
    elif args.revise:
        if not args.reason:
            print("error: --revise requires --reason", file=sys.stderr)
            return 1
        rejected_path, draft_path = revise(pipeline_dir, args.revise, args.actor, args.reason,
                                            from_stage=args.revise_from_stage)
        print(f"Rejected (with feedback) -> {rejected_path}\nNew draft -> {draft_path}")
    elif args.sync:
        paths = sync(pipeline_dir, args.actor)
        print(f"Synced {len(paths)} item(s)" + ("" if not paths else ":"))
        for p in paths:
            print(f"  {p}")
    elif args.move:
        if not args.from_stage or not args.to_stage:
            print("error: --move requires --from and --to", file=sys.stderr)
            return 1
        path = move(pipeline_dir, args.move, args.from_stage, args.to_stage,
                    actor=args.actor, detail=args.detail or f"moved to {args.to_stage}",
                    body_file=args.body_file, carry_forward=args.carry_forward)
        print(f"Moved -> {path}")
    elif args.event:
        if not args.item_id_for_event:
            print("error: --event requires --item-id", file=sys.stderr)
            return 1
        log_event(pipeline_dir, args.item_id_for_event, args.event, args.actor, args.detail)
        print(f"Logged {args.event} event for {args.item_id_for_event}")
    else:
        print("error: nothing to do — pass --approve, --reject, --revise, --sync, --move, --event, "
              "--pending, --cleanup-queue, --cleanup-orphaned-reviews, --check-completeness, "
              "--verify-manifest, or --promote", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
