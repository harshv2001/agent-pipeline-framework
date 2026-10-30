---
timestamp: <ISO 8601>
item_id: <specific item_id, or "pipeline" for a pipeline-level event such as a run starting or ending>
pipeline: <pipeline name>
event: <discovered | decided | drafted | agent_reviewed | escalated | packaged_for_review | approved | rejected | published | promoted | publish_failed | violation | correction | run_started | run_ended | run_request_consumed | run_request_expired | run_request_rejected>
actor: <agent role + version, e.g. "triage-agent v1", or a human identifier for review decisions>
detail: <one line — what happened, specific enough to be useful without opening the referenced file>
ref: <path to the stage-store file this event concerns, relative to the pipeline folder>
---

<Optional free-text elaboration, only when the one-line detail field isn't
enough — e.g. the full text of a policy violation, or the reasoning behind
a "correction" event referencing an earlier entry.>
