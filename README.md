# Agent Pipeline Framework

[![tests](https://github.com/harshv2001/agent-pipeline-framework/actions/workflows/tests.yml/badge.svg)](https://github.com/harshv2001/agent-pipeline-framework/actions/workflows/tests.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A base specification and working scripts for building **governed, multi-agent AI pipelines** —
automated content and publishing workflows, designed for **Claude Code**, where every
item passes a two-gate review (an automated agent check, then an explicit human
approval) and gets hash-locked before it ships. A complete, runnable example
is included (see "Layout" below) — this isn't only a specification.

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

This repository ships the base framework — `base-framework/`, `docs/`,
`templates/`, `scripts/` — plus one complete, runnable worked example under
`examples/` (see "Layout" below); `pipelines/` itself stays empty, ready for
yours (`docs/10-building-a-new-pipeline.md`).

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
├── examples/
│   └── agency-blog-pipeline/    Complete worked example — start here to see it running before reading the docs
│       ├── README.md             Orientation + what's already seeded in this checkout
│       ├── WALKTHROUGH.md        Step-by-step; every step marked [TERMINAL] or [ANY AI CHAT]
│       ├── ARCHITECTURE.md       This example's own diagrams (separate from docs/diagrams/)
│       ├── client-config.yaml    Name/services/brand palette — the only client-specific values
│       ├── setup_client.py       Generates a fresh instance for a real client (no AI involved)
│       ├── setup-agency-client/  Claude Code Skill wrapping setup_client.py as a conversation
│       ├── _templates/           What setup_client.py renders config.yaml/spec.md/logic.md from
│       ├── sample-client-site/   Fixture site — what the topic engine analyzes
│       ├── topic-engine/         Site analysis → proposed topics → human-approved CSV export
│       └── pipeline/
│           └── clienta-blog-pipeline/   The 10-stage governed pipeline; one item
│                                         staged for real in its own stage-store
└── pipelines/               Your own concrete pipelines go here (empty in this repo)
```

An optional upstream component — something that decides *what* a pipeline
should look for next and feeds it a run-request — is a supported pattern,
documented as a contract in `docs/11-topic-engine.md`. A generic, runnable
instance of it ships in `examples/agency-blog-pipeline/topic-engine/`;
build your own to fit your own source and config, using that as a starting
shape.

## Start here

0. **Want to see it running before reading anything?**
   [`examples/agency-blog-pipeline/`](examples/agency-blog-pipeline/) is a
   complete, runnable example — a digital agency's client-blog pipeline,
   plus an upstream topic-engine instance, with one item already carried
   through all ten stages and staged for real. Its own README walks the
   whole thing end to end, and its
   [`ARCHITECTURE.md`](examples/agency-blog-pipeline/ARCHITECTURE.md) has
   that example's own diagrams (separate from the framework-level ones
   below, which don't change per pipeline).
1. For a quick visual orientation before reading prose, see
   `docs/diagrams/00-high-level-architecture.md` (the five always-present
   components) and `docs/diagrams/01-detailed-architecture.md` (every
   stage, agent, script, and run sequence).
2. Read `docs/00-overview-and-philosophy.md` through `docs/04-agent-roles.md`
   to understand the model.
3. Read `docs/10-building-a-new-pipeline.md` for the step-by-step of
   extending the base into a real pipeline of your own.
4. Run `scripts/scaffold_pipeline.py <name>` to generate a new pipeline
   folder from the templates, then fill in `spec.md`, `logic.md`, and
   `config.yaml` — or hand a natural-language brief to the
   `pipeline-builder` skill (`base-framework/pipeline-builder/SKILL.md`) to
   do steps 1 through 5 of `docs/10-building-a-new-pipeline.md` for you.

## Status

This base framework was extracted from a private production system: a
concrete pipeline built on it has taken real content through both review
gates to a staged, then promoted, published page, across multiple scheduled
runs. What's in this repository is the generic half of that system —
governance rules, stage-store model, agent contracts, scripts — with that
original system's own pipeline-specific implementation (its actual source,
brand voice, destination, and upstream topic-sourcing component) kept
private, since those are specific to whoever is running them, not part of
the framework itself. In its place, `examples/agency-blog-pipeline/` ships
a second, generic, fictional implementation of the same shape — openly, in
this repo — so the framework isn't only described in the abstract.

Two lifecycle rules worth knowing before you operate it
(`docs/03-stage-store-model.md`, "Immutability by stage"):
`05-pending-human-review` holds only items awaiting a decision (approving or
rejecting moves the packet out), and an `08-executed` receipt reads `staged`
until a human merges to production and records it with
`advance_stage.py --promote`. The scripts' tests run with
`python -m unittest discover -s scripts/tests`.

## Limitations and Roadmap

What this framework doesn't do today, stated plainly:

- **"Append-only" and "immutable" are script-discipline guarantees, not
  cryptographic or filesystem ones** — see `docs/01-governance-rules.md`,
  "What these guarantees actually mean." Only Rule 4's content hash is
  checked automatically before every publish; the rest is enforced by
  what this framework's own scripts choose to do, not a permission
  boundary.
- **No scheduled-task or CI setup is created for you.** Steps 6–8 of
  `docs/10-building-a-new-pipeline.md` (scheduled tasks, the dry run,
  going live) are deliberately manual, human-triggered acts.
- **Automatic multi-role dispatch is Claude Code-specific.** Another AI
  assistant can act as each agent role (the role files are plain
  markdown), but only Claude Code's own Skill/subagent system currently
  chains Source → Triage → Content → Reviewer → Publisher automatically
  without a human relaying between steps — see the FAQ below and
  `examples/agency-blog-pipeline/WALKTHROUGH.md`.
- **One concrete example ships today** —
  `examples/agency-blog-pipeline/`, a CSV-sourced, full-drafting content
  pipeline. The other pipeline shapes in
  `docs/10-building-a-new-pipeline.md` (a reactive LinkedIn responder, a
  republishing pipeline, a direct website-update pipeline) are
  illustrated there, not built.
- **The stage-store is files in git, by design**
  (`docs/03-stage-store-model.md`, "Why markdown files instead of a
  database") — a deliberate tradeoff for auditability and zero hosting,
  not an oversight, but it means this doesn't scale past what a human
  can reasonably browse in a folder. A database backend once volume
  outgrows that is a named, intended option, not yet built.
- **No hosted or managed version.** This is self-hosted — you run it
  inside your own Claude Code / Cowork sessions and your own git
  repository; there's no service to sign up for.
- **Pre-1.0.** [`v0.1.0`](https://github.com/harshv2001/agent-pipeline-framework/releases/tag/v0.1.0)
  is tagged and marked a pre-release on purpose — this list above is
  exactly why: it's early, not yet a stable base to build a production
  dependency on without reading it first.

Roadmap, roughly in priority order:

1. A second worked example in a different shape — most likely the
   republishing case from `docs/10-building-a-new-pipeline.md`, since
   it's the cheapest to build well and demonstrates the lighter-weight
   end of what this framework supports.
2. A Claude Agent SDK-based orchestrator as an alternative to Claude
   Code's own Skill dispatch, for running this with no Claude Code
   session at all (see "How it runs" above).
3. Tag a `v1.0.0` once enough of this list has shrunk that "stable" would
   be an honest word for it.

Known gaps beyond this list are tracked as GitHub issues — contributions
and discussion welcome.

## Frequently asked questions

**What is this, in one sentence?**
A base specification plus working scripts for AI agent pipelines that read a
source, decide what matters, draft content, route it through an automated
review and then an explicit human approval gate, and publish — with every
decision logged and the approved content hash-locked before it ships.

**Does this require Claude Code?**
The orchestration — dispatching the Source/Triage/Content/Reviewer/Publisher
roles automatically and loading Skills — is built for Claude Code / Cowork
(see "How it runs" above). The agent-role prompts themselves
(`base-framework/agents/*.md`) are plain markdown with no Claude-specific API
calls, so another AI coding assistant can act as each role manually, one
dispatch at a time. `examples/agency-blog-pipeline/WALKTHROUGH.md` is written
to work that way with Codex, ChatGPT, or Gemini too, not only Claude Code.

**Is there a working example, or just a specification?**
[`examples/agency-blog-pipeline/`](examples/agency-blog-pipeline/) is a
complete, runnable instance — a digital agency's client-blog pipeline, with
one item carried through all ten governance stages for real, plus a script
(`setup_client.py`) that generates a fresh instance for an actual client.

**How is this different from a no-code automation tool (n8n, Zapier) or a
plain prompt chain?**
Two independent review gates before anything publishes (an automated agent
check against a written policy, then an explicit human decision), a
read-only guarantee on every source, an append-only audit log of every
decision, and a content hash that proves the published output matches
exactly what was approved — rather than a sequence of API calls with no
built-in checkpoint.

**Is this safe to use for content that carries real risk — a brand, a
regulated industry, anything with a compliance reviewer in the loop?**
That's the specific case it's built for (see "Why this exists" above and
`docs/01-governance-rules.md`). It deliberately is not optimized for
throughput — the two review gates and the hash check are friction by
design, not an oversight.

**Can I use this with GPT-4, Gemini, or another model instead of Claude?**
The governance model itself — the stage-store, the hashing, the audit log —
is plain files and scripts, not tied to any one model. The orchestration
layer (`base-framework/SKILL.md`) is written for Claude Code specifically;
using a different agent runtime means replacing that dispatch mechanism,
not the governance rules.

**Where do I start?**
See "Start here" above — `examples/agency-blog-pipeline/` to see it running
first, or `docs/00-overview-and-philosophy.md` to read the model first.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
