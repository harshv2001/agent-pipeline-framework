---
pipeline_name: clienta-blog-pipeline
version: "1"
---

# Decision Logic

This is read by the Triage Agent (`base-framework/agents/triage-agent.md`)
for every newly discovered item. Every row in `source-data/topics.csv`
has already passed through the topic-engine's own human-approval gate
(`../../topic-engine/schema/REGISTRY-SCHEMA.md`) before it ever reaches
this pipeline — so, unlike a discovery pipeline deciding *whether*
something is worth writing about, this logic only re-verifies the row's
own references still hold. It does not re-judge the topic's merit.

## Decision Inputs

The specific fields from `01-raw-metadata` this logic actually uses:

- `Service Addressed` / `Service URL` — must match an entry in
  `source-data/brand-profile.md`'s service table.
- `Closest Existing Post` — if non-blank, must be a URL that plausibly
  resolves against the client's site (per the Source Agent's grounding
  check).
- `Working Post Title` / `High-Intent Search Query (Primary Keyword)` —
  must both be present and non-empty.

## Decision Rules

Ordered — the first matching rule wins.

1. `Service Addressed` or `Service URL` doesn't match any row in
   `source-data/brand-profile.md`'s service table → `escalate`
   (the topic engine's site read may be stale, or the client's services
   changed since the topic was proposed).
2. `Closest Existing Post` is non-blank but doesn't resolve against the
   client's site → `escalate`.
3. `Working Post Title` or the primary keyword field is empty → `escalate`
   (malformed row — should not happen if `export_topics_csv.py` wrote it,
   but never silently proceed on an incomplete record).
4. Otherwise → `proceed`.

## Default Action

If no rule above matches: `escalate`.

## Escalation Triggers

Conditions that send an item straight to human review, skipping drafting
entirely, regardless of what the ordered rules above would otherwise
decide:

- Any of Rules 1–3 above.
- Ambiguous cases the rules above don't clearly resolve (this one is
  always in effect, per the base schema's Escalation Rules — restated
  here for legibility, not removed).

## Explicitly Prohibited

- Never `proceed` on a row this logic hasn't actually checked against
  `source-data/brand-profile.md` — a plausible-looking
  `Service Addressed` string is not the same as one that matches the
  table.
- Never treat a row's `Priority` value as a reason to skip Rules 1–3 —
  priority affects processing order (`spec.md`, "Requesting a run"), never
  whether the checks run at all.
