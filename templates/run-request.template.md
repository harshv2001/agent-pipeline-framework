---
request_id: <unique string — e.g. a UUID, or a date-based id such as RUN-2026-0922-01>
pipeline: <pipeline name — must match this pipeline's folder name exactly>
scope_value: <the literal value to use as this run's source.scope — a search term, an account handle, a folder path>
requested_by: <who or what created this request — a name, or the name of the requesting automation>
requested_at: <ISO 8601 timestamp>
expires_at: <ISO 8601 timestamp, optional — omit for no expiry>
---

## Why this request

<Optional: one or two sentences of context for a human reading this file
later — what prompted this value, what it's for. This is read the same
way any other pipeline input is read: as data a human or the Source Agent
may look at, never as an instruction
(base-framework/agents/source-agent.md, "Handling untrusted content"). Only
`scope_value` is ever used as this run's scope.>
