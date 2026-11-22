# agency-blog-pipeline — worked example

A complete, runnable example of this framework built for a specific,
common case: **a digital agency running a content pipeline for a
client's blog.** If you run an agency, or you're evaluating this
framework for one, this is meant to be lifted close to as-is for a real
client account — read "Adapting this for a real client" below once
you've seen it run.

The running example: **AgencyA** runs the blog for its client
**ClientA** (`clienta.com` — a fictional small-business bookkeeping and
fractional-CFO service; see `sample-client-site/`). Adapting this for a
real client is a generated step (`setup_client.py`, "Adapting this for a
real client" below), not a rewrite.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for this example's own diagrams
(the topic-engine → CSV handoff, the output-mode branch, and a
sequence diagram of the exact TOP-0001 run seeded below) — separate from
the base framework's own pipeline-agnostic diagrams in
[`../../docs/diagrams/`](../../docs/diagrams/).

## What's already seeded in this checkout

Before running anything, you can just look — this is a runnable example,
but you don't have to run it to see a complete result:

- **Topic engine**: a bootstrap site-read (`topic-engine/site-profile/`),
  5 proposed topics, 4 approved and exported, 1 rejected
  (`topic-engine/registry/registry.csv` shows all 5 and their status).
- **Blog pipeline**: `TOP-0001` carried through all ten stages for real —
  discovered, triaged, drafted (with a generated hero image), agent-reviewed
  (with one flagged-but-not-blocking note), packaged, approved, and staged
  to a local git branch standing in for ClientA's real site repo.
- **The human-review revision loop, demonstrated with `TOP-0002`**: the
  Agent Reviewer passed the first draft as structurally complete, but the
  human reviewer judged it too thin and asked for more depth via
  `scripts/advance_stage.py --revise` instead of approving or rejecting
  outright — see `stage-store/07-rejected/TOP-0002.md` (the first
  attempt, terminal with `revision: true`) and
  `stage-store/08-executed/TOP-0002-v2.md` (the redraft that actually
  addressed the feedback, approved and staged). This is a real,
  recurring case — human review doesn't only ever rubber-stamp what
  automated review already passed, and this framework's design accounts
  for that explicitly (`docs/06-review-and-notification.md`, "Rejection
  is not a dead end").
- `TOP-0003` and `TOP-0004` are approved and exported to
  `source-data/topics.csv` but not yet picked up — a realistic backlog,
  not a failure. `pipeline/clienta-blog-pipeline/status-report.csv`
  shows all four at a glance (note: it reports plain `TOP-0002` as
  "Rejected," which is accurate for that exact record — it doesn't
  follow `supersedes` chains to `TOP-0002-v2`, so read the row's
  Comments column, not just its Status, for the full story).

Run `python pipeline/clienta-blog-pipeline/scripts/init_demo_site_repo.py`
to generate the local git repo these were staged to (it's gitignored —
generated state, not source) and inspect
`git log --all --oneline` / `git diff main stage/insights-top-0001` (or
`stage/insights-top-0002-v2`) inside it to see exactly what a real
publish would produce.

## What's here, and why three pieces

```
agency-blog-pipeline/
├── client-config.yaml       ClientA's values -- every script below reads this, never hardcodes
├── sample-client-site/      ClientA's site (fixture) -- what gets analyzed
├── topic-engine/            Decides WHAT to write about -- site analysis -> topics CSV
├── pipeline/
│   └── clienta-blog-pipeline/   Decides HOW to write it -- the 10-stage governed pipeline
├── setup_client.py          Generates a fresh, empty instance for a real client (no AI involved)
├── _templates/              What setup_client.py renders config.yaml/spec.md/logic.md from
├── setup-agency-client/     Claude Code Skill wrapping setup_client.py as a conversation
└── WALKTHROUGH.md           Step-by-step that works with any AI assistant, or none
```

This mirrors how an actual agency engagement works: you don't get a
content calendar for free, and you don't want the two concerns — *what's
worth writing* and *is this draft good enough to publish* — governed by
the same logic. The topic engine is the optional, lighter-weight piece
(`docs/11-topic-engine.md`'s pattern); the blog pipeline is the full
governed framework (`docs/01-governance-rules.md`) that every draft goes
through regardless of where its topic came from.

## Run it yourself

There are three distinct things "running this" can mean here — worth
being precise about, since they're not the same automation:

1. **Just look at what's already here.** No setup, nothing to run —
   see "What's already seeded in this checkout" above.
2. **Set up a new client and run the bootstrap** (site read → proposed
   topics → human approval → CSV export). In Claude Code, invoke
   [`setup-agency-client/SKILL.md`](setup-agency-client/SKILL.md) — it
   runs this part automatically, as one conversation, calling
   `setup_client.py` and then dispatching the site-read and
   topic-proposal steps itself. With any other AI assistant (Codex,
   ChatGPT, Gemini), or none at all, see `WALKTHROUGH.md` Parts 1–3
   instead — same sequence, done by hand, one step at a time.
3. **Run one topic through the governed pipeline itself**
   (draft → agent review → human approval → publish). This is a
   *separate* automation from step 2's Skill — in Claude Code, it's
   `base-framework/SKILL.md` (the generic pipeline-runner that dispatches
   Source → Triage → Content → Reviewer → Publisher automatically for
   *any* pipeline on this framework, not something built specifically for
   this example). With any other assistant, see `WALKTHROUGH.md` Part 4 —
   you tell your assistant which role to act as, one dispatch at a time;
   nothing here currently chains that automatically outside Claude Code.

See [`WALKTHROUGH.md`](WALKTHROUGH.md) for the full step-by-step either
way — every step there is marked `[TERMINAL]` (a literal, copy-pasteable
command, no shell-specific syntax) or `[ANY AI CHAT]` (paste a given
prompt into whichever assistant you use and save its reply to the named
file) — and [`topic-engine/README.md`](topic-engine/README.md) /
[`pipeline/clienta-blog-pipeline/spec.md`](pipeline/clienta-blog-pipeline/spec.md)
for the full detail on each piece.

## Adapting this for a real client

**Don't find-and-replace `ClientA` by hand** — the name appears in
dozens of files, and a manual pass is exactly the kind of step that's
easy to get *mostly* right and never notice the one spot you missed.
Every script in this example reads the client's name, services, and
brand colors from one file, `client-config.yaml` — nothing is
hardcoded. Adapting this for a new client is a generated step, not a
search-and-hope one:

```bash
python setup_client.py --name "Acme Bookkeeping" --domain acme.com \
    --service "Bookkeeping|bookkeeping|/services/bookkeeping" \
    --service "Tax Prep|tax-prep|/services/tax-prep" \
    --out ../acme-blog-pipeline
```

This generates a fresh, empty instance — no `ClientA` seed data carried
over — with `topic-engine/` and `pipeline/acme-bookkeeping-blog-pipeline/`
both reading the new `client-config.yaml` it writes. Run
`python setup_client.py --help` for every option, including
`--framework-root` (places the pipeline half directly into a clone of
this repo's `pipelines/` directory, so it can use `scripts/advance_stage.py`
and `base-framework/SKILL.md` immediately — the way a pipeline on this
framework actually runs). **Put the output somewhere other than inside
this public repository** — the generated instance is meant to hold a
real client's data, which shouldn't live inside an open-source template
project.

From there:

1. Replace `<new instance>/sample-client-site/` with a real export of
   the client's actual site (`topic-engine/scripts/analyze_site.py`'s
   docstring explains what it needs — static, server-rendered HTML;
   export a JS-heavy site first).
2. Run the bootstrap (`topic-engine/scripts/analyze_site.py`, then have
   an AI assistant act as the Topic Discovery Agent and write a real
   `site-profile.md` and propose real topics against the real site) —
   use [`setup-agency-client/SKILL.md`](setup-agency-client/SKILL.md) if
   you're in Claude Code, or [`WALKTHROUGH.md`](WALKTHROUGH.md) for the
   exact sequence with any other assistant.
3. Point the new instance's `config.yaml`'s
   `output_destinations[0].connector_ref` at the client's actual site
   repo (`git:github.com/...`) instead of the local
   `./demo-site-repo` stand-in, and set up whatever credential
   `docs/08-connectors-and-tooling.md` calls for — or, if the client isn't
   on a git-based static site, leave `output_mode: local_files` and hand
   the generated files to their CMS instead (`spec.md`, "Output
   Destinations").
4. Replace `scripts/generate_hero_svg.py`'s placeholder output with real
   image generation once you have a dependency/API budget for it — it
   exists only so this example runs with nothing but Python.

Everything else — the ten-stage governance, the review policy, the
run-request filters, the status-report discipline, every script — needs
no per-client edit at all; that's the part of this framework that's the
same for every pipeline, and it's also why `setup_client.py` can copy it
verbatim instead of templating it.
