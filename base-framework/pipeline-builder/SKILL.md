---
name: pipeline-builder
description: Mechanizes docs/10-building-a-new-pipeline.md end to end from one natural-language brief — scaffolds a new pipeline, drafts spec.md/logic.md/config.yaml, and refuses to hand it back until it validates clean. Use when asked to build, create, or set up a new pipeline from a description, not to run an existing one.
---

# Pipeline Builder

This skill authors a new `pipelines/<name>/` from a single natural-language
brief, following `docs/10-building-a-new-pipeline.md` Steps 0 through 5
exactly — it does not introduce a different way of specifying a pipeline,
it just does the file-writing so you don't have to hold five files'
worth of structure in your head at once. It is an authoring-time tool,
separate from `base-framework/SKILL.md` (the `pipeline-runner`), which
executes a pipeline once it exists.

## What this skill is not

It is not a shortcut around governance decisions, and it is not a
deployment tool. Read both before using it:

- **It asks rather than invents.** Anything that determines what the
  pipeline is *allowed to do* — a connector's `access` value, an
  `action_scope`, a `logic.md` rule, an escalation trigger — is a
  governance decision, not a drafting detail. If the brief doesn't specify
  one of these clearly enough to write down, ask; never guess a plausible-
  sounding default and move on. A wrong guess here is a wrong guess in
  what gets published under the person's name.
- **It stops before anything externally consequential.** This skill never
  creates a scheduled task, never runs a discovery or publish run, and
  never touches any destination. It produces files under `pipelines/<name>/`
  and nothing else. `docs/10-building-a-new-pipeline.md` Steps 6–8
  (scheduled tasks, the dry run, going live) stay manual, deliberate acts
  you take afterward, on a pipeline you've had the chance to read in full
  first.

## Invocation

Expects a natural-language brief describing the pipeline: what it watches
or reads, what makes an item worth acting on, what it produces, and where
that output goes. A one-paragraph brief is enough to start — this skill
asks follow-up questions for anything it needs and the brief doesn't
supply. It does not need to be structured; turning unstructured intent
into the framework's structure is the point of this skill.

If the brief describes something that isn't a discovery-and-review
pipeline at all (no source to triage, nothing to draft), say so rather
than forcing it into this shape.

## Procedure

### Step 0 — Confirm the shape, then optionally context-pack the build

Restate back, in a sentence or two, what you understood: the source, the
triage question, what gets produced, and the destination. Get a
confirmation or correction before writing anything — this is cheap now and
expensive after five files are drafted around a misunderstanding.

For anything beyond a small pipeline, apply
`docs/10-building-a-new-pipeline.md` Step 0: use the `context-pack-builder`
skill to assemble a context pack for *this build task* (not the runtime
pipeline) before drafting — what the pipeline must accomplish, what's
explicitly out of scope, which existing pipeline or brand-voice doc to
pattern-match, what "ready to scaffold" means. Skip this for a trivially
simple brief where it would add ceremony without catching anything.

### Step 1 — Extract the one-paragraph purpose

Write the plain-language "done" statement `docs/10-building-a-new-pipeline.md`
Step 1 describes. Read it back for confirmation along with Step 0's
restatement if you haven't already confirmed the shape.

### Step 2 — Choose a name and scaffold

Propose a pipeline folder name following `docs/09-directory-layout.md`'s
naming convention (lowercase, hyphenated, specific about source and
destination — `linkedin-search-to-original-post`, not `linkedin-pipeline`).
Confirm it doesn't collide with an existing folder under `pipelines/`, then
run:

```
python scripts/scaffold_pipeline.py <name>
```

### Step 3 — Resolve source and destination connectors

Before writing anything into `config.yaml`, work out, per
`docs/08-connectors-and-tooling.md`'s "check before you build": is there an
MCP server or connector already available for this source and this
destination? Ask the user directly if it's unclear which is available or
preferred — do not silently fall back to `browser` when a purpose-built
connector might exist, and do not silently choose one destination over
another when the brief mentions several without ranking them.

For each of source and destination, you need, and must either extract from
the brief or ask for:
- `connector_type` and `connector_ref`
- for the source: `scope` (what exactly is read) and how `item_id` is
  derived (a stable field to hash — never a sequential counter,
  `docs/09-directory-layout.md`)
