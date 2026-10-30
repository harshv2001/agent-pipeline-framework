# Agent Pipeline Framework

A base specification for building governed, multi-agent content and automation
pipelines with Claude.

## What this is

You build one pipeline (say, "scan a source, decide what matters, draft
content, get it reviewed, publish it") and the next four pipelines you need
are 80% the same shape. This framework separates that shared shape — the
stages, the governance rules, the agent roles, the audit trail — from what's
different about each pipeline — the source, the decision logic, the output.

The shared shape lives once, in `base-framework/`. A concrete pipeline you
build on top of it lives in `pipelines/<name>/` and **extends** the base the
way a subclass extends a base class in an object-oriented language: it
inherits the stage sequence, the governance rules, and the agent contracts
unmodified, and it supplies only the parts that make it specific — its
source, its decision logic, its output destinations, its schedule. See
[`docs/02-inheritance-model.md`](docs/02-inheritance-model.md) for exactly
how that works and what a pipeline is and isn't allowed to override.

This repository ships the base framework only — `base-framework/`, `docs/`,
`templates/`, `scripts/`. It does not ship any concrete pipeline; `pipelines/`
is where yours goes once you build one (`docs/10-building-a-new-pipeline.md`).

## Why this exists

Most "AI content pipeline" tooling competes on throughput. This one doesn't.
It separates agent roles and gives each only the tools it needs, requires an
automated review and then an explicit human decision before anything leaves
the pipeline, and locks approved content with a hash so what gets published
is provably what was approved. That's friction if you want volume. It's the
point if what you're publishing carries risk — a wrong claim under your
brand, a regulated industry, anyone with a compliance reviewer in the loop.

## The non-negotiables

Four rules hold for every pipeline built on this framework, with no
per-pipeline opt-out:

1. **Sources are read-only, always.** No pipeline ever writes to, deletes
   from, or modifies whatever it's scraping or reading from.
2. **Every output is staged before it exists anywhere else.** Nothing goes
   from "generated" to "published" in one step — it passes through named,
   append-only stage folders you can inspect at any point.
3. **Two independent reviews gate anything leaving the pipeline**: an
   automated agent review against the pipeline's own policy, then an
   explicit human decision. Nothing is published, posted, or written outside
   the pipeline's own storage without both.
4. **Every decision is logged.** What was found, what was decided, why, by
   which agent, and when — append-only, never edited or deleted.

Full detail in [`docs/01-governance-rules.md`](docs/01-governance-rules.md).

## How it runs

This framework is built to run as **Claude Code / Cowork skills and
subagents**, triggered either on demand or on a schedule (via scheduled
tasks), with **a git repository as the durable state store**. That pairing
was chosen deliberately over a standalone Agent-SDK service or an
n8n-orchestrated build:

- Scheduled runs are stateless, ephemeral sessions — so state has to live
  outside the session, and a git repo gives you that plus a free audit trail
  (every stage transition is a commit) with no extra infrastructure to host.
- The multi-agent orchestration (source → triage → content → review →
  publish) maps directly onto Claude Code subagents dispatched from one
  orchestrating skill — no separate workflow engine required.
- Human review is asynchronous and notification-driven (your choice, see
  [`docs/06-review-and-notification.md`](docs/06-review-and-notification.md)):
  a scheduled digest run tells you what's waiting; you review on your own
  time by editing a status field in the repo or opening a session and asking
  Claude to walk you through the queue.

If you later need this to run somewhere with no Claude Code session at all
(a bare server, triggered by a third-party webhook), the stage-store model
and governance rules transfer directly to a Claude Agent SDK
implementation — only `docs/05-execution-model.md` would need a rewrite.

## Layout

```
agent-pipeline-framework/
├── docs/                    Read these in order — 00 through 11
│   └── diagrams/            High-level and detailed architecture diagrams (Mermaid)
├── base-framework/
│   ├── SKILL.md             The orchestrator skill ("pipeline-runner")
│   ├── pipeline-builder/    Mechanizes docs/10's walkthrough from one brief
│   ├── spec/                The abstract pipeline-spec contract
│   └── agents/              The 7 base agent role definitions
├── templates/               Copy these when building a new pipeline
├── scripts/                 Scaffolding, validators, stage transitions (advance_stage.py:
│                            approve/reject/promote/check-completeness/verify-manifest,
│                            the review-queue tools), the run-request consumer;
│                            tests/ holds their unittest suite
└── pipelines/               Your concrete pipelines go here (empty in this repo)
```

An optional upstream component — something that decides *what* a pipeline
should look for next and feeds it a run-request — is a supported pattern,
documented as a contract in `docs/11-topic-engine.md`, with no
implementation shipped here; build it to fit your own source and config.

## Start here

0. For a quick visual orientation before reading prose, see
   `docs/diagrams/00-high-level-architecture.md` (the five always-present
   components) and `docs/diagrams/01-detailed-architecture.md` (every
   stage, agent, script, and run sequence).
1. Read `docs/00-overview-and-philosophy.md` through `docs/04-agent-roles.md`
   to understand the model.
2. Read `docs/10-building-a-new-pipeline.md` for the worked example and the
   step-by-step of extending the base into a real pipeline.
3. Run `scripts/scaffold_pipeline.py <name>` to generate a new pipeline
   folder from the templates, then fill in `spec.md`, `logic.md`, and
   `config.yaml` — or hand a natural-language brief to the
   `pipeline-builder` skill (`base-framework/pipeline-builder/SKILL.md`) to
   do steps 1 through 5 of `docs/10-building-a-new-pipeline.md` for you.

## Status

This base framework was extracted from a private production system: a
concrete pipeline built on it has taken real content through both review
gates to a staged, then promoted, published page, across multiple scheduled
runs. What's in this repository is the generic half of that system —
governance rules, stage-store model, agent contracts, scripts — with every
pipeline-specific implementation (source, brand voice, destination, any
upstream topic-sourcing component) kept out, since those are specific to
whoever is running them, not part of the framework itself.

Two lifecycle rules worth knowing before you operate it
(`docs/03-stage-store-model.md`, "Immutability by stage"):
`05-pending-human-review` holds only items awaiting a decision (approving or
rejecting moves the packet out), and an `08-executed` receipt reads `staged`
until a human merges to production and records it with
`advance_stage.py --promote`. The scripts' tests run with
`python -m unittest discover -s scripts/tests`.

Known gaps and where this is headed next are tracked as issues — contributions
and discussion welcome.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
