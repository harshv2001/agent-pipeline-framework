# 09 — Directory Layout Reference

The full repository layout, as delivered and as it grows once pipelines are
added:

```
pipeline-framework/                      Repo root
├── README.md
├── docs/
│   ├── 00-overview-and-philosophy.md
│   ├── 01-governance-rules.md
│   ├── 02-inheritance-model.md
│   ├── 03-stage-store-model.md
│   ├── 04-agent-roles.md
│   ├── 05-execution-model.md
│   ├── 06-review-and-notification.md
│   ├── 07-configuration-reference.md
│   ├── 08-connectors-and-tooling.md
│   ├── 09-directory-layout.md           This file
│   ├── 10-building-a-new-pipeline.md
│   ├── 11-topic-engine.md
│   └── diagrams/
│       ├── 00-high-level-architecture.md
│       └── 01-detailed-architecture.md
├── base-framework/
│   ├── SKILL.md                         The pipeline-runner orchestrator skill
│   ├── pipeline-builder/
│   │   └── SKILL.md                     Mechanizes docs/10's walkthrough from one brief
│   ├── spec/
│   │   └── pipeline-spec.schema.md      The abstract base contract
│   └── agents/
│       ├── source-agent.md
│       ├── triage-agent.md
│       ├── content-agent.md
│       ├── agent-reviewer.md
│       ├── human-liaison.md
│       ├── publisher-agent.md
│       └── archivist-agent.md
├── templates/
│   ├── pipeline-spec.template.md
│   ├── logic.template.md
│   ├── config.template.yaml
│   ├── context-pack.template.md
│   ├── metadata-record.template.md
│   ├── decision-log.template.md
│   ├── review-packet.template.md
│   ├── agent-override.template.md
│   └── audit-log-entry.template.md
├── topic-engine/                        Optional upstream component (docs/11-topic-engine.md)
│   ├── ARCHITECTURE.md                  Design + the engine <-> pipeline contract
│   ├── README.md, SKILL.md, agents/, schema/, templates/
│   ├── config/engine.yaml               Caps, kill switch, surface -> pipeline routes
│   ├── registry/                        topics/*.md, ledger.csv (append-only), registry.csv (generated)
│   ├── audit/, handoff/, site-index/    Run log; assisted-mode hand-offs; git-ignored cache
│   └── scripts/                         validate_registry, backpressure, reconcile, write_run_request, ...
│       └── tests/                       incl. the write-boundary and pipeline-contract tests
├── scripts/
│   ├── _common.py                       Shared helpers (frontmatter, hashing, stage lookups)
│   ├── scaffold_pipeline.py
│   ├── validate_stage_file.py
│   ├── advance_stage.py                 Transitions, approve/reject/promote,
│   │                                     --pending / --cleanup-queue / --check-completeness / --verify-manifest
│   ├── consume_run_request.py           Resolves/consumes a runtime scope (docs/05)
│   └── tests/                           unittest suite for the scripts above
└── pipelines/
    └── <name>/                          One folder per concrete pipeline
        ├── spec.md
        ├── logic.md
        ├── config.yaml
        ├── agents/                      Optional role overrides
        ├── run-requests/                Scaffolded for every pipeline; only
        │   ├── pending/                 populated/consumed if config.yaml's
        │   └── consumed/                source.scope_source is 'runtime' (docs/07)
        └── stage-store/
            ├── 00-source-manifest/
            ├── 01-raw-metadata/
            ├── 02-triage-decisions/
            ├── 03-draft/
            ├── 04-agent-review/
            ├── 05-pending-human-review/
            ├── 06-approved/
            ├── 07-rejected/
            ├── 08-executed/
            └── 09-audit-log/
```

## Naming conventions

- Pipeline folder names: lowercase, hyphenated, and specific about both the
  source and the destination where both apply —
  `linkedin-search-to-blog-post`, not `linkedin-pipeline`. A name should let
  someone browsing `pipelines/` understand what it does without opening any
  file.
- `item_id`s: a stable hash (recommend the first 12 hex characters of a
  SHA-256 of the canonical source reference), never a sequential counter —
  sequential IDs collide across pipeline runs and don't survive a source
  changing its own ordering.
- Stage-store filenames: always `<item_id>.md`, one file per item per
  stage — never batch multiple items into one file, since that breaks the
  per-file immutability and audit-log referencing the model depends on.

## Where this repo lives

Delivered as a standalone repository. Reasonable homes: its own new
repository (so pipelines can be added and versioned independently of any
one product's codebase), or alongside an existing organization's other
repositories if pipelines will primarily serve that organization's own
content and publishing needs. Either way, treat `main` (or your default
branch) as the record of what actually ran — avoid rewriting history on it,
for the same reason the audit log itself is append-only.
