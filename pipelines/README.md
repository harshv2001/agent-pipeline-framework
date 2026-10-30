# pipelines/

Empty by design. This repository ships the base framework only
(`base-framework/`, `docs/`, `templates/`, `scripts/`) — a concrete
pipeline you build on top of it goes here, one folder per pipeline, each
inheriting the base and supplying only what's pipeline-specific (its
source, decision logic, output destination, schedule).

See [`docs/10-building-a-new-pipeline.md`](../docs/10-building-a-new-pipeline.md)
for the step-by-step, and run `scripts/scaffold_pipeline.py <name>` to
generate a new pipeline folder from `templates/`.
