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

To reject outright, with nothing further to come of it: run
`scripts/advance_stage.py --reject <item_id> --reason "..."`, or edit
`status` above to `rejected` and add a `reason` field, then commit. This
is terminal — no new draft is produced.

To ask for changes instead — you like the direction but this isn't
publishable as-is (more depth, a different angle, anything the Content
Agent should redo): run `scripts/advance_stage.py --revise <item_id>
--reason "..."`, **not** plain `--reject`. This rejects the current
packet with your feedback attached (still terminal and kept for audit,
same as any rejection) and opens a new versioned draft
(`<item_id>-v2`) for the Content Agent's next attempt, in one step. See
`docs/06-review-and-notification.md`, "Rejection is not a dead end."
