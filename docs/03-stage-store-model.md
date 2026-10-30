# 03 — The Stage-Store Model

Every pipeline instance keeps its state as plain markdown files (plus a
YAML config) in a fixed folder structure under `pipelines/<name>/`, all of
it version-controlled in the framework's git repo. This is "the pipeline
storage" referred to elsewhere in these docs.

## Folder structure

```
pipelines/<name>/
├── spec.md
├── logic.md
├── config.yaml
├── agents/                       (optional role overrides — docs/02)
├── run-requests/                 (optional — only used when source.scope_source: runtime, docs/07)
│   ├── pending/
│   └── consumed/
└── stage-store/
    ├── 00-source-manifest/       Read-only pointer(s) to the source, fixed at setup
    ├── 01-raw-metadata/          One record per discovered item, immutable once written
    ├── 02-triage-decisions/      One decision record per item: proceed | discard, with rationale
    ├── 03-draft/                 Working content for items that proceeded (research notes, drafts, revisions)
    ├── 04-agent-review/          Automated review verdicts, referencing a specific draft version
    ├── 05-pending-human-review/  Review packets awaiting your decision — the notification trigger point (a queue: decided items are moved out)
    ├── 06-approved/              Human-approved items, content hash locked, ready for the Publisher Agent
    ├── 07-rejected/              Human-rejected items — terminal, kept for audit, never deleted
    ├── 08-executed/              Receipts of what was actually staged/published, with the destination's confirmation (status staged → promoted)
    └── 09-audit-log/             Append-only event log: every transition, every agent action, every decision
```

A pipeline's `spec.md` may add stages (Rule 7, `docs/01-governance-rules.md`)
but the ten above are always present, always in this order, and always
named this way — consistency across pipelines is what makes the scripts in
`scripts/` (and your own ability to jump into an unfamiliar pipeline and
understand its state) work without pipeline-specific tooling.

## File identity and naming

Every item is assigned an `item_id` the first time it's discovered
(`00-source-manifest` → `01-raw-metadata`), derived from a stable hash of
the source reference (URL, post ID, file path — whatever uniquely and
durably identifies it at the source). That `item_id` is the filename stem
in every subsequent stage: `01-raw-metadata/<item_id>.md`,
`02-triage-decisions/<item_id>.md`, and so on. This is what makes dedup
mechanical: before creating a new `01-raw-metadata` record, the Source Agent
checks whether `<item_id>.md` already exists anywhere in the stage-store for
this pipeline.

A revision opened by `scripts/advance_stage.py --revise`
(docs/06-review-and-notification.md, "Rejection is not a dead end") gets a
versioned id instead of a brand new one: `<item_id>-v2`, `-v3`, and so on,
computed by scanning every stage for the highest version already used so
the number is never reused. The unversioned record is implicitly v1. This
keeps the revision's own `item_id` stable through its own `03-draft` →
`04-agent-review` → `05-pending-human-review` cycle while still reading, at
a glance, as a later attempt at the same original item (and `supersedes`
makes the link to the prior attempt explicit either way).

## Required frontmatter

Every stage-store file (except `09-audit-log` entries, which have their own
format — see below) starts with YAML frontmatter:

```yaml
---
item_id: <stable hash>
pipeline: <pipeline name>
stage: <one of the ten stage names>
status: <stage-specific — see templates/>
source_ref: <immutable pointer back to 00-source-manifest>
produced_by: <agent role + version, e.g. triage-agent v1>
created_at: <ISO 8601 timestamp>
supersedes: <item_id-relative path, or null>
---
```

`supersedes` is how corrections happen without editing history (Rule 2): a
corrected record points at the one it replaces; the old record stays on
disk, untouched, and readers follow `supersedes` chains to the current
version.

## Immutability by stage

