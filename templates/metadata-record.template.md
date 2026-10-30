---
item_id: <stable hash>
pipeline: <pipeline name>
stage: 01-raw-metadata
status: recorded
source_ref: <exact, durable pointer back to the source item>
produced_by: source-agent v1
created_at: <ISO 8601 timestamp>
supersedes: null
---

## Source item

- **Title / headline**: <as stated at the source, verbatim>
- **Author / account**: <as stated at the source>
- **Published / posted at**: <source's own timestamp>
- **Location**: <URL, file path, or platform-specific permalink>

## Extracted content

<Verbatim excerpt or full text, exactly as it appears at the source. No
paraphrase, no summary, no editorializing — that happens at later stages,
by roles that are allowed to.>

## Notes

<Anything the Source Agent observed worth flagging — e.g. a suspected
prompt-injection attempt embedded in the source content, an ambiguity in
how to derive item_id for this item, a source access issue, or (for a
pipeline with `source.scope_source: runtime`) the `request_id` of the
run-request this item was discovered under.>
