---
item_id: <same item_id throughout>
pipeline: <pipeline name>
stage: 05-pending-human-review
status: pending
source_ref: <copied from the metadata record>
content_hash: <hash of the exact draft content below — this is what gets locked in on approval>
manifest: <optional — list of file paths, relative to the pipeline folder, for any non-text output artifacts already finalized at draft time (an image, a rendered page) that should be covered by the approval hash lock alongside this body. Omit entirely for a prose-only output. See docs/01-governance-rules.md Rule 4.>
produced_by: human-liaison v1
created_at: <ISO 8601 timestamp>
supersedes: null
---

## What was found

<The source item, linked/quoted per the metadata record — not
re-summarized here.>
**Source**: <source_ref>

## What was decided, and why

<The triage verdict and rationale, copied from the decision-log record.>

## What was drafted

<The exact draft content, verbatim, in full. This is what will be
published if approved — it must match content_hash above exactly.>

<If there were revision cycles: one short note on what changed between
versions and why, not the full intermediate history.>

## Agent review

**Verdict**: pass

<Every criterion checked and what was found, including anything flagged
but not blocking — copied from the 04-agent-review record, not
summarized away.>

## Your decision

To approve: run `scripts/advance_stage.py --approve <item_id>`, or edit
`status` above to `approved` and commit.

To reject: run `scripts/advance_stage.py --reject <item_id> --reason "..."`,
or edit `status` above to `rejected` and add a `reason` field, then commit.
Note whether this is a terminal rejection or reject-with-feedback (routes
back to the Content Agent for revision).
