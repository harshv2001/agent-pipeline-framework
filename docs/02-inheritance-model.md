# 02 — The Inheritance Model

This is the mechanics of "extends" — how a concrete pipeline is defined in
terms of the base framework, what it must supply, what it may override, and
what is fixed.

## The three files that define a pipeline

Every pipeline under `pipelines/<name>/` consists of exactly three
hand-written files, plus whatever the framework generates at runtime
(`stage-store/`):

- **`spec.md`** — the class declaration. States what this pipeline is for,
  which base agent roles it uses (with any overrides), which stages it adds
  on top of the base sequence, and which connectors it declares. This is
  metadata and structure, not decision content.
- **`logic.md`** — the implementation of the one abstract method every
  pipeline must implement: given a piece of metadata, what should happen to
  it. Written in structured plain language because the agent reading it is
  an LLM, not a compiler — but it follows a fixed schema (see
  `templates/logic.template.md`) so it's checkable and comparable across
  pipelines.
- **`config.yaml`** — the constructor arguments. Concrete values: which
  source, which schedule, which output destination, which thresholds.
  Nothing in `config.yaml` should require re-reading `spec.md` or `logic.md`
  to understand — it's the dial settings, not the design.

## What's inherited unmodified (you never restate these)

- The seven base agent roles and their input/output contracts
  (`base-framework/agents/*.md`).
- The stage-store folder structure and file-naming convention
  (`docs/03-stage-store-model.md`).
- The two-gate review requirement and its ordering (agent review, then
  human review, then hash-verified publish).
- The audit-log format and the requirement that it's append-only.
- The orchestration mechanics in `base-framework/SKILL.md` — how a run is
  triggered, how subagents are dispatched, how a run resumes after a
  scheduled task fires.
- The optional runtime-scope mechanism (`source.scope_source: runtime`,
  `run-requests/`, `scripts/consume_run_request.py`) a pipeline may opt
  into instead of a fixed `source.scope` literal. When used, it's the same
  base mechanics for every pipeline, never a pipeline-specific
  reimplementation (`docs/05-execution-model.md`,
  `docs/07-configuration-reference.md`). What *feeds* that inbox is outside
  the inheritance model — a human, or the optional `topic-engine/`
  (`docs/11-topic-engine.md`).

## What you must supply (the "abstract methods")

Every pipeline's `spec.md` must declare:

- `purpose` — one paragraph, plain language, what this pipeline is for and
  what "done" looks like for one item.
- `source` — one or more connector declarations, each `access: read_only`
  (see `docs/08-connectors-and-tooling.md`).
- `output_destinations` — one or more connector declarations, each scoped
  to the specific write action the Publisher Agent is allowed to take (e.g.
  "create a draft post," not "full account access").
- `extends_version` — which version of the base framework this pipeline was
  built against (see "Versioning," below).

Every pipeline must also supply `logic.md` — the decision rule — even for
the "republishing" case, where it can be as short as "proceed if the item
hasn't already been published to this channel; discard otherwise." A
pipeline with no `logic.md` is not valid; "always proceed" is a valid
`logic.md`, but it must be written down and reviewed like any other logic.

## What you may override, and the constraint on overriding

- **Agent role prompts**: a pipeline may extend (never replace) a base
  agent's prompt with pipeline-specific context — brand voice, domain
  vocabulary, a channel's formatting constraints. This is additive: place
  the extension in `pipelines/<name>/agents/<role>.md` and it is appended to
  the base role's prompt at dispatch time, never substituted for it. See
  `templates/agent-override.template.md`.
- **Extra stages**: a pipeline may insert additional stages (e.g., a
  legal-compliance check between agent review and human review for a
  regulated topic). It may not remove or reorder the base stages.
- **Extra review criteria**: a pipeline's `spec.md` may add checklist items
  to the Agent Reviewer's policy. It may not remove any base criterion.
- **Escalation thresholds**: a pipeline may lower the bar for when the
  Triage Agent escalates an ambiguous item to human review instead of
  deciding automatically. It may not raise that bar past the base default,
  and it may never configure a path that publishes without human review.

Anything not explicitly listed above as overridable is fixed. If a use case
seems to need to override something on the fixed list, that's a signal the
base framework needs a considered, versioned change — not a per-pipeline
exception. Raise it as a base-framework change (see "Versioning" below), not
a silent deviation in one pipeline's spec.

## Versioning

`base-framework/spec/pipeline-spec.schema.md` carries a version number.
Every pipeline's `spec.md` pins the version it was built against via
`extends_version` in its frontmatter. When the base framework changes in a
way that affects existing pipelines (a new required field, a changed stage
name), bump the version and treat existing pipelines as still running
against their pinned version until someone deliberately migrates them —
the same discipline as pinning a dependency version in software, and for
the same reason: an unreviewed, automatic change to shared governance
rules is exactly the kind of silent drift Rule 6 (`docs/01-governance-rules.md`)
exists to prevent.

## Composition over special-casing

If two pipelines are extremely similar (e.g., "LinkedIn post from a new
article" and "X post from a new article" both source from the same
reviewed-articles folder and differ only in the content step's target
format and the output connector), do not fork one pipeline's files into the
other. Instead:

1. Confirm the `source` and `logic.md` really are identical — if so, they
   can literally be the same values in both `config.yaml` files, hand-kept
   in sync, or (once you have three or more such pipelines) factored into a
   shared `logic.md` referenced by both via a `logic_ref` field.
2. Let the difference live entirely in `output_destinations` and the
   Content Agent's role override — this is exactly the case the override
   mechanism above is for.

This keeps the number of independent things you have to reason about
proportional to how different your pipelines actually are, not to how many
you've built.
