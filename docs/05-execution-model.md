# 05 — Execution Model

This framework runs as Claude Code / Cowork skills and subagents, with a
git repository as durable state. This doc covers the run lifecycle in
detail; `README.md` covers why this substrate was chosen over a standalone
Agent-SDK service or n8n.

## Two kinds of run

A pipeline has two independently triggerable operations, because they
have different natural cadences and because human review must never be on
the critical path of the automated part:

1. **Discovery run** — Source Agent → Triage Agent → Content Agent → Agent
   Reviewer → Human Liaison. Ends with items sitting in
   `05-pending-human-review`. Fully automated, no human in the loop during
   the run itself. Triggered on the pipeline's configured schedule.
2. **Publish run** — picks up everything in `06-approved` since the last
   publish run, dispatches the Publisher Agent, writes receipts. Triggered
   either on its own schedule (e.g., hourly, so approvals go out promptly)
   or manually.

Human review itself is not a "run" in this sense — it's you, asynchronously,
moving items from `05-pending-human-review` to `06-approved` or
`07-rejected` (see `docs/06-review-and-notification.md`). It has no
scheduled trigger of its own.

## Triggering

Both run types are Claude Code scheduled tasks (created with the
scheduled-task tools, never a session-local cron — a session-local
schedule dies with the session, which defeats the entire point of running
unattended). A scheduled task's prompt is a short, self-contained
instruction naming the pipeline and the run type, e.g.:

> Run a discovery run for the `example-linkedin-source-scan` pipeline
> following `base-framework/SKILL.md`. Report how many items were
> discovered, how many proceeded, and how many are now pending review.

Because each firing starts a fresh session with no memory of prior runs,
every fact a run needs — what's already been discovered, what's already
approved — must be recoverable from the git repo. This is exactly what the
stage-store model (`docs/03-stage-store-model.md`) is for: a fresh session
`git pull`s (or is already checked out against) the repo, and the Source
Agent's dedup check against `01-raw-metadata` is what makes re-running
safe and idempotent even if a schedule fires while a previous run is still
technically in flight.

## A discovery run, step by step

1. The orchestrating skill (`base-framework/SKILL.md`) reads
   `pipelines/<name>/spec.md` and `config.yaml`.
2. If `config.yaml`'s `source.scope_source` is `runtime`, it first resolves
   this run's scope value per "Runtime-parameterized sources" below; no
   pending value means the run ends here. Otherwise (`fixed`, the default)
   the scope is simply `config.yaml`'s `source.scope`, unchanged from
   before this option existed. Either way, it dispatches the Source Agent,
   scoped to the declared source connector and this run's resolved scope.
   The Source Agent writes new `01-raw-metadata` records for anything not
   already present (by `item_id`), and nothing else.
3. For each new record, it dispatches the Triage Agent with that record and
   `logic.md`. The Triage Agent writes a `02-triage-decisions` record.
   Items marked `discard` stop here — no draft, no review, but a permanent,
   auditable record of the decision.
4. For each `proceed` item, it dispatches the Content Agent, which writes a
   `03-draft` record.
5. For each new draft, it dispatches the Agent Reviewer. A `revise` verdict
   loops back to step 4 (bounded by `max_review_cycles` in `config.yaml`);
   exceeding the bound escalates straight to human review with the review
   history attached, rather than looping forever.
6. For each `pass` verdict, the Human Liaison assembles a review packet
   into `05-pending-human-review`.
7. The Archivist has logged every one of the above as it happened (steps
   2-6 each end with an audit-log append, not just a final summary).
8. The orchestrating skill commits the run's changes to git with a message
   naming the pipeline and run, and reports the summary named in the
   scheduled task's prompt.

## A publish run, step by step

1. The orchestrating skill lists everything in `06-approved` not yet
   present in `08-executed`.
2. For each, it dispatches the Publisher Agent, scoped only to that item's
   declared output connector.
