---
pipeline_name: <replace-with-folder-name>
extends_version: "1.0"
run_types: [discovery, publish]
---

# <Pipeline Name>

## Purpose

<One paragraph. What is this pipeline for, and what does "done" look like
for one item? Be concrete — "flag interesting AI news" is not concrete;
"identify posts from this list of accounts that raise a claim about
enterprise AI adoption specific enough to fact-check and respond to" is.>

## Source

- **Connector**: <mcp | connector | skill | browser | filesystem, and the
  specific name>
- **Access**: read_only
- **Scope**: <what exactly is being read — an account, a folder, a search
  query — or, if `config.yaml` sets `source.scope_source: runtime`, the
  fixed search/read *envelope*, since the specific value then comes from
  `run-requests/` per run (`docs/05-execution-model.md`)>
- **`item_id` derivation**: <the stable field(s) hashed to produce item_id
  — e.g. "SHA-256 of the canonical post URL, first 12 hex chars">

Full connection details belong in `config.yaml`; this section explains why
this source and how identity is derived, for a human reading the spec.

## Agent Roles Used

| Role | Override? | Notes |
|---|---|---|
| Source Agent | No | |
| Triage Agent | No | |
| Content Agent | <Yes/No> | <e.g. brand-voice override at agents/content-agent.md> |
| Agent Reviewer | <Yes/No> | <e.g. extra criterion, see Review Policy below> |
| Human Liaison | No | |
| Publisher Agent | No | |
| Archivist | No | |

## Stage Sequence

The ten base stages (`docs/03-stage-store-model.md`), unmodified:
00-source-manifest → 01-raw-metadata → 02-triage-decisions → 03-draft →
04-agent-review → 05-pending-human-review → 06-approved → 07-rejected /
08-executed → 09-audit-log.

Additional stages this pipeline inserts (if any):

- <stage name, where it sits, what it checks — delete this section if none>

## Review Policy

Base criteria (`base-framework/spec/pipeline-spec.schema.md`) apply
unmodified. Additions specific to this pipeline:

- <e.g. "Any claim naming a named competitor is flagged for mandatory
  human review regardless of agent-review verdict.">

## Output Destinations

- **Name**: <label>
  **Connector**: <mcp | connector | skill | browser, and the specific name>
  **Access**: write
  **Action scope**: <the single specific action allowed>

## Escalation Rules

Base default: any ambiguous triage decision escalates to human review
without drafting. Additions specific to this pipeline (may only add
escalation conditions, never remove the base default or add a bypass):

- <e.g. "Any item mentioning a named competitor escalates directly,
  regardless of what logic.md's ordinary rules would otherwise decide.">
