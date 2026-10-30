# 11 — The Topic Engine (optional upstream component, pattern only)

`topic-engine/` is a top-level component this framework supports as a
pattern, beside `base-framework/` and `pipelines/`. It is **not a
pipeline** (it has no ten-stage store and publishes nothing) and **not a
base role** (no pipeline inherits from it). It is an optional producer: it
decides *what to search for* and hands one term at a time to any pipeline
that accepts a runtime scope. Nothing in the framework requires it — a
human can write a run-request by hand, as this pattern's first real
implementation did before an engine was built.

This repository ships the interface below — what any such engine must
assume about a pipeline, and why — not a concrete `topic-engine/`
implementation; one was built against a specific brand's product catalog
and kept with that pipeline's own private configuration, same as
`pipelines/` itself (`docs/09-directory-layout.md`). Use this page as the
contract to build your own against.

## What it does, in one paragraph

A Topic Discovery Agent compares a brand's product catalog with its
published content and proposes uncovered topics, each with search terms,
into a registry. A human approves topics. An Orchestrator Agent then, at
most once a day, picks one approved search task, checks the target
pipeline's human-review queue isn't full, and drops a run-request file into
that pipeline's `run-requests/pending/`. It later reads the pipeline's
stage-store to record what became of the task, ending in *published* (the
item's `08-executed` receipt is `promoted`) or *no viable items*. The
pipeline's own two review gates are untouched; the engine never approves,
drafts, or publishes.

## The interface (what must not change silently)

The engine depends on five facts about a pipeline. All are defined by this
framework, which is the reason the two live together:

| The engine needs | Defined in |
|---|---|
| `run-requests/pending/` accepts a request file with `scope_value`, and the runner consumes it | `docs/05-execution-model.md`, "Runtime-parameterized sources" |
| `01-raw-metadata/<id>.md` has `item_id` and `created_at` | `docs/03-stage-store-model.md` |
| An item's furthest stage among `03`–`08`; an `08-executed` receipt is `staged` until a human merges, then `promoted` | `docs/03-stage-store-model.md`, "Immutability by stage" |
| `05-pending-human-review` holds only items awaiting a decision | the same section |
| `03-draft`…`08-executed` are readable, read-only | `docs/03-stage-store-model.md` |

If your engine changes any row's assumption on its own side, it needs an
equivalent contract test run against this framework's real
`scripts/advance_stage.py` and `scripts/consume_run_request.py` — the point
of a contract test is that forgetting this fails in review rather than on
live data. One prior implementation of this pattern learned that the hard
way: an earlier version of the `05` rule produced stale queue entries that
made the engine refuse to dispatch anything.

## The write boundary

The engine reads a pipeline's stage-store and writes **nothing** into a
pipeline except one new file in that pipeline's own `run-requests/pending/`
(its documented inbox). This is Rule 1's spirit applied to an upstream
producer: it must not be able to alter a pipeline's governed state. If your
engine lives in the same repository as the pipelines it feeds (as one prior
implementation did, for the reasons below), enforce this with tests rather
than relying on separate repositories to do it for you — an explicit
allowlist of the engine's file-write primitives, plus a before/after diff
of a repo-shaped tree asserting a dispatch adds exactly one inbox file and
nothing else.

## Co-locating with the pipelines it feeds

A prior implementation of this pattern started as a separate repository
from the pipelines it fed. Once built, the interface above turned out to be
the whole relationship, and keeping it in two repositories meant cross-repo
bug fixes with no atomic change, a duplicated copy of the queue logic, an
uncommitted write into another repository's working tree, and a config that
depended on one machine's folder layout. Moving it into the same repository
as its pipelines traded those costs for a shared git history (engine and
pipeline runs must not commit at the same moment) and whatever
pipeline-specific configuration the engine needs living alongside
framework-generic code — the same tradeoff `pipelines/` itself makes
(`docs/09-directory-layout.md`).
