---
name: archivist-agent
description: Records every stage transition and agent action to the append-only audit log. Implemented as a hook called by pipeline-runner after every other role's action, via scripts/advance_stage.py, rather than dispatched as an independent subagent.
tools: [Read, Write]
---

# Archivist ("Recorder")

## Job

Guarantee that `09-audit-log/` is a complete, append-only record of every
stage transition, every agent action, every automated verdict, and every
human decision, for every item, in every pipeline. This role's contract is
documented here because it's part of the base framework's fixed governance
surface (Rule 5, `docs/01-governance-rules.md`), even though in practice
it's invoked as a deterministic hook (`scripts/advance_stage.py`) rather
than as an LLM subagent with judgment calls to make.

## When it's invoked

After every single stage transition performed by `pipeline-runner`
(`base-framework/SKILL.md`) — every Source Agent write, every Triage
verdict, every draft, every review verdict, every human decision, every
publish attempt (successful or not).

## Outputs

One append-only entry per event in `09-audit-log/`, following
`templates/audit-log-entry.template.md`'s schema exactly: timestamp,
`item_id` (or `pipeline` for pipeline-level events), `event` type, `actor`,
one-line `detail`, and a `ref` path to the stage-store file the event
concerns.

## Contract

1. Every event type listed in `templates/audit-log-entry.template.md` must
   be logged — no event type is optional or configurable out by a
   pipeline (Rule 5 makes this fixed, not overridable).
2. A logged entry is never edited or deleted, including for events later
   found to be mistaken — a correction is a new entry (`event: correction`)
   referencing the original, not an edit to it.
3. Housekeeping that changes the stage-store without changing an item's
   decision — e.g. `advance_stage.py --cleanup-queue` removing a leftover
   copy from `05-pending-human-review`, or `--promote` advancing an
   `08-executed` receipt from `staged` to `promoted` — is logged like any
   other event (`correction` / `promoted`), with enough `detail` to show
   what was checked first and that nothing was lost.
4. A policy violation detected by any role or script (an attempted
   write to a read-only source, a hash mismatch, an attempt to skip a
   stage) is logged as `event: violation` with full detail, regardless of
   whether the attempted action was actually carried out or was blocked
   before it happened.

## Why this isn't a dispatched LLM subagent

Logging what happened is a mechanical, deterministic task with no judgment
call in it — the event type, actor, and reference are already known by
whichever role or script just acted. Routing it through an LLM dispatch
would add cost and a new place for the log itself to be inaccurate, for no
benefit. `scripts/advance_stage.py` implements this contract directly; it
is documented as an agent role, not a script, because a future
implementation of this framework (a different execution substrate,
`README.md`'s note on the Agent-SDK alternative) still needs this exact
contract honored, however it's implemented there.
