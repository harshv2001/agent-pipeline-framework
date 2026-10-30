---
schema_version: "1.0"
---

# Pipeline Spec — Base Schema

This is the abstract base contract every `pipelines/<name>/spec.md` extends
(`docs/02-inheritance-model.md`). It defines the required frontmatter
fields, the required body sections, and which of each are fixed versus
overridable. A concrete `spec.md` that omits a required field, or attempts
to override a fixed one, fails `scripts/validate_stage_file.py`.

## Required frontmatter

```yaml
---
pipeline_name: <string>
extends_version: "1.0"          # must match this file's schema_version, or a version this framework declares compatible
run_types: [discovery, publish] # fixed — every pipeline supports both
---
```

## Required body sections

### Purpose
One paragraph. What this pipeline is for, and what "done" looks like for
one item. Free text — this is not overridable in the OOP sense because
it's not inherited at all; every pipeline writes its own.

### Source
One or more connector declarations (mirrors `config.yaml`'s `source` — the
prose here explains *why* this source, the YAML in `config.yaml` states
*what*). Must state `access: read_only`. **Fixed**: no pipeline may declare
a source with any other access level.

### Agent Roles Used
A table listing each of the seven base roles and whether this pipeline uses
it as-is or with an override (pointing to `pipelines/<name>/agents/<role>.md`
if so). All seven are always used — **fixed** — though a role's work may be
trivial for a given pipeline (e.g., Triage Agent applying a one-line
`logic.md`).

### Stage Sequence
The ten base stages, in order — **fixed**, restated here for legibility —
plus any pipeline-specific additional stages, each with a one-line
description of what it checks and where it sits in the sequence. Additions
are **overridable** (may only add, never remove or reorder the base ten —
`docs/01-governance-rules.md` Rule 7).

### Review Policy
The base Agent Reviewer criteria — **fixed**, restated here for
legibility — plus any pipeline-specific additions (**overridable**, may
only add criteria, never remove one).

Base criteria (every pipeline's Agent Reviewer checks all of these,
regardless of what a pipeline adds):
- Every factual claim in the draft is supported by the source material or
  cited research — no unsupported claims.
- No personally identifiable information about a private individual appears
  in the draft unless the source itself is that person's own public
  statement being discussed.
- Content that is AI-assisted and will be published under a byline
  discloses that, if the destination's norms or this pipeline's
  configuration require disclosure.
- No claim the source material would not reasonably be read to support,
  including no invented quotes or statistics.
- Brand/voice conformance per whatever style guide this pipeline's Content
  Agent override references, if any.

### Output Destinations
One or more connector declarations (mirrors `config.yaml`'s
`output_destinations`). Must state `access: write` and a specific
`action_scope` per destination. **Fixed**: no destination may omit
`action_scope` in favor of blanket access.

### Escalation Rules
When the Triage Agent escalates directly to human review instead of
drafting. **Overridable only downward** — a pipeline may add conditions
that escalate more often than the base default (ambiguous decisions
always escalate, base default), never conditions that reduce escalation
or that permit bypassing human review entirely.

## Versioning this schema

Bump `schema_version` for any change that adds a required field, changes a
fixed rule, or renames a stage. Existing pipelines keep running against
their pinned `extends_version` (`docs/02-inheritance-model.md`,
"Versioning") until deliberately migrated — this file changing is not
itself a reason for `pipeline-runner` to refuse a pipeline pinned to an
older, still-declared-compatible version.

## Compatibility declarations

This file may declare which older `extends_version` values remain
compatible with the current base-framework agent contracts and stage
model, e.g.:

```yaml
compatible_with: ["1.0"]
```

`pipeline-runner` (`base-framework/SKILL.md`) checks a pipeline's
`extends_version` against this list before running.