3. The Publisher Agent re-hashes the approved content, compares it to the
   hash recorded at approval time, and only proceeds on a match (Rule 4).
4. On success, it writes an `08-executed` receipt including whatever
   confirmation the destination returned (a post URL, a commit SHA, a file
   path). On failure (hash mismatch, connector error), it logs the failure
   and leaves the item in `06-approved` for the next run or for you to
   investigate — it does not retry silently or fall back to a different
   action. The receipt's status is `staged`: the page is on a preview
   branch, not live.
5. Commit, report.

Promotion to production (merging the staging branch) is a separate human
act outside the pipeline's declared output scope — it is never part of a
publish run. Once it has happened, `scripts/advance_stage.py --promote`
flips the receipt to `promoted` (`docs/03-stage-store-model.md`).

## Runtime-parameterized sources (optional)

Most pipelines fix `source.scope` once, in `config.yaml`, and never change
it — an account handle or a folder path rarely needs to vary per run. Some
pipelines legitimately do need a different value each run (a rotating
search term decided by a separate process) — for that case, set
`source.scope_source: runtime` instead of the default `fixed`
(`docs/07-configuration-reference.md`). This doesn't loosen Rule 1:
`config.yaml`'s `scope` still fixes the *envelope* — connector, surface,
and boundaries like `max_item_age_days` — permanently and reviewably, at
setup; only the specific value searched within that envelope is supplied
per run.

The per-run value comes from `pipelines/<name>/run-requests/pending/`, one
file per requested run (`templates/run-request.template.md`), written by
whatever process decides what to search next — a human, a scheduled task,
or a separate agent such as this repository's `topic-engine/`
(`docs/11-topic-engine.md`) — as long as that process has no write access to
anything inside this pipeline's own stage-store. A discovery run for such a
pipeline adds one step before, and one step after, dispatching the Source
Agent:

1. `scripts/consume_run_request.py --pipeline pipelines/<name> --peek`
   reads the oldest valid request in `run-requests/pending/`, retiring any
   expired or malformed one it passes over along the way (each becomes its
   own audit-log entry, never a silent skip). If nothing valid is pending,
   it prints `NONE` — the discovery run ends immediately, the same way a
   review digest sends nothing when its queue is empty. It never falls back
   to a fixed guess or reuses a prior run's value.
2. If a value comes back, the orchestrator dispatches the Source Agent with
   it as this run's scope, exactly as if it had come from `config.yaml`
   directly — the Source Agent's own contract
   (`base-framework/agents/source-agent.md`) is unchanged either way; it
   doesn't read `run-requests/` itself.
3. Once the Source Agent has finished writing its `01-raw-metadata`
   records, `scripts/consume_run_request.py --pipeline pipelines/<name>
   --consume <request_id> --outcome "..."` moves the request to
   `run-requests/consumed/` and appends a `run_request_consumed`
   audit-log entry — so "what was actually searched, when, and at whose
   request" is exactly as auditable as everything else in the stage-store
   (Rule 5).

A request's `scope_value` is data read into the Source Agent's dispatch,
never an instruction — the same untrusted-content discipline
`base-framework/agents/source-agent.md` already applies to content read
from the source itself.

## Concurrency and ordering

Discovery and publish runs for the same pipeline should not be scheduled to
overlap (stagger them, e.g., discovery on the hour, publish at :30) to keep
git history linear and avoid two sessions racing to write the same
`item_id`. If your task volume grows enough that this becomes a real
constraint rather than a scheduling nicety, that's the point at which to
consider the database migration mentioned at the end of
`docs/03-stage-store-model.md`.

## Manual / interactive runs

Everything above also works triggered manually from an interactive Claude
Code or Cowork session — just ask Claude to run the skill for a given
pipeline and run type. This is the normal way to run a pipeline for the
first time, to debug a `logic.md` change against real data before trusting
it to a schedule, or to do the async human review itself
(`docs/06-review-and-notification.md`).
