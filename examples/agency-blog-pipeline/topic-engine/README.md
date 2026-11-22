# topic-engine (agency-blog-pipeline example)

A worked, generic instance of the optional upstream pattern described in
[`docs/11-topic-engine.md`](../../../docs/11-topic-engine.md). It decides
*what ClientA's blog should cover next* and hands topics to
[`../pipeline/clienta-blog-pipeline/`](../pipeline/clienta-blog-pipeline/)
as a plain CSV — no multi-surface search dispatch, no daily orchestrator
loop, just: analyze the site once, propose topics, a human approves them,
export the approved ones to a CSV. That's deliberately a smaller scope
than the pattern doc's full description (registry + ledger + backpressure
+ orchestrator dispatching run-requests across several search surfaces);
this example only needs the registry + ledger half of that, because its
one "surface" is a fixed CSV file, not a live search term a pipeline has
to go searching with per run.

## Running it by hand

```bash
cd examples/agency-blog-pipeline/topic-engine
pip install -r scripts/requirements.txt

# 1. Bootstrap run (mandatory before the first topic can be proposed)
python scripts/analyze_site.py --engine .
#    -> writes site-profile/site-facts.json (mechanical extraction only)
#    then have the Topic Discovery Agent (agents/topic-discovery-agent.md)
#    read that plus the raw site and write site-profile/site-profile.md
#    (the qualitative read: industry, voice, personality) before proposing
#    any topics.

# 2. Propose topics (agent-driven: writes registry/topics/TOP-####.md files
#    and logs a 'proposed' row per topic)
python scripts/next_topic_id.py --engine .
python scripts/append_ledger.py --engine . --topic-id TOP-0001 \
    --event proposed --actor "topic-discovery-agent v1" \
    --run-id TDA-2026-1122 --detail "Bootstrap run: initial batch"

# 3. A human reviews registry/registry.csv and approves or rejects each one
python scripts/fold_ledger.py --engine .
python scripts/append_ledger.py --engine . --topic-id TOP-0001 \
    --event approved --actor harsh --run-id REVIEW-2026-1122 \
    --detail "Approved as proposed"

# 4. Export every approved, not-yet-exported topic to the pipeline's source-data CSV,
#    plus the pipeline's own copy of the client's voice/services (brand-profile.md)
python scripts/export_topics_csv.py --engine . \
    --out ../pipeline/clienta-blog-pipeline/source-data/topics.csv \
    --run-id EXP-2026-1122
python scripts/export_brand_profile.py --engine . \
    --out ../pipeline/clienta-blog-pipeline/source-data/brand-profile.md

python -m unittest discover -s scripts/tests   # regression tests
```

## Running it again later (optional)

Step 1 only needs to happen once, unless the client's site changes
significantly. A later run can skip straight to proposing a fresh batch
of topics against the existing `site-profile.md` and the pipeline's
current `topics.csv` (so it doesn't re-propose something already
exported). That's what makes this "optional in subsequent runs, a
prerequisite for the first" in practice: the pipeline never has to wait
on the engine running again, and the engine, when it does run again, only
ever adds rows — it never touches a row the pipeline has already started
working from.

## Layout

```
topic-engine/
├── README.md                    This file
├── schema/REGISTRY-SCHEMA.md     Field reference + status derivation
├── templates/topic.template.md
├── agents/topic-discovery-agent.md
├── config/engine.yaml            Client, site source, bootstrap flag, handoff path
├── registry/
│   ├── topics/                   One file per topic
│   ├── ledger.csv                Append-only events (proposed/approved/rejected/exported/correction)
│   └── registry.csv              Generated view — never hand-edited
├── site-profile/
│   ├── site-facts.json           Mechanical extraction (scripts/analyze_site.py)
│   └── site-profile.md           Qualitative read — written by the agent, not a script
└── scripts/                      analyze_site, next_topic_id, append_ledger,
                                   fold_ledger, export_topics_csv,
                                   export_brand_profile, validate_registry;
                                   tests/
```

`../client-config.yaml` (the example root, a sibling of this folder and
of `pipeline/<slug>-blog-pipeline/`) is where this client's name, slug,
services, and brand palette actually live — nothing here hardcodes one
of those (`_common.py`'s `load_client_config`).
```

## What's cut from the full topic-engine pattern, and why

- **No multi-surface routing or `routes[]` config.** This engine feeds
  exactly one destination (one blog pipeline, via one CSV), so there's
  nothing to route between.
- **No backpressure check or daily-dispatch orchestrator.** Those exist in
  the full pattern because an Orchestrator Agent is deciding, every day,
  whether to drop one more run-request into a *live* search pipeline
  without flooding its human-review queue. This example's handoff is a
  batch export a human explicitly triggers, not a standing automated
  loop — so there's no dispatch cadence to protect.
- **No per-task `dispatched`/`searched`/`blocked`/`outcome` ledger
  events.** Those track a search task's own lifecycle inside a
  continuously running discovery pipeline. Once a topic here is
  `exported`, what happens to it is the blog pipeline's own concern,
  tracked by its own `status-report.csv` — this engine's job ends at the
  export.

If you need the full continuous pattern (several search surfaces, a
standing daily dispatch loop, reconciliation back from the pipeline), use
this example's registry/ledger scaffolding as a starting point and layer
`docs/11-topic-engine.md`'s interface table on top — don't start from
scratch.

## Encoding on Windows

Every file here is UTF-8, and `scripts/analyze_site.py` unescapes HTML
entities (`&amp;` → `&`) so non-ASCII text (em dashes, curly quotes)
round-trips correctly. Windows PowerShell 5.1's console may still
*display* an em dash as `â€”` or `�` even when the bytes on disk are
correct — that's a terminal rendering issue, not file corruption. Use the
scripts for writes (they're explicit about UTF-8); if you read a file
directly from PowerShell 5.1, add `-Encoding UTF8` (or use PowerShell 7,
whose default is UTF-8).