- whether this source's scope is fixed once (the default, and right for
  almost every pipeline) or genuinely needs to vary per run
  (`source.scope_source: runtime`, `docs/05-execution-model.md`,
  "Runtime-parameterized sources") — ask rather than defaulting to
  `runtime`; it adds a `run-requests/` handoff most pipelines don't need
- for each destination: a single, specific `action_scope` — never a
  blanket permission. If the brief says "post to LinkedIn," ask whether
  that means creating a draft for later manual publish or something more
  automated; do not assume the more permissive reading.

Write these into both `spec.md` (the human-readable Source and Output
Destinations sections) and `config.yaml` (the machine-readable
`source`/`output_destinations` blocks) — same facts, two files, per the
existing template shape.

### Step 4 — Draft `logic.md`

This is the step `docs/10-building-a-new-pipeline.md` calls out as
requiring actual judgment, not boilerplate, and that holds here too. Draft:

- **Decision inputs**: the specific fields from `01-raw-metadata` the
  rules below actually use — list them explicitly.
- **Decision rules**, ordered, first-match-wins, each specific enough that
  two different readings of the same item reach the same verdict.
- **Default action**: `discard` or `escalate` only — never default to
  `proceed`. If the brief doesn't make the default obvious, ask rather
  than picking one.
- **Escalation triggers**: conditions that skip straight to human review
  without drafting, on top of the base "ambiguous cases always escalate"
  rule (restate that rule, per the template — don't remove it).
- **Explicitly prohibited**: anything the brief implies should never
  happen even if a rule above could be read to permit it (a common one:
  never proceed on engagement/virality alone).

Draft a first pass from the brief, then show it and ask whether the rules
match intent — decision logic is exactly the kind of governance-relevant
content this skill must not finalize unilaterally.

### Step 5 — Role overrides, if implied

If the brief mentions a brand voice, a vocabulary rule, a format
constraint, or an extra review criterion, write the relevant
`pipelines/<name>/agents/<role>.md` override from
`templates/agent-override.template.md`, appended to the base role's
prompt — never replacing it (`docs/02-inheritance-model.md`). Update
`spec.md`'s Agent Roles Used table to mark that role as overridden. If
nothing in the brief implies an override, leave this step out — most
pipelines don't need one.

### Step 6 — Validate, loop until clean

Run:

```
python scripts/validate_stage_file.py --pipeline pipelines/<name>
```

This checks `config.yaml` against the governance schema and sweeps
`spec.md`, `logic.md`, `config.yaml`, and any `agents/*.md` overrides for
unresolved template placeholders. If it fails, fix every reported problem
and re-run — do not hand the pipeline back, summarize it as "mostly done,"
or suggest the person finish it themselves while a validation error
stands. A pipeline this skill hands back is either fully specified or not
handed back at all.

### Step 7 — Hand back, point at what's still manual

Report what was created (the folder, a summary of source/destination/
logic), confirm `validate_stage_file.py --pipeline` passes, and say plainly
that Steps 6–8 of `docs/10-building-a-new-pipeline.md` — creating the
scheduled tasks, the manual dry run, and going live — are next and are not
something this skill does.

## What this skill must never do

- Never invent a governance-relevant value (`access`, `action_scope`, a
  `logic.md` rule, an escalation trigger, a default action) the brief
  didn't clearly specify — ask instead.
- Never create a scheduled task, run a discovery or publish run, or take
  any action against a real source or destination.
- Never hand back a pipeline that fails
  `validate_stage_file.py --pipeline pipelines/<name>` — fix it or say
  plainly what's blocking it and why it needs a human decision, don't
  soften a failure into a caveat.
- Never restate content the person already gave precisely (a source URL, a
  named connector) in a way that changes its meaning — copy it, don't
  paraphrase it, into `spec.md`/`config.yaml`.
- Never write directly into `pipelines/<name>/stage-store/` — that's
  runtime output, not authoring output; this skill's job ends at a
  validated `spec.md`/`logic.md`/`config.yaml` (and any `agents/`
  overrides).
