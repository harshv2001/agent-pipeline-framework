# pipelines/

Empty by design. This repository ships the base framework only
(`base-framework/`, `docs/`, `templates/`, `scripts/`) — a concrete
pipeline you build on top of it goes here, one folder per pipeline, each
inheriting the base and supplying only what's pipeline-specific (its
source, decision logic, output destination, schedule).

See [`docs/10-building-a-new-pipeline.md`](../docs/10-building-a-new-pipeline.md)
for the step-by-step, and run `scripts/scaffold_pipeline.py <name>` to
generate a new pipeline folder from `templates/`.

Want a complete, runnable reference before building your own? See
[`examples/agency-blog-pipeline/`](../examples/agency-blog-pipeline/) — a
worked example (plus a matching optional topic-engine upstream of it,
`docs/11-topic-engine.md`) built for a digital agency running a client's
blog, with one item carried through all ten stages for real. Its own
`ARCHITECTURE.md` diagrams that example's specific wiring; the
framework-level diagrams in `docs/diagrams/` cover the generic shape
every pipeline here inherits.
