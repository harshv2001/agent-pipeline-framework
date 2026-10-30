---
diagram: high-level-architecture
covers: base-framework as a whole — sources, orchestration, stage-store, human review, destinations
last_synced_with: base-framework/spec/pipeline-spec.schema.md v1.0; docs/07-configuration-reference.md (optional source.scope_source: runtime + run-requests/ input added); docs/11-topic-engine.md (optional topic-engine/ producer of run-requests)
---

# High-Level Architecture

The five things that always exist, for every pipeline built on this
framework, and how they connect. See
[`01-detailed-architecture.md`](01-detailed-architecture.md) for the
stage-by-stage, agent-by-agent breakdown this collapses.

```mermaid
flowchart TD
    subgraph SOURCES["External sources (read-only)"]
        SRCITEM["Website / folder / social account / search"]
    end

    subgraph SCHEDULE["Scheduled tasks"]
        TRIG_DISC["Discovery run trigger"]
        TRIG_PUB["Publish run trigger"]
        TRIG_DIGEST["Review digest trigger"]
    end

    subgraph RUNPARAM["Optional: per-run scope (source.scope_source: runtime)"]
        TOPICENG["topic-engine/ (optional)<br/>chooses the keyword; writes only<br/>to run-requests/pending/"]
        RUNREQ["run-requests/pending/<br/>(a human, or topic-engine/ —<br/>never the pipeline's own agents)"]
        TOPICENG --> RUNREQ
    end

    subgraph FRAMEWORK["Base framework + pipeline instance (Claude Code / Cowork)"]
        ORCH["pipeline-runner orchestrator skill"]
        AGENTS["7 base agent roles:<br/>Source, Triage, Content,<br/>Agent Reviewer, Human Liaison,<br/>Publisher, Archivist"]
        PIPEDEF["Pipeline definition:<br/>spec.md + logic.md + config.yaml"]
    end

    subgraph STAGESTORE["Stage-store (git repo — durable state)"]
        DISCOVER["Discovery & drafting<br/>(metadata, decisions, drafts, agent review)"]
        PENDING["Pending human review"]
        GATE["Approved / rejected"]
        EXECUTED["Executed (receipts)"]
        AUDIT["Audit log (append-only)"]
    end

    HUMAN(["You — async human review"])

    subgraph DESTINATIONS["External destinations"]
        DSTITEM["Blog / LinkedIn / X / website"]
    end

    TRIG_DISC --> ORCH
    TRIG_PUB --> ORCH
    TRIG_DIGEST --> PENDING
    RUNREQ -. "resolved once per run,<br/>never a fallback" .-> ORCH
    DISCOVER -. "read-only: items, queue,<br/>receipt status" .-> TOPICENG

    PIPEDEF -. configures .-> ORCH
    ORCH --> AGENTS

    SOURCES -- "read only" --> AGENTS
    AGENTS --> DISCOVER
    DISCOVER --> PENDING
    PENDING -- "notify" --> HUMAN
    HUMAN -- "approve / reject" --> GATE
    GATE -- "approved only" --> AGENTS
    AGENTS -- "hash-verified publish" --> DESTINATIONS
    AGENTS --> EXECUTED
    DISCOVER --> AUDIT
    PENDING --> AUDIT
    GATE --> AUDIT
    EXECUTED --> AUDIT
```

## Reading this diagram

- **Sources feed in read-only** — nothing in the framework ever writes back
  to a source (`docs/01-governance-rules.md`, Rule 1).
- **The pipeline definition configures the orchestrator, it doesn't run
  anything itself** — `spec.md`/`logic.md`/`config.yaml` are data the
  `pipeline-runner` skill reads, not code that executes.
- **Everything between discovery and "approved" sits in git**, because
  scheduled runs are stateless sessions (`docs/05-execution-model.md`).
- **Human review is the only path from "pending" to "approved"** — there is
  no automated route around it (Rule 3).
- **Destinations only ever hear from the framework once, per item, after
  approval and a hash check** (Rule 4).
- **`topic-engine/` is an optional producer, not a stage.** It reads the stage-store and writes nothing there —
  its one write is a new file in `run-requests/pending/` (enforced by tests,
  `docs/11-topic-engine.md`).
- **The per-run scope input is optional and dashed on purpose** — most
  pipelines never use it (`source.scope_source: fixed`, the default); a
  pipeline that opts into `runtime` still reads `config.yaml` for its fixed
  envelope, and this is only where the one varying value comes from
  (`docs/07-configuration-reference.md`, `docs/05-execution-model.md`).

## Keeping this in sync

This diagram should change only when something in that list above
changes — a new top-level component, a new external touchpoint, or a
change to which direction data/control flows. Day-to-day pipeline
additions (a new `pipelines/<name>/`) don't change this diagram at all,
since it's drawn at the level of the framework, not any one pipeline.
