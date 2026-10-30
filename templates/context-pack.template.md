---
item_id: <same item_id as the metadata/decision records this pack is for>
pipeline: <pipeline name>
verdict: pending
---

# Context Pack — {item_id}

Filled in by the Content Agent, step 0, before drafting
(`base-framework/agents/content-agent.md`), using the `context-pack-builder`
skill (https://github.com/ViksyaHQ/context-pack-builder). This is not a
separate stage-store file — it's the opening section of this item's
`03-draft/{item_id}.md` record, sitting above the draft itself.

Keep this short. For every line below, the test is: *what breaks if the
Content Agent doesn't see this?* If nothing breaks, cut it — a pack that's
too long defeats the purpose as surely as one that's too thin.

## 1. Intent

<One or two sentences: what this specific draft needs to accomplish, tied
to `logic.md`'s rationale for why this item proceeded and `spec.md`'s
Purpose. Not a restatement of the pipeline's purpose in general — what
"done" looks like for *this item*.>

## 2. Scope boundary

<What this draft must NOT do. Out-of-scope is mandatory, not optional —
if this section is empty, that's a gap, not a sign there are no
boundaries. E.g., for a republishing pipeline: "no new claims beyond what
the source article states." For a reactive social post: "responds to the
point raised, does not summarize or promote the source post itself.">

## 3. Touchpoints

<Which destination this is headed for (`config.yaml`'s
`output_destinations`, by name) and its `action_scope` — so the Content
Agent writes for the actual format and constraint it will be checked
against, not a generic draft. Which downstream checks apply: the base
Review Policy always; name any pipeline-specific additions from `spec.md`.>

## 4. Contracts & constraints

<Brand voice / vocabulary rules (from any `agents/content-agent.md`
override), factual-support requirement (every claim must trace to
`source_ref` or cited research — this is fixed, not pipeline-specific),
and any pipeline-specific constraint from `logic.md`'s "Explicitly
Prohibited" section that bears on drafting rather than triage.>

## 5. Definition of done

<What "ready for agent review" means for this item — concrete enough that
the Agent Reviewer (a different dispatch, with no memory of this
reasoning) can check it without asking the Content Agent what was meant.
At minimum: every claim cited, brand voice applied, scope boundary
respected.>

## 6. References

<Link or point to, don't re-paste: `source_ref`, any additional research
consulted, the brand-voice document if one exists. If something here is
important enough to need re-pasting in full, that's usually a sign it
belongs in section 4 as a constraint instead.>

## Verdict

`pending` while drafting this pack. Before drafting starts, set to:

- **`fail`** — name the specific gap: starved (section 1, 3, or 4 has no
  real content to ground a draft) or drowned (this pack, or the material
  behind it, is so broad the actual constraint is buried). Do not draft.
  This routes the item to human review as an escalation instead.
- **`pass`** — sufficient and focused. Proceed to draft below this pack in
  the same `03-draft/{item_id}.md` file.
