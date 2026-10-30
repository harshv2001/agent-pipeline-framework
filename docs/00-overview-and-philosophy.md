# 00 — Overview and Philosophy

## The problem this solves

A recurring shape shows up across very different automations: scan
something, decide what's worth acting on, do something with the ones that
qualify, get that reviewed, then let it out into the world. Written from
scratch each time, every pipeline re-derives the same questions — where does
staged output live, who's allowed to publish, what happens when a review
fails, how do you know what ran last Tuesday — and answers them slightly
differently each time. That inconsistency is where governance gaps and
silent mistakes come from.

This framework answers those questions once, and lets each concrete pipeline
answer only the questions that are actually specific to it: what's the
source, what's the decision rule, what's the output.

## The inheritance analogy

The framework is deliberately structured the way a base class is structured
in an object-oriented language, because the same discipline applies:

| OOP concept | This framework |
|---|---|
| Abstract base class | `base-framework/spec/pipeline-spec.schema.md` |
| Concrete subclass | `pipelines/<name>/spec.md` |
| Inherited method (fixed) | The stage sequence, the two review gates, the audit log |
| Abstract method (must implement) | `logic.md` (decision rule), source and output connector declarations |
| Overridable method (may extend, may only tighten) | Agent role prompts, extra review criteria, extra stages |
| Final method (may never override) | Source read-only enforcement, the requirement that both reviews pass before publish |
| Constructor arguments | `config.yaml` |
| Class version pin | `extends_version` in `spec.md`'s frontmatter |

This isn't a metaphor for its own sake — it's a design constraint. If a rule
would need to be an "abstract method" that most pipelines override in a way
that weakens it, it doesn't belong in the base at all; it belongs in
`logic.md` where it's visible and pipeline-specific. Governance rules that
protect against harm (source mutation, unreviewed publishing) are "final" —
no pipeline may override them, and the scripts in `scripts/` mechanically
check for attempts to do so.

## What counts as a pipeline here

Both of these are the same abstraction, at different levels of the decision
step:

- **Discovery pipelines**: scan a source (a website, a folder, an X account,
  a LinkedIn search), extract metadata, decide per item whether it's worth
  acting on, and — for the ones that qualify — research further and generate
  new content from scratch.
- **Republishing pipelines**: take something that already exists and is
  already reviewed (an approved article in a folder) and adapt it for a
  destination (a LinkedIn post, an X thread, a blog cross-post). The
  decision step is nearly trivial ("is this item new and not yet
  republished to channel X?") and the content step is reformatting rather
  than generation.

Both run through the identical stage sequence and the identical two review
gates. The difference is entirely in `logic.md` and in how thin the content
step is — which is the point: the framework doesn't need a special case for
"simple" pipelines, because "simple" is just "trivial decision logic, light
content step," not a different shape.

## What this framework is not

- It is not a replacement for judgment. The decision logic and the review
  criteria are written by you, in plain language, per pipeline. The
  framework enforces that decisions get made and logged consistently; it
  doesn't make the decisions good.
- It is not a no-review autoposting tool. If a use case genuinely needs
  zero-touch publishing, that is explicitly out of scope for this framework
  — see the non-negotiables in `docs/01-governance-rules.md`.
- It is not tied to one source or one destination. Sources and destinations
  are connectors declared in config; see
  `docs/08-connectors-and-tooling.md`.

## How to read the rest of these docs

Read 01 through 04 first — they define the vocabulary (stages, agents,
inheritance) everything else uses. 05 through 09 are reference material you
return to while building. 10 is the worked walkthrough — read it once
end-to-end before you build your first pipeline, then treat it as a
checklist.
