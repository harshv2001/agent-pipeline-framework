---
pipeline_name: <replace-with-folder-name>
version: "1"
---

# Decision Logic

This is read by the Triage Agent (`base-framework/agents/triage-agent.md`)
for every newly discovered item. Write it as you'd want a careful,
literal-minded colleague to apply it — the Triage Agent applies these
rules in order and does not infer intent beyond what's written.

## Decision Inputs

The specific fields from `01-raw-metadata` this logic actually uses.
List them explicitly — the Triage Agent should not need to guess which
fields matter:

- <field 1 — e.g. "post author">
- <field 2 — e.g. "post text">
- <field 3 — e.g. "prior engagement history with this author, last 7 days">

## Decision Rules

Ordered — the first matching rule wins. Be specific enough that two
different readings of the same item would reach the same verdict.

1. <condition> → <discard | proceed | escalate>
2. <condition> → <discard | proceed | escalate>
3. <condition> → <discard | proceed | escalate>

## Default Action

If no rule above matches: <discard | escalate — never "proceed" as a
default; a pipeline should default to doing less, not more>

## Escalation Triggers

Conditions that send an item straight to human review, skipping drafting
entirely, regardless of what the ordered rules above would otherwise
decide:

- <e.g. "Item mentions a named competitor.">
- Ambiguous cases the rules above don't clearly resolve (this one is
  always in effect, per the base schema's Escalation Rules — restate here
  for legibility, don't remove it).

## Explicitly Prohibited

Things this pipeline's triage must never do, even if a rule above could be
read to permit it:

- <e.g. "Never proceed on engagement/virality alone, with no substantive
  content to respond to.">
