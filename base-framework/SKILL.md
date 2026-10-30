---
name: pipeline-runner
description: Orchestrates a discovery or publish run for a pipeline built on this framework. Use when asked to run, execute, or check a pipeline defined under pipelines/<name>, or to process its pending review queue.
---

# Pipeline Runner

This skill is the orchestrator described in `docs/05-execution-model.md`.
It does not itself decide anything about a pipeline's domain — it reads a
pipeline's `spec.md`, `logic.md`, and `config.yaml`, and dispatches the
seven base agent roles (`base-framework/agents/*.md`) in the fixed order
the governance rules require.

## Invocation

This skill expects to be invoked with:
- a **pipeline name** (matching a folder under `pipelines/`)
- a **run type**: `discovery`, `publish`, or `review-digest`

Example invocation text: "Run a discovery run for
`linkedin-search-to-original-post`" or "Run the review digest across all
pipelines."

If invoked with no pipeline name and run type `review-digest`, operate
across every pipeline under `pipelines/`. Every other run type requires a
specific pipeline name — refuse to guess which pipeline was meant if more
than one could plausibly match, and ask.

## Before doing anything: load context

1. Read `pipelines/<name>/spec.md`, `logic.md`, and `config.yaml`.
2. Confirm `spec.md`'s `extends_version` matches (or is compatible with)
   `base-framework/spec/pipeline-spec.schema.md`'s current version. If not,
   stop and flag the mismatch rather than proceeding on stale assumptions
   about the base contract.
3. Run `scripts/validate_stage_file.py --pipeline pipelines/<name>`.
   Do not proceed past a validation failure — a failing config means a
   governance rule (read-only sources, scoped write access, escalation
   defaults) is not correctly declared, and running anyway is exactly the
   silent-drift failure mode `docs/01-governance-rules.md` exists to
   prevent. This check also sweeps `spec.md`, `logic.md`, `config.yaml`,
   and any `agents/*.md` overrides for leftover template placeholders
   (unfilled `<...>` markers) — do not proceed past that failure either;
   an unfilled placeholder in `logic.md` is not a rule the Triage Agent can
   meaningfully apply.

## Discovery run

Follow `docs/05-execution-model.md`, "A discovery run, step by step,"
exactly. In summary, dispatch in order, one subagent invocation per role
per item (batch only within a role, never across roles):

1. **Resolve this run's scope** — only if `config.yaml`'s
   `source.scope_source` is `runtime`; skip this step entirely for the
   default `fixed` mode. Run
   `scripts/consume_run_request.py --pipeline pipelines/<name> --peek`.
   `NONE` means nothing is queued: end the run here, commit nothing new,
   and report "no pending run-request" to whoever invoked it — never fall
   back to a fixed guess or a prior run's value. Otherwise, carry the
   printed value into step 2 as this run's scope, and remember its
   `request_id` for step 3.
2. **Source Agent** (`base-framework/agents/source-agent.md`, plus
   `pipelines/<name>/agents/source-agent.md` if it exists) — scoped to
   `config.yaml`'s `source`, using the scope resolved in step 1 (which, for
   the default `fixed` mode, is just `config.yaml`'s `source.scope`
   unchanged). Writes new `01-raw-metadata` records only for `item_id`s not
   already present anywhere in this pipeline's stage-store.
3. Only if step 1 resolved a runtime scope: run
   `scripts/consume_run_request.py --pipeline pipelines/<name> --consume
   <request_id> --outcome "items_discovered=<N>"` to close it out — this
   both moves the request to `run-requests/consumed/` and logs
   `run_request_consumed` (`docs/05-execution-model.md`,
   "Runtime-parameterized sources").
4. **Triage Agent**, per new record, given that record plus `logic.md`.
   Writes `02-triage-decisions`. Route by verdict: `discard` → stop;
   `escalate` → skip straight to Human Liaison with a note that this item
   was never drafted; `proceed` → continue.
5. **Content Agent**, per `proceed` item. Writes `03-draft`.
6. **Agent Reviewer**, per new draft, as a fresh dispatch with no context
   from step 5 beyond the draft and the review policy. Writes
   `04-agent-review`. `revise` → back to step 5, incrementing a cycle
   counter; at `max_review_cycles` (`config.yaml`), escalate instead of
   looping again. `pass` → continue.
