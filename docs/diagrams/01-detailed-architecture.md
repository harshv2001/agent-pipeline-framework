---
diagram: detailed-architecture
covers: every stage folder, agent role and tool grant, script, verdict branch, and run sequence
last_synced_with: base-framework/spec/pipeline-spec.schema.md v1.0; base-framework/agents/content-agent.md (context-pack-builder gate added); docs/05-execution-model.md (optional source.scope_source: runtime, run-requests/, consume_run_request.py added); docs/03-stage-store-model.md (05 is a queue consumed on decision; 08 status staged -> promoted via advance_stage.py --promote); docs/11-topic-engine.md (optional topic-engine/ producer + read-only consumer of the stage-store)
---

# Detailed Architecture

Three diagrams, together covering everything in
[`00-high-level-architecture.md`](00-high-level-architecture.md) at the
level of individual stage-store folders, agent tool grants, scripts, and
verdict branches. Node names match the file and folder names used
throughout `docs/` and `base-framework/` exactly, so this doubles as a map
from picture to file.

## 1. Structure and data flow

```mermaid
flowchart TD
    CFG["config.yaml"]
    SPEC["spec.md"]
    LOGICF["logic.md"]
    VAL{"validate_stage_file.py"}
    HALT["Halt run — report validation errors"]
    ORCH["pipeline-runner (base-framework/SKILL.md)"]

    CFG --> VAL
    SPEC --> VAL
    VAL -- "fail" --> HALT
    VAL -- "pass" --> ORCH

    subgraph CONNECTORS["Connector types (config.yaml: source / output_destinations)"]
        CT_MCP["mcp"]
        CT_CONN["connector"]
        CT_SKILL["skill"]
        CT_BROWSER["browser"]
        CT_FS["filesystem"]
    end

    SRC["Source Agent<br/>tools: Read, Grep, Glob, WebFetch, WebSearch"]
    CONNECTORS -- "access: read_only" --> SRC

    RRPEND["run-requests/pending/<br/>(optional — scope_source: runtime)"]
    TENG["topic-engine/ write_run_request.py<br/>(optional producer — its only write into a pipeline)"]
    TENG --> RRPEND
    S05 -. "backpressure: genuinely pending only" .-> TENG
    S08 -. "reconcile: receipt status (promoted = published)" .-> TENG
    CONSUME["consume_run_request.py<br/>(run by ORCH — Source Agent has no script tools)"]
    RRCONSUMED["run-requests/consumed/"]
    RRPEND -- "--peek" --> CONSUME
    CONSUME -- "NONE: end run here" --> ORCH
    CONSUME -- "resolved scope_value" --> ORCH
    ORCH -- "dispatch, this run's scope" --> SRC
    SRC -- "after writing 01-raw-metadata" --> CONSUME
    CONSUME -- "--consume: log run_request_consumed" --> RRCONSUMED

    S00["00-source-manifest/"]
    S01["01-raw-metadata/{item_id}.md"]
    SRC -- "dedup check by item_id" --> S00
    SRC -- "new item" --> S01

    TRI["Triage Agent<br/>tools: Read"]
    S01 --> TRI
    LOGICF --> TRI
    S02["02-triage-decisions/{item_id}.md"]
    TRI --> S02

    VERDICT1{"Triage verdict"}
    S02 --> VERDICT1
    TERM_DISCARD["Terminal: discarded<br/>(logged, no draft)"]
    VERDICT1 -- "discard" --> TERM_DISCARD

    CON["Content Agent<br/>tools: Read, WebFetch, WebSearch, Write, Skill"]
    VERDICT1 -- "proceed" --> CON
    CPACK{"Context pack verdict<br/>(context-pack-builder skill)"}
    CON -- "step 0: assemble pack" --> CPACK
    S03["03-draft/{item_id}.md<br/>context pack + draft"]
    CPACK -- "pass" --> S03
    CPACK -- "fail: starved or drowned" --> LIA

    REV["Agent Reviewer<br/>tools: Read — independent dispatch"]
    S03 --> REV
    S04["04-agent-review/{item_id}.md"]
    REV --> S04

    VERDICT2{"Agent review verdict<br/>vs. config.decision.max_review_cycles"}
    S04 --> VERDICT2
    VERDICT2 -- "revise, cycles remaining" --> CON
    LIA["Human Liaison<br/>tools: Read, Write"]
    VERDICT2 -- "pass" --> LIA
    VERDICT2 -- "revise, cycles exhausted -> escalate" --> LIA
    VERDICT1 -- "escalate" --> LIA

    S05["05-pending-human-review/{item_id}.md<br/>content_hash computed"]
    LIA --> S05

    DIGEST["Review digest (scheduled task)"]
    S05 -- "notify" --> DIGEST
    HUMAN(["Human — async review<br/>(in-session, or hand-edit status + commit)"])
    DIGEST --> HUMAN
    S05 -.direct file edit.-> HUMAN

    ADVAPPROVE["advance_stage.py --approve<br/>(moves the packet: 05 file removed once 06 holds it)"]
    ADVREJECT["advance_stage.py --reject --reason"]
    HUMAN -- "approve" --> ADVAPPROVE
    HUMAN -- "reject" --> ADVREJECT

    S06["06-approved/{item_id}.md<br/>content_hash LOCKED"]
    S07["07-rejected/{item_id}.md"]
    ADVAPPROVE --> S06
    ADVREJECT --> S07
    S07 -- "reject-with-feedback" --> CON

    PUB["Publisher Agent<br/>tools: connector write, scoped to action_scope"]
    S06 --> PUB
    HCHECK{"Re-hash matches<br/>locked content_hash?"}
    PUB --> HCHECK
    VIOL["Log failure/violation —<br/>stays in 06-approved, no retry"]
    HCHECK -- "no" --> VIOL
    DEST["Output connector<br/>(action_scope-limited)"]
    HCHECK -- "yes" --> DEST
    S08["08-executed/{item_id}.md<br/>(receipt, status: staged)"]
    DEST --> S08
    HUMANPROMO(["Human merges staging branch to production<br/>(outside the pipeline's output scope)"])
    ADVPROMOTE["advance_stage.py --promote<br/>(08 status staged -> promoted, audited)"]
    S08 -.-> HUMANPROMO
    HUMANPROMO --> ADVPROMOTE
    ADVPROMOTE --> S08

    ADVSTAGE["advance_stage.py<br/>(every stage transition)"]
    S09["09-audit-log/{date}.md<br/>(append-only)"]
    S00 --> ADVSTAGE
    S01 --> ADVSTAGE
    S02 --> ADVSTAGE
    S03 --> ADVSTAGE
    S04 --> ADVSTAGE
    S05 --> ADVSTAGE
    S06 --> ADVSTAGE
    S07 --> ADVSTAGE
    S08 --> ADVSTAGE
    TERM_DISCARD --> ADVSTAGE
    VIOL --> ADVSTAGE
    ADVSTAGE --> S09
```

