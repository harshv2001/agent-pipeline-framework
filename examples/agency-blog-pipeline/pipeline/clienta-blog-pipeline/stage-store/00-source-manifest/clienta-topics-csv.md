---
item_id: clienta-topics-csv
pipeline: clienta-blog-pipeline
stage: 00-source-manifest
status: fixed
source_ref: source-data/clienta_topics.csv
produced_by: human (Harsh)
created_at: '2026-11-22T08:00:00Z'
supersedes: null
---

## Source envelope

- **Connector**: `filesystem`
- **Path**: `source-data/clienta_topics.csv`
- **Access**: read_only, permanently — this pipeline never edits or
  reorders this file.
- **Written by**: `../../topic-engine/scripts/export_topics_csv.py`,
  after a human approves each topic in the topic engine's own registry.
  This pipeline doesn't distinguish a topic-engine-written row from a
  hand-written one — the envelope is "whatever is in this CSV," fixed at
  setup; which specific row(s) a given run acts on is a per-run filter
  from `run-requests/` (`config.yaml`'s `source.scope_source: runtime`).

This record is fixed at pipeline setup and does not change per run —
see `docs/03-stage-store-model.md`, "Immutability by stage."