- `00-source-manifest` and `01-raw-metadata`: fully immutable after
  creation. If the source changes, that's a new item (new `item_id`) or a
  new pipeline run's fresh discovery — never an edit to a past record. For
  a pipeline with `source.scope_source: runtime`
  (`docs/07-configuration-reference.md`), the manifest still fixes the
  search *envelope* — connector, access, surface, boundaries — permanently
  at setup; only the specific per-run value comes from `run-requests/`
  instead, and every value used is itself audited
  (`docs/05-execution-model.md`, "Runtime-parameterized sources"). What the
  pipeline is allowed to read never changes without a reviewed config edit
  either way.
- `02-triage-decisions` through `05-pending-human-review`: immutable once
  written; a revision is a new record with `supersedes` set.
- **`05-pending-human-review` is the one queue stage.** Every other stage
  keeps its record forever (01 for dedup, 02–04 as history, 06 for the
  hash lock and publish-run pickup, 08 as the receipt), but 05 must hold
  *only items still awaiting a decision* — the review digest, `--sync`, and
  any cross-pipeline backpressure check count it. So an approval or
  rejection **moves** the packet: `advance_stage.py --approve`/`--reject`
  write the identical body into `06`/`07` (byte for byte, with
  `prior_stage_ref` pointing back and the content hash locked) and then
  remove the `05` file, so no information is lost and git history keeps the
  original. Leftover copies from before this rule are listed by
  `advance_stage.py --pending` and cleared (only if byte-identical to the
  decided record) by `--cleanup-queue`.
- `06-approved`: immutable — this is the exact, hash-locked content Rule 4
  depends on. Nothing here is ever edited; a needed change means rejecting
  and re-drafting.
- `07-rejected`, `09-audit-log`: append-only by definition, never edited.
- `08-executed`: append-only, with **one** sanctioned exception — the
  receipt's `status` moves `staged` → `promoted` when a human merges the
  item's staging branch to production (an act outside the pipeline's own
  declared output scope, so it has no agent). `advance_stage.py --promote`
  is the only way: it changes nothing but the frontmatter `status`
  (monotonic, never back), appends to `status_history`, leaves the body's
  bytes untouched, and writes a `promoted` audit entry. Anything that asks
  "was this published?" should read this status, not just whether an
  `08` file exists — a `staged` item is on a preview branch, not live.

## The audit log format

`09-audit-log/` holds one file per day (or per run), each a sequence of
append-only entries:

```yaml
---
timestamp: <ISO 8601>
item_id: <or "pipeline" for pipeline-level events like a run starting>
event: <discovered | decided | drafted | agent_reviewed | escalated | packaged_for_review | approved | rejected | revision_requested | published | promoted | publish_failed | violation | correction | run_started | run_ended | run_request_consumed | run_request_expired | run_request_rejected>
actor: <agent role + version, or your identifier for human decisions>
detail: <one line — what happened>
ref: <path to the stage-store file this event concerns>
---
```

The last three events (`run_request_*`) only occur for a pipeline with
`source.scope_source: runtime` — see `docs/05-execution-model.md`,
"Runtime-parameterized sources," and `scripts/consume_run_request.py`,
which writes them.

See `templates/audit-log-entry.template.md` for the exact fields and
`scripts/advance_stage.py`, which writes these automatically on every
stage transition it performs.

## Why markdown files instead of a database

Three reasons this framework chose files-in-git over a database or a
queue system:

1. **Git is the audit trail for free.** Every stage transition is a commit;
   `git log --follow` on an item's files gives you its full history with no
   extra tooling.
2. **It's reviewable by a human directly**, without a dashboard — you can
   open `05-pending-human-review/<item_id>.md` in any editor and read
   exactly what's being asked of you.
3. **It matches the execution model** (`docs/05-execution-model.md`):
   scheduled, stateless Claude Code sessions need externally durable state
   between runs, and a git repo is durable state with no service to host or
   keep running.

If a pipeline's volume ever outgrows "a human can browse the folder" (many
thousands of items), the model can move to a database that preserves the
same fields and immutability rules — that's a swap-out of storage
mechanics that the schema above is designed to survive without changing
`spec.md` or `logic.md` for any existing pipeline.
