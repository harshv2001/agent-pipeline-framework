"""Regression tests for the human-review queue and promotion behavior in
scripts/advance_stage.py (BUG-1 / BUG-2 from BUGS-2026-10-06.md).

Run from the repo root:
    python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import advance_stage as adv  # noqa: E402
from _common import (  # noqa: E402
    STAGES, check_completeness, manifest_hash, queue_report, read_item, sha256_hex, stage_file,
    write_item,
)

PIPE = "demo-pipeline"


def make_pipeline(root: Path) -> Path:
    p = root / PIPE
    for stage in STAGES:
        (p / "stage-store" / stage).mkdir(parents=True)
    (p / "config.yaml").write_text("pipeline_name: demo-pipeline\n", encoding="utf-8")
    return p


def put(p: Path, stage: str, item_id: str, status: str, body: str = "\nthe packet body — with an em dash\n"):
    write_item(stage_file(p, stage, item_id), {
        "item_id": item_id, "pipeline": PIPE, "stage": stage, "status": status,
        "source_ref": "https://example.test/x", "produced_by": "test", "created_at": "2026-10-06T00:00:00Z",
        "supersedes": None,
    }, body)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = make_pipeline(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_approve_consumes_queue_file_and_keeps_history_stages(self):
        put(self.p, "04-agent-review", "a1", "reviewed")
        put(self.p, "05-pending-human-review", "a1", "pending")
        out = adv.approve(self.p, "a1", "human")
        self.assertTrue(out.exists())
        self.assertFalse(stage_file(self.p, "05-pending-human-review", "a1").exists())
        self.assertTrue(stage_file(self.p, "04-agent-review", "a1").exists())  # history untouched
        fm, body = read_item(out)
        self.assertEqual(fm["status"], "approved")
        self.assertEqual(fm["content_hash"], sha256_hex(body))
        self.assertEqual(queue_report(self.p)["pending"], [])

    def test_reject_consumes_queue_file(self):
        put(self.p, "05-pending-human-review", "r1", "pending")
        adv.reject(self.p, "r1", "human", "not on brand")
        self.assertFalse(stage_file(self.p, "05-pending-human-review", "r1").exists())
        self.assertTrue(stage_file(self.p, "07-rejected", "r1").exists())

    def test_move_into_queue_keeps_source_stage(self):
        put(self.p, "04-agent-review", "m1", "reviewed")
        put(self.p, "05-pending-human-review", "m1", "pending")
        adv.move(self.p, "m1", "04-agent-review", "05-pending-human-review", "liaison", "packaged")
        self.assertTrue(stage_file(self.p, "04-agent-review", "m1").exists())

    def test_failed_destination_write_does_not_lose_the_packet(self):
        put(self.p, "05-pending-human-review", "f1", "pending")
        put(self.p, "06-approved", "f1", "approved")  # destination already occupied
        with self.assertRaises(SystemExit):
            adv.approve(self.p, "f1", "human")
        self.assertTrue(stage_file(self.p, "05-pending-human-review", "f1").exists())

    def test_queue_report_classifies(self):
        put(self.p, "05-pending-human-review", "p1", "pending")
        put(self.p, "05-pending-human-review", "h1", "approved")  # hand-edited, not synced
        put(self.p, "05-pending-human-review", "s1", "pending")   # leftover
        put(self.p, "06-approved", "s1", "approved")
        rep = queue_report(self.p)
        self.assertEqual(rep["pending"], ["p1"])
        self.assertEqual(rep["undecided_sync"], ["h1"])
        self.assertEqual(rep["stale"], [("s1", "06-approved")])

    def test_sync_skips_stale_instead_of_aborting(self):
        put(self.p, "05-pending-human-review", "s1", "approved")
        put(self.p, "06-approved", "s1", "approved")           # stale + marked approved
        put(self.p, "05-pending-human-review", "ok", "approved")  # genuine hand-approval
        done = adv.sync(self.p, "human")
        self.assertEqual([d.name for d in done], ["ok.md"])
        self.assertFalse(stage_file(self.p, "05-pending-human-review", "ok").exists())
        self.assertTrue(stage_file(self.p, "05-pending-human-review", "s1").exists())  # left for cleanup

    def test_cleanup_removes_only_byte_identical_leftovers(self):
        put(self.p, "05-pending-human-review", "same", "pending", body="\nidentical\n")
        put(self.p, "06-approved", "same", "approved", body="\nidentical\n")
        put(self.p, "05-pending-human-review", "diff", "pending", body="\nversion A\n")
        put(self.p, "06-approved", "diff", "approved", body="\nversion B\n")
        put(self.p, "05-pending-human-review", "only08", "pending")
        put(self.p, "08-executed", "only08", "staged")
        removed, skipped = adv.cleanup_queue(self.p, "human", dry_run=True)
        self.assertEqual(removed, ["same"])
        self.assertTrue(stage_file(self.p, "05-pending-human-review", "same").exists())  # dry run
        removed, skipped = adv.cleanup_queue(self.p, "human")
        self.assertEqual(removed, ["same"])
        self.assertFalse(stage_file(self.p, "05-pending-human-review", "same").exists())
        self.assertTrue(stage_file(self.p, "05-pending-human-review", "diff").exists())
        self.assertTrue(stage_file(self.p, "05-pending-human-review", "only08").exists())
        self.assertEqual(len(skipped), 2)
        log = "".join(f.read_text(encoding="utf-8") for f in (self.p / "stage-store" / "09-audit-log").glob("*.md"))
        self.assertIn("removed leftover 05-pending-human-review copy", log)


class ReviseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = make_pipeline(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_revise_rejects_and_opens_versioned_draft(self):
        put(self.p, "05-pending-human-review", "cd1", "pending", body="\noriginal draft\n")
        rejected_path, draft_path = adv.revise(self.p, "cd1", "human (Harsh)", "more depth please")
        self.assertFalse(stage_file(self.p, "05-pending-human-review", "cd1").exists())
        self.assertTrue(rejected_path.exists())
        fm, body = read_item(rejected_path)
        self.assertEqual(fm["status"], "rejected")
        self.assertEqual(fm["reason"], "more depth please")
        self.assertTrue(fm["revision"])
        self.assertEqual(body, "original draft\n")

        self.assertEqual(draft_path.name, "cd1-v2.md")
        dfm, dbody = read_item(draft_path)
        self.assertEqual(dfm["item_id"], "cd1-v2")
        self.assertEqual(dfm["stage"], "03-draft")
        self.assertEqual(dfm["status"], "needs_revision")
        self.assertEqual(dfm["revision_reason"], "more depth please")
        self.assertEqual(dfm["supersedes"], str(rejected_path.relative_to(self.p)))
        self.assertEqual(dbody, body)

        log = "".join(f.read_text(encoding="utf-8") for f in (self.p / "stage-store" / "09-audit-log").glob("*.md"))
        self.assertIn("event: rejected", log)
        self.assertIn("event: revision_requested", log)

    def test_revise_again_skips_to_next_free_version(self):
        put(self.p, "05-pending-human-review", "cd1", "pending")
        adv.revise(self.p, "cd1", "human", "first round of feedback")
        put(self.p, "05-pending-human-review", "cd1-v2", "pending")
        _, draft_path = adv.revise(self.p, "cd1-v2", "human", "second round of feedback")
        self.assertEqual(draft_path.name, "cd1-v3.md")


class PromoteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = make_pipeline(Path(self._tmp.name))
        put(self.p, "08-executed", "e1", "staged", body="\nreceipt body\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_promote_leaves_body_bytes_untouched_lf_and_crlf(self):
        path = stage_file(self.p, "08-executed", "e1")
        for eol in (b"\n", b"\r\n"):
            raw = (b"---" + eol + b"item_id: e1" + eol + b"stage: 08-executed" + eol +
                   b"status: staged" + eol + b"created_at: '2026-10-06T00:00:00Z'" + eol + b"---" + eol +
                   eol + eol + b"## body \xe2\x80\x94 with leading blank lines" + eol + b"  trailing  " + eol)
            path.write_bytes(raw)
            before = raw.split(b"---" + eol, 2)[2]
            adv.promote(self.p, "e1", "human", "merged")
            after = path.read_bytes().split(b"---" + eol, 2)[2]
            self.assertEqual(before, after, f"body changed with eol={eol!r}")
            self.assertEqual(read_item(path)[0]["status"], "promoted")

    def test_promote_updates_status_history_and_audit_but_not_body(self):
        path = adv.promote(self.p, "e1", "human (Harsh)", "merged to main", ref="main@abc1234")
        fm, body = read_item(path)
        self.assertEqual(fm["status"], "promoted")
        self.assertEqual(body, "receipt body\n")
        self.assertEqual([h["status"] for h in fm["status_history"]], ["staged", "promoted"])
        self.assertEqual(fm["promotion_ref"], "main@abc1234")
        log = "".join(f.read_text(encoding="utf-8") for f in (self.p / "stage-store" / "09-audit-log").glob("*.md"))
        self.assertIn("event: promoted", log)

    def test_promote_is_monotonic(self):
        adv.promote(self.p, "e1", "human", "merged")
        with self.assertRaises(SystemExit):
            adv.promote(self.p, "e1", "human", "merged again")

    def test_promote_requires_an_executed_item(self):
        with self.assertRaises(SystemExit):
            adv.promote(self.p, "nope", "human", "x")


class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = make_pipeline(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_discarded_item_is_not_stuck(self):
        put(self.p, "02-triage-decisions", "d1", "discard")
        self.assertEqual(check_completeness(self.p), [])

    def test_proceed_with_no_draft_is_stuck(self):
        put(self.p, "02-triage-decisions", "p1", "proceed")
        stuck = check_completeness(self.p)
        self.assertEqual([s[0] for s in stuck], ["p1"])
        self.assertEqual(stuck[0][1], "02-triage-decisions")

    def test_escalate_with_no_review_packet_is_stuck(self):
        put(self.p, "02-triage-decisions", "e1", "escalate")
        stuck = check_completeness(self.p)
        self.assertEqual([s[0] for s in stuck], ["e1"])

    def test_escalate_that_reached_review_queue_is_not_stuck(self):
        put(self.p, "02-triage-decisions", "e1", "escalate")
        put(self.p, "05-pending-human-review", "e1", "pending")
        self.assertEqual(check_completeness(self.p), [])

    def test_drafted_but_never_reviewed_is_stuck(self):
        put(self.p, "02-triage-decisions", "p1", "proceed")
        put(self.p, "03-draft", "p1", "drafted")
        stuck = check_completeness(self.p)
        self.assertEqual([s[0] for s in stuck], ["p1"])
        self.assertEqual(stuck[0][1], "03-draft")

    def test_reviewed_but_never_packaged_is_stuck(self):
        put(self.p, "02-triage-decisions", "p1", "proceed")
        put(self.p, "03-draft", "p1", "drafted")
        put(self.p, "04-agent-review", "p1", "reviewed")
        stuck = check_completeness(self.p)
        self.assertEqual([s[0] for s in stuck], ["p1"])
        self.assertEqual(stuck[0][1], "04-agent-review")

    def test_fully_approved_item_is_not_stuck(self):
        put(self.p, "02-triage-decisions", "p1", "proceed")
        put(self.p, "03-draft", "p1", "drafted")
        put(self.p, "04-agent-review", "p1", "reviewed")
        put(self.p, "05-pending-human-review", "p1", "pending")
        adv.approve(self.p, "p1", "human")
        self.assertEqual(check_completeness(self.p), [])

    def test_revised_draft_without_a_02_record_is_tracked_on_its_own(self):
        # revise() creates a new item_id straight at 03-draft, bypassing 02 --
        # it must still be checked and can still be stuck on its own.
        put(self.p, "05-pending-human-review", "cd1", "pending")
        _, draft_path = adv.revise(self.p, "cd1", "human", "needs more depth")
        self.assertEqual(draft_path.stem, "cd1-v2")
        stuck = check_completeness(self.p)
        self.assertEqual([s[0] for s in stuck], ["cd1-v2"])
        self.assertEqual(stuck[0][1], "03-draft")

    def test_cli_check_completeness_exit_code(self):
        put(self.p, "02-triage-decisions", "p1", "proceed")
        old_argv = sys.argv
        try:
            sys.argv = ["advance_stage.py", "--pipeline", str(self.p), "--check-completeness"]
            self.assertEqual(adv.main(), 1)
        finally:
            sys.argv = old_argv


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = make_pipeline(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _put_with_manifest(self, item_id, manifest, body="\ndraft body\n"):
        write_item(stage_file(self.p, "05-pending-human-review", item_id), {
            "item_id": item_id, "pipeline": PIPE, "stage": "05-pending-human-review",
            "status": "pending", "source_ref": "https://example.test/x", "produced_by": "test",
            "created_at": "2026-10-06T00:00:00Z", "supersedes": None, "manifest": manifest,
        }, body)

    def test_approve_without_manifest_locks_only_content_hash(self):
        put(self.p, "05-pending-human-review", "a1", "pending")
        out = adv.approve(self.p, "a1", "human")
        fm, _ = read_item(out)
        self.assertNotIn("manifest_hash", fm)

    def test_approve_with_manifest_locks_manifest_hash(self):
        image = self.p / "assets" / "hero.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"\x89PNG fake bytes")
        self._put_with_manifest("a1", ["assets/hero.png"])
        out = adv.approve(self.p, "a1", "human")
        fm, body = read_item(out)
        self.assertEqual(fm["manifest"], ["assets/hero.png"])
        self.assertEqual(fm["manifest_hash"], manifest_hash(self.p, body, ["assets/hero.png"]))

    def test_verify_manifest_ok_when_unchanged(self):
        image = self.p / "assets" / "hero.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"original bytes")
        self._put_with_manifest("a1", ["assets/hero.png"])
        adv.approve(self.p, "a1", "human")
        ok, message = adv.verify_manifest(self.p, "a1")
        self.assertTrue(ok, message)

    def test_verify_manifest_fails_when_file_changes_after_approval(self):
        image = self.p / "assets" / "hero.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"original bytes")
        self._put_with_manifest("a1", ["assets/hero.png"])
        adv.approve(self.p, "a1", "human")
        image.write_bytes(b"swapped in after approval")
        ok, message = adv.verify_manifest(self.p, "a1")
        self.assertFalse(ok)
        self.assertIn("MISMATCH", message)

    def test_verify_manifest_fails_when_file_goes_missing(self):
        image = self.p / "assets" / "hero.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"original bytes")
        self._put_with_manifest("a1", ["assets/hero.png"])
        adv.approve(self.p, "a1", "human")
        image.unlink()
        ok, message = adv.verify_manifest(self.p, "a1")
        self.assertFalse(ok)

    def test_verify_manifest_ok_with_nothing_locked(self):
        put(self.p, "05-pending-human-review", "a1", "pending")
        adv.approve(self.p, "a1", "human")
        ok, message = adv.verify_manifest(self.p, "a1")
        self.assertTrue(ok)
        self.assertIn("no manifest_hash locked", message)

    def test_cli_verify_manifest_exit_code(self):
        image = self.p / "assets" / "hero.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"original bytes")
        self._put_with_manifest("a1", ["assets/hero.png"])
        adv.approve(self.p, "a1", "human")
        image.write_bytes(b"tampered")
        old_argv = sys.argv
        try:
            sys.argv = ["advance_stage.py", "--pipeline", str(self.p), "--verify-manifest", "a1"]
            self.assertEqual(adv.main(), 1)
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
