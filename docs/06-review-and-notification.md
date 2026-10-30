# 06 — Human Review and Notification

Human review is asynchronous by design: a discovery run never blocks
waiting for you, and you never have to be watching a session for a
pipeline to make progress up to the review gate. This doc covers how items
reach you and how your decision gets back into the stage-store.

## How you're notified

Rather than one notification per item (which doesn't scale past a handful
of pipelines), a separate, lightweight **digest** scheduled task runs on
its own cadence (daily is a reasonable default; configurable per
deployment, not per pipeline, since it's cross-pipeline) and:

1. Scans `05-pending-human-review/` across every pipeline under
   `pipelines/` for items still awaiting a decision
   (`scripts/advance_stage.py --pending` — approval and rejection move a
   packet out of this folder, and `--pending` flags any leftover copy of an
   already-decided item rather than counting it).
2. If anything is waiting, sends one push and/or email notification (via
   the scheduled task's built-in notification channels) summarizing: how
   many items, per pipeline, and how long the oldest has been waiting.
3. Sends nothing if the queue is empty — no daily "all clear" noise.

A pipeline whose review queue is time-sensitive (same-day relevance, e.g. a
trending topic) can additionally set a shorter `review_sla_hours` in its
`config.yaml`; the digest task flags (but does not escalate past) anything
older than that threshold as overdue.

## How you actually review

Two supported mechanics, both valid, pick whichever fits the moment:

**In a session.** Open a Claude Code or Cowork session and ask to review
the pending queue for a pipeline (or all pipelines). Claude reads each
`05-pending-human-review` packet and presents it — what was found, what was
drafted, what the agent reviewer checked and passed — and asks you to
approve or reject, one item or in bulk with per-item reasons. On your
decision, Claude runs `scripts/advance_stage.py` to move the file to
`06-approved` (recording the content hash) or `07-rejected` (recording your
stated reason), and commits.

**Directly in the repo.** Open the file in `05-pending-human-review/`
yourself, and edit its `status` field to `approved` or `rejected` (with a
`reason` field for rejections), then commit. The next scheduled run (or a
manual `scripts/advance_stage.py --sync` pass) picks up the status change,
locks the content hash on approval, and moves the file to the corresponding
folder. This path needs no live session at all — useful for reviewing from
a phone or an editor with no Claude session open.

Both paths write the same fields and produce the same audit-log entry, so
which one you used is not itself something anything downstream needs to
know.

## What a review packet contains

See `templates/review-packet.template.md` for the exact schema. In
substance, every packet gives you, without requiring you to dig elsewhere:

- What was found (the source item, linked or quoted, never re-fetched or
  re-summarized lossily at this stage).
- What was decided and why (`logic.md`'s reasoning for this specific item).
- What was drafted (the actual content, not a description of it).
- What the agent reviewer checked and its verdict, including anything it
  flagged but passed on judgment (e.g., "tone is more informal than the
  brand voice guide; judged acceptable for this format").
- The content hash that will be locked in on approval.

## Rejection is not a dead end

A `07-rejected` record can note whether it's rejected outright (this item
should never be reconsidered) or rejected-with-feedback (revise and
resubmit). For the latter, use `scripts/advance_stage.py --revise <item_id>
--reason "..."` instead of plain `--reject`: it does both steps in one
call — rejects into `07-rejected` as usual (still terminal, see
docs/03-stage-store-model.md) with `revision: true` so it reads as
feedback rather than a final no, and opens a new versioned `03-draft`
record (`<item_id>-v2`, etc., `supersedes` pointing back at the rejection)
for the Content Agent's next attempt, same as an agent-review `revise`
verdict, still bounded by `max_review_cycles`.

## Why not synchronous review

A synchronous "pause and wait for approval mid-run" model was considered
and rejected for this framework: it would require a scheduled task's
session to stay alive indefinitely waiting on you, which either times out
ungracefully or ties up a run for hours. Decoupling discovery (automated,
scheduled) from review (async, human-paced) from publish (automated,
gated on approval) means each proceeds at its own natural speed, and a
slow week of reviewing on your end never causes discovery runs to fail or
back up in a way that loses data — items just accumulate safely in
`05-pending-human-review` until you get to them.