## 2. Discovery run — dispatch order

```mermaid
sequenceDiagram
    participant Sched as Scheduled task
    participant Orch as pipeline-runner
    participant Val as validate_stage_file.py
    participant Src as Source Agent
    participant Tri as Triage Agent
    participant Cont as Content Agent
    participant Rev as Agent Reviewer
    participant Lia as Human Liaison
    participant Repo as git repo

    Sched->>Orch: fire discovery run
    Orch->>Val: validate config.yaml
    Val-->>Orch: pass
    alt source.scope_source: runtime
        Orch->>Repo: consume_run_request.py --peek (run-requests/pending/)
        alt no valid request pending
            Orch-->>Sched: report "no pending run-request" — end run
        else request resolved
            Orch->>Src: dispatch (resolved scope)
            Src->>Repo: write new 01-raw-metadata records (dedup by item_id)
            Orch->>Repo: consume_run_request.py --consume (log run_request_consumed)
        end
    else source.scope_source: fixed (default)
        Orch->>Src: dispatch (config.yaml source.scope)
        Src->>Repo: write new 01-raw-metadata records (dedup by item_id)
    end
    loop for each new item
        Orch->>Tri: dispatch (record + logic.md)
        Tri->>Repo: write 02-triage-decisions
        alt discard
            Tri-->>Orch: stop — logged, no draft
        else escalate
            Orch->>Lia: package directly, no draft
            Lia->>Repo: write 05-pending-human-review
        else proceed
            Orch->>Cont: dispatch (draft)
            Cont->>Cont: assemble context pack (context-pack-builder skill), set verdict
            alt context pack fails — starved or drowned
                Cont-->>Orch: escalate, do not draft
                Orch->>Lia: package as escalation, context pack attached
                Lia->>Repo: write 05-pending-human-review
            else context pack passes
                Cont->>Repo: write 03-draft (context pack + draft content)
                Orch->>Rev: dispatch (independent review)
                Rev->>Repo: write 04-agent-review
                alt pass
                    Orch->>Lia: package
                    Lia->>Repo: write 05-pending-human-review
                else revise, cycles remaining
                    Orch->>Cont: revise draft
                else revise, cycles exhausted
                    Orch->>Lia: package as escalation, full history attached
                    Lia->>Repo: write 05-pending-human-review
                end
            end
        end
    end
    Orch->>Repo: commit run
    Orch-->>Sched: report summary
```

## 3. Publish run — dispatch order

```mermaid
sequenceDiagram
    participant Sched as Scheduled task
    participant Orch as pipeline-runner
    participant Pub as Publisher Agent
    participant Dest as Output connector
    participant Repo as git repo

    Sched->>Orch: fire publish run
    Orch->>Repo: list 06-approved not yet in 08-executed
    loop for each approved item
        Orch->>Pub: dispatch (item, action_scope)
        Pub->>Repo: re-hash content
        alt hash matches
            Pub->>Dest: execute declared action only
            Dest-->>Pub: confirmation (URL / ID / commit SHA)
            Pub->>Repo: write 08-executed receipt
        else hash mismatch
            Pub->>Repo: log violation — leave item in 06-approved, no retry
        end
    end
    Orch->>Repo: commit run
    Orch-->>Sched: report summary
```

## Reading these diagrams

- Diagram 1 is the one to check when you're unsure which script or agent
  touches which stage folder, or what a role's exact tool grant is.
- Diagrams 2 and 3 are the ones to check when you're unsure of *order* —
  what happens before what, and where a run can legitimately stop early
  (discard, a failed hash check) versus loop (a revise cycle).
- Every node name in diagram 1 is a real path or file named identically in
  `docs/03-stage-store-model.md`, `docs/04-agent-roles.md`, and
  `scripts/`. Nothing here is a level of abstraction above those docs.

## Keeping this in sync

Update this file whenever any of the following changes: a stage is added
or reordered (`docs/03-stage-store-model.md`), a role's tool grant or
position in the sequence changes (`docs/04-agent-roles.md`,
`base-framework/agents/*.md`), a script's behavior changes
(`scripts/*.py`), or the schema version in
`base-framework/spec/pipeline-spec.schema.md` bumps in a way that changes
any of the above. Bump `last_synced_with` in this file's frontmatter, and
in `00-high-level-architecture.md`, at the same time.
