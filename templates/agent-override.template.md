---
role: <source-agent | triage-agent | content-agent | agent-reviewer | human-liaison | publisher-agent>
pipeline: <pipeline name>
---

# <Role> Override — <Pipeline Name>

This content is **appended** to the base role's prompt
(`base-framework/agents/<role>.md`) at dispatch time. It never replaces any
part of the base contract — anything that reads as a replacement (e.g.
"ignore the base prohibition on...") is invalid and will be rejected in
review; overrides may only add pipeline-specific context or, where the
base schema explicitly allows it (`docs/02-inheritance-model.md`), add
restrictions.

## Additional context for this role, on this pipeline

<E.g., for a Content Agent override: brand voice guide reference,
prohibited vocabulary, required disclosure language, format constraints
specific to the destination (character limits, thread structure).>

<E.g., for an Agent Reviewer override: additional checklist criteria
specific to this pipeline's subject matter or destination.>

## What this override does not change

<Explicitly restate, for anyone reviewing this override, that it does not
touch: the role's tool grant, its position in the stage sequence, or any
base prohibition. This section exists so a reviewer of the override file
itself can confirm at a glance that it stays within the allowed bounds.>