7. **Human Liaison**, per passed item. Writes `05-pending-human-review`.
8. After every step above, the dispatched role has already written its
   stage-store file directly (step text above: "Writes `03-draft`", etc.)
   — call `scripts/advance_stage.py --move` for the transition next, with
   no `--body-file`/`--carry-forward`. In this default mode it does not
   touch that file's content; it only validates the write (right `item_id`,
   right `stage`) and appends the `09-audit-log` entry, and it enforces
   that the transition is an allowed one (it will refuse, for example, a
   direct `01-raw-metadata` → `06-approved` jump, or a `--move` call for a
   stage whose file was never actually written). Only pass `--body-file`
   or `--carry-forward` for the rare transition that genuinely needs
   `advance_stage.py` itself to supply the content — see the script's own
   usage docstring.
9. Commit the resulting changes with a message naming the pipeline, run
   type, and a one-line summary (items discovered / proceeded / discarded /
   escalated / now pending review).
10. Report that same summary back to whoever invoked the run.

## Publish run

Follow `docs/05-execution-model.md`, "A publish run, step by step." In
summary: list `06-approved` items not yet in `08-executed`; for each,
dispatch the **Publisher Agent** scoped only to that item's specific
`output_destinations` entry; it re-hashes and compares before acting (Rule
4); on success write `08-executed` via `advance_stage.py`; on hash mismatch
or connector failure, log via `advance_stage.py --event failure` and leave
the item in `06-approved` — do not retry within the same run and do not
fall back to a different connector or action. Commit, report.

A publish run only ever *stages*. If the human later merges the item's
staging branch to production — an act outside the pipeline's declared
output scope, done by them or on their explicit say-so in a session — record
it with `scripts/advance_stage.py --promote <item_id> --detail "..." --ref
"main@<sha>"` so the `08-executed` receipt reads `promoted`, not `staged`
(`docs/03-stage-store-model.md`, "Immutability by stage"). Never promote on
inference; only after the merge has actually happened and been checked.

## Review digest

List the *genuinely pending* items in `05-pending-human-review` across the
requested scope (one pipeline or all): run
`scripts/advance_stage.py --pipeline pipelines/<name> --pending` per
pipeline rather than counting files — the queue holds only items awaiting a
decision, and `--pending` also flags any leftover copy of an
already-decided item (clear with `--cleanup-queue`). If empty, send no
notification and report "queue empty." If
non-empty, dispatch the notification per `docs/06-review-and-notification.md`
(counts per pipeline, oldest-item age, anything past `review_sla_hours`
flagged) and report the same summary back to the invoker.

## Handling a human review decision (interactive session)

When asked to walk through the pending queue rather than run a scheduled
digest: for each item in `05-pending-human-review`, present the full
review packet (`templates/review-packet.template.md`) — not a paraphrase —
and ask for a decision. On approval, call
`scripts/advance_stage.py --approve <item_id>` (locks the content hash,
moves to `06-approved`, and removes the packet from `05` — the queue holds
only undecided items). On rejection, call
`scripts/advance_stage.py --reject <item_id> --reason "<what they said>"`.
Commit after each decision or in a batch at the end of the session — either
is fine as long as nothing is left uncommitted when the session ends.

## What this skill must never do

- Never move an item past `05-pending-human-review` without an explicit
  approval recorded via `advance_stage.py` — not a default, not a timeout,
  not an inference from "you seemed to like this one."
- Never dispatch the Publisher Agent for anything outside `06-approved`.
- Never edit a stage-store file in place; every change is a new file plus
  an `advance_stage.py`-recorded transition. (The sole exception is
  `advance_stage.py --promote`'s status flip on an `08` receipt — frontmatter
  only, audited; `docs/03-stage-store-model.md`.)
- Never skip `validate_stage_file.py --pipeline pipelines/<name>` before a
  run because a pipeline "hasn't changed" — configs can be edited by hand
  between runs, and a leftover placeholder is exactly the kind of edit a
  human might not notice they left unfinished.
