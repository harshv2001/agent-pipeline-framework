# 07 — Configuration Reference

`config.yaml` is the one file in a pipeline where every field is a concrete
value, not prose. This is the full field reference; `templates/config.template.yaml`
is the fill-in-the-blanks starting point.

```yaml
pipeline_name: <string, matches the pipelines/<name> folder>
extends_version: <string, the base-framework spec version this pins to>

source:
  connector_type: <mcp | connector | skill | browser | filesystem>
  connector_ref: <name of the MCP server / connector / skill / device folder>
  access: read_only          # fixed — see docs/01-governance-rules.md Rule 1
  scope_source: <fixed | runtime — optional, defaults to 'fixed'>
  scope: <connector-specific — e.g. a search query, an account handle, a folder path>
  poll_frequency_minutes: <int>   # informational; actual cadence set by the scheduled task's cron

decision:
  logic_ref: ./logic.md
  max_review_cycles: <int>        # bound on Content Agent <-> Agent Reviewer revise loops
  escalate_on_ambiguous: true     # fixed true — see docs/02-inheritance-model.md

output_destinations:
  - name: <label, e.g. "linkedin_company_page">
    connector_type: <mcp | connector | skill | browser>
    connector_ref: <name>
    access: write
    action_scope: <the single specific action allowed — e.g. "create_draft_post", never "full_account">

review:
  agent_review_policy_ref: ./spec.md#review-policy   # base criteria + pipeline additions
  review_sla_hours: <int, optional>                  # flags overdue items in the digest; does not auto-escalate

schedule:
  discovery_run_trigger_id: <scheduled task id, filled in once created>
  publish_run_trigger_id: <scheduled task id, filled in once created>

notifications:
  # cross-pipeline digest settings live in the digest task's own config,
  # not here — see docs/06-review-and-notification.md
  include_in_digest: true

audit:
  retention: indefinite   # fixed — see docs/01-governance-rules.md Rule 5
```

## Field notes

- **`source.access` and `output_destinations[].access`** are shown fixed
  above deliberately — `scripts/validate_stage_file.py` rejects a
  `config.yaml` where `source.access` is anything but `read_only`, or where
  an output destination omits `access: write` and a specific
  `action_scope`. A destination without a stated `action_scope` is treated
  as invalid, not as "full access."
- **`source.scope_source`**: optional, defaults to `fixed`. `fixed` means
  `scope` is a permanent literal, exactly as before this field existed —
  the overwhelming majority of pipelines want this and never need to set
  the field at all. `runtime` means this pipeline's specific scope value
  legitimately changes from run to run (a rotating search term supplied by
  a separate process); `scope` then documents the fixed *envelope* — the
  connector, surface, and boundaries that never change — not a literal
  value, and the actual per-run value is resolved from
  `pipelines/<name>/run-requests/pending/` instead. This does not loosen
  Rule 1: the set of things the pipeline is allowed to read is still fixed,
  reviewably, in `config.yaml`; only the specific value searched within
  that fixed envelope varies. See `docs/05-execution-model.md`,
  "Runtime-parameterized sources," for the full mechanism, and
  `docs/10-building-a-new-pipeline.md` for when to reach for it (rarely —
  it's the exception, not the default).
- **`decision.max_review_cycles`**: pick a small number (2-3). This bounds
  cost and prevents an agent/reviewer disagreement from looping
  indefinitely; exceeding it escalates to human review with the full
  back-and-forth attached, which is usually more informative than another
  automated pass would be anyway.
- **`schedule.*_trigger_id`**: left blank when you first write `config.yaml`
  and filled in after you create the actual scheduled tasks (see
  `docs/10-building-a-new-pipeline.md`, step 6). Keeping the ID here (rather
  than only in the scheduled-task system) means the pipeline's own files
  document what triggers it, and `scripts/validate_stage_file.py` can warn
  if a config references a trigger that no longer exists.
- **`review.review_sla_hours`**: optional. Omit it for pipelines with no
  real time-sensitivity (a reference-doc update pipeline) rather than
  setting an arbitrary number — an SLA that doesn't mean anything just
  becomes digest noise.

## What does not belong in `config.yaml`

Anything that requires judgment to read correctly belongs in `spec.md` or
`logic.md` instead: decision rules, review criteria beyond the
policy reference, brand voice, prose of any kind. If you find yourself
writing a sentence as a YAML string value, it's in the wrong file.
