# agency-blog-pipeline — worked example

A complete, runnable example of this framework built for a specific,
common case: **a digital agency running a content pipeline for a
client's blog.** If you run an agency, or you're evaluating this
framework for one, this is meant to be lifted close to as-is for a real
client account — read "Adapting this for a real client" below once
you've seen it run.

The running example: **AgencyA** runs the blog for its client
**ClientA** (`clienta.com` — a fictional small-business bookkeeping and
fractional-CFO service; see `sample-client-site/`). Every file in this
folder uses `ClientA` as a literal, searchable placeholder — adapting
this for a real client is a find-and-replace plus a few config values,
not a rewrite.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for this example's own diagrams
(the topic-engine → CSV handoff, the output-mode branch, and a
sequence diagram of the exact TOP-0001 run seeded below) — separate from
the base framework's own pipeline-agnostic diagrams in
[`../../docs/diagrams/`](../../docs/diagrams/).

## What's here, and why three pieces

```
agency-blog-pipeline/
├── sample-client-site/     ClientA's site (fixture) -- what gets analyzed
├── topic-engine/            Decides WHAT to write about -- site analysis -> topics CSV
└── pipeline/
    └── clienta-blog-pipeline/   Decides HOW to write it -- the 10-stage governed pipeline
```

This mirrors how an actual agency engagement works: you don't get a
content calendar for free, and you don't want the two concerns — *what's
worth writing* and *is this draft good enough to publish* — governed by
the same logic. The topic engine is the optional, lighter-weight piece
(`docs/11-topic-engine.md`'s pattern); the blog pipeline is the full
governed framework (`docs/01-governance-rules.md`) that every draft goes
through regardless of where its topic came from.

## Run it yourself, start to finish

```bash
cd examples/agency-blog-pipeline

# 1. Topic engine: analyze the site, propose topics, approve some, export to CSV
cd topic-engine
pip install -r scripts/requirements.txt
python scripts/analyze_site.py --engine .
#   -> then the Topic Discovery Agent reads site-profile/site-facts.json
#      plus the raw site and writes site-profile/site-profile.md (already
#      done for you in this checkout -- see topic-engine/README.md to redo
#      it, or to run a later, optional refresh batch)
python scripts/fold_ledger.py --engine .            # regenerate registry/registry.csv
python scripts/validate_registry.py --engine .
python scripts/export_topics_csv.py --engine . \
    --out ../pipeline/clienta-blog-pipeline/source-data/clienta_topics.csv \
    --run-id EXP-$(date +%Y%m%d)

# 2. Blog pipeline: already has one fully worked item (TOP-0001) committed
#    in its stage-store -- inspect it directly:
cd ../pipeline/clienta-blog-pipeline
cat stage-store/08-executed/TOP-0001.md

# To run a NEW item through the pipeline yourself (TOP-0002, 0003, or 0004
# are approved and exported but not yet picked up -- see status-report.csv):
#   - write a run-requests/pending/ file (templates/run-request.template.md,
#     base framework) with scope_value: id=TOP-0002
#   - dispatch base-framework/SKILL.md's discovery run, which walks the
#     Source -> Triage -> Content -> Agent-Review -> Human-Liaison chain
#   - review stage-store/05-pending-human-review/TOP-0002.md, then:
python ../../../../scripts/advance_stage.py --pipeline . --approve TOP-0002
python ../../../../scripts/advance_stage.py --pipeline . --verify-manifest TOP-0002
python scripts/init_demo_site_repo.py   # first time only -- stands in for ClientA's real site repo
python scripts/publish_output.py --item-id TOP-0002
python ../../../../scripts/advance_stage.py --pipeline . --move TOP-0002 --from 06-approved --to 08-executed --actor "publisher-agent v1" --detail "staged"
python tooling/build_status_report.py
```

See [`topic-engine/README.md`](topic-engine/README.md) and
[`pipeline/clienta-blog-pipeline/spec.md`](pipeline/clienta-blog-pipeline/spec.md)
for the full detail on each piece.

## What's already seeded in this checkout

So you can see a complete result without running anything first:

- **Topic engine**: a bootstrap site-read (`topic-engine/site-profile/`),
  5 proposed topics, 4 approved and exported, 1 rejected
  (`topic-engine/registry/registry.csv` shows all 5 and their status).
- **Blog pipeline**: `TOP-0001` carried through all ten stages for real —
  discovered, triaged, drafted (with a generated hero image), agent-reviewed
  (with one flagged-but-not-blocking note), packaged, approved, and staged
  to a local git branch standing in for ClientA's real site repo. `TOP-0002`,
  `TOP-0003`, `TOP-0004` are approved and exported to
  `source-data/clienta_topics.csv` but not yet picked up — a realistic
  backlog, not a failure. `pipeline/clienta-blog-pipeline/status-report.csv`
  shows all four at a glance.

Run `python pipeline/clienta-blog-pipeline/scripts/init_demo_site_repo.py`
to generate the local git repo TOP-0001 was staged to (it's gitignored —
generated state, not source) and inspect
`git log --all --oneline` / `git diff main stage/insights-top-0001` inside
it to see exactly what a real publish would produce.

## Adapting this for a real client

1. Find-and-replace `ClientA` → your client's actual name throughout
   `topic-engine/config/engine.yaml`,
   `pipeline/clienta-blog-pipeline/source-data/clienta_brand_profile.md`,
   and `pipeline/clienta-blog-pipeline/agents/content-agent.md`.
2. Replace `sample-client-site/` with a real export of the client's actual
   site (`topic-engine/scripts/analyze_site.py`'s docstring explains what
   it needs — static, server-rendered HTML; export a JS-heavy site first).
3. Re-run the bootstrap (`topic-engine/scripts/analyze_site.py`, then have
   the Topic Discovery Agent write a fresh `site-profile.md` and propose
   real topics against the real site).
4. Point `pipeline/clienta-blog-pipeline/config.yaml`'s
   `output_destinations[0].connector_ref` at the client's actual site
   repo (`git:github.com/...`) instead of the local
   `./demo-site-repo` stand-in, and set up whatever credential
   `docs/08-connectors-and-tooling.md` calls for — or, if the client isn't
   on a git-based static site, leave `output_mode: local_files` and hand
   the generated files to their CMS instead (`spec.md`, "Output
   Destinations").
5. Replace `scripts/generate_hero_svg.py`'s placeholder output with real
   image generation once you have a dependency/API budget for it — it
   exists only so this example runs with nothing but Python.

Everything else — the ten-stage governance, the review policy, the
run-request filters, the status-report discipline — needs no change per
client; that's the part of this framework that's the same for every
pipeline.
