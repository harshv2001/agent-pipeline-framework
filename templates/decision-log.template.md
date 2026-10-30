---
item_id: <same as the matching metadata record>
pipeline: <pipeline name>
stage: 02-triage-decisions
status: <proceed | discard | escalate>
source_ref: <copied from the metadata record>
produced_by: triage-agent v1
created_at: <ISO 8601 timestamp>
supersedes: null
---

## Verdict

**<proceed | discard | escalate>**

## Rule applied

<Which specific rule from logic.md produced this verdict — quote or
closely paraphrase it. If no rule matched and the default action was used,
say so explicitly.>

## Rationale

<Why this item satisfies (or doesn't satisfy) that rule — specific to this
item, not a restatement of the rule itself. Written so a human reading only
this file later understands the reasoning with no other context.>

## Notes

<Any ambiguity encountered, any escalation trigger that applied, anything
flagged in the metadata record's own notes that's relevant here.>
