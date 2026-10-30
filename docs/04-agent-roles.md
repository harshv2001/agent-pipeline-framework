# 04 — Agent Roles

Seven base agent roles carry out every pipeline run. Each is defined once
in `base-framework/agents/<role>.md`, written to be usable directly as a
Claude Code subagent definition (frontmatter: `name`, `description`,
`tools`; body: the role's contract). A pipeline may extend a role's prompt
(`docs/02-inheritance-model.md`) but never its tool grant — capabilities are
fixed at the base.

## Why separate roles instead of one agent doing everything

Two reasons, both load-bearing rather than stylistic:

- **Independence for review.** Rule 3 (`docs/01-governance-rules.md`)
  requires the reviewer to not be the producer. That only means something
  if they're actually separate agent invocations with separate context —
  not the same agent asked to "now review your own work."
- **Capability minimization.** An agent that only ever reads a source has
  no publish tool available to it at all, so a prompt-injection attempt
  from scraped content (a webpage or post engineered to instruct the agent
  reading it) cannot cause a publish action even if it fools the model —
  there's no tool to call. Each role gets the minimum tool grant its job
  requires.

## The seven roles

### 1. Source Agent ("Scout")
Connects to the pipeline's declared source(s), reads only, extracts
metadata into a `01-raw-metadata` record per new item. Cannot write
anywhere except `01-raw-metadata` in its own pipeline. Cannot decide
whether an item matters — it has no access to `logic.md`. Full contract:
`base-framework/agents/source-agent.md`.

### 2. Triage Agent ("Gatekeeper")
Reads a `01-raw-metadata` record plus the pipeline's `logic.md`, applies
the decision rule, writes a `02-triage-decisions` record: `proceed`,
`discard`, or `escalate` (ambiguous — sent straight to human review without
a draft). Cannot generate content, cannot access output connectors. Full
contract: `base-framework/agents/triage-agent.md`.

### 3. Content Agent ("Producer")
Runs only for `proceed` items. Before drafting, assembles a context pack
(via the `context-pack-builder` skill) scoping what this item's draft
needs and doesn't need, and gates on it — a `fail` verdict escalates to
human review instead of drafting on insufficient or unfocused context.
On `pass`, depending on the pipeline, either researches further and drafts
new content, or adapts existing already-reviewed content for a destination
format (the "republishing" case, `docs/00-overview-and-philosophy.md`),
using format/utility skills (docx, pdf, png, and similar) freely and
without declaration when the output needs them
(`docs/08-connectors-and-tooling.md`). Writes to `03-draft`. May use
read-only research connectors beyond the primary source. Cannot publish.
Full contract:
`base-framework/agents/content-agent.md`.

### 4. Agent Reviewer ("Inspector")
A separate invocation from the Content Agent, given the draft and the
pipeline's review policy (base criteria plus any pipeline additions), with
no memory of how the draft was produced. Checks factual support against
cited sources, brand-voice conformance, disclosure requirements, PII, and
any pipeline-specific criteria. Writes a `04-agent-review` verdict: `pass`
(→ `05-pending-human-review`) or `revise` (→ back to Content Agent, with
feedback, up to a bounded retry count set in `config.yaml`). Full contract:
`base-framework/agents/agent-reviewer.md`.

### 5. Human Liaison ("Notifier")
Packages agent-review-passed items into a review packet
(`templates/review-packet.template.md`) in `05-pending-human-review` and
triggers the async notification described in
`docs/06-review-and-notification.md`. Makes no decisions of its own — pure
packaging and notification. Full contract:
`base-framework/agents/human-liaison.md`.

### 6. Publisher Agent ("Executor")
The only role ever granted a write-capable output connector. Runs only on
items in `06-approved`, verifies the content hash matches what was approved
(Rule 4), executes the publish/save/send action, and writes a receipt to
`08-executed`. If the hash doesn't match, or the target action fails, it
logs a violation or failure event and does not retry silently. Full
contract: `base-framework/agents/publisher-agent.md`.

### 7. Archivist ("Recorder")
Appends an entry to `09-audit-log` after every other agent's action —
implemented as a hook called by the orchestrating skill after each stage
transition, rather than a separately dispatched agent, since its job is
purely mechanical recording. Documented as a role here because its contract
(what must be logged, in what format) is part of the base framework and a
pipeline should never be able to configure events out of the log. Full
contract: `base-framework/agents/archivist-agent.md`.

## How they're dispatched

`base-framework/SKILL.md` is the orchestrator: it reads a pipeline's
`spec.md` and `config.yaml`, and for each stage of a run, dispatches the
corresponding role as a subagent (via the Agent/Task mechanism), assembling
that agent's prompt from the base role definition plus any pipeline-level
override plus the specific stage-store file(s) it needs to act on. See
`docs/05-execution-model.md` for the run lifecycle in full, including how a
scheduled run resumes mid-pipeline after a fresh session starts.

## Adding a role

The seven above cover the shape described in `docs/00-overview-and-philosophy.md`.
If a pipeline genuinely needs an additional role (the legal-compliance
check mentioned in `docs/02-inheritance-model.md` is a good example), add
it as a new stage with its own agent definition under
`pipelines/<name>/agents/`, following the same contract shape as the base
roles (declared inputs, declared outputs, declared tool grant, explicit
prohibited actions). Don't extend an existing role to do a second job —
that reintroduces the independence problem the separation exists to avoid.
