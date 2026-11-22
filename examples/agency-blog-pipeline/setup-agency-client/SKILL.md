---
name: setup-agency-client
description: Sets up a new client instance of the agency-blog-pipeline example end to end — asks for the client's name/domain/services, runs setup_client.py, then walks through the bootstrap (site swap, site analysis, topic proposals, approval, first draft). Use when asked to set this example up for a real client, point it at a new client, or onboard a client onto this pipeline. Claude Code-specific — see ../WALKTHROUGH.md for the same sequence in another AI assistant's chat.
---

# Setup Agency Client

Wraps `examples/agency-blog-pipeline/setup_client.py` so onboarding a new
client is a conversation, not a 40-file find-and-replace. The mechanical
substitution step itself still runs as a plain, deterministic script —
this skill never improvises that part; it only collects the inputs and
then calls the script exactly as documented.

## What this skill is not

It does not analyze the client's site, judge their brand voice, or
propose topics — those genuinely need an agent's judgment, done as a
separate dispatch (Step 4 below), not folded into this setup skill. This
skill's own job ends once the new instance exists and validates.

## Procedure

### Step 0 — Collect the inputs

Ask, in plain conversation, for:
- The client's display name (e.g. "Acme Bookkeeping").
- Their site's domain (informational only).
- Their services: a name, a short slug, and a URL for each — at least
  one. If they don't have a services page yet, ask what they actually
  sell; this is what the hero images and CTAs will key off of.
- Where the new instance should live: a location *outside* this
  framework's own repository for the files setup_client.py writes
  directly (their own machine, their agency's own private repo) — never
  suggest putting a real client's data inside this public template. If
  they also have a local clone of `agent-pipeline-framework` they intend
  to run pipelines from, ask for that path too (`--framework-root`) so
  the pipeline half can go straight into its `pipelines/` directory and
  use its governance scripts immediately.

Don't guess any of these — a wrong service URL or a skipped service
silently produces wrong CTAs later, with no error to catch it.

### Step 1 — Confirm, then run the script

Restate what was collected in one short list and get a yes before
running anything. Then run:

```bash
python examples/agency-blog-pipeline/setup_client.py \
  --name "<Client Name>" --domain <domain> \
  --service "<Name>|<slug>|<url>" [repeat per service] \
  --out <their chosen location> \
  [--framework-root <their framework clone, if they gave one>]
```

If it errors (a malformed `--service`, a path that already exists,
a `--framework-root` that doesn't look like a real clone), fix the
specific input and retry — don't work around the error by hand-editing
whatever the script half-wrote.

### Step 2 — Get the real site in place

Tell them plainly: replace `<instance>/sample-client-site/README.txt`'s
folder with a real, static export of the client's actual site (the
placeholder file explains the exact shape expected). If their site is
JS-rendered, they need to export its rendered HTML first — this skill
doesn't do that for them.

### Step 3 — Bootstrap: mechanical extraction

Run, from the new instance's `topic-engine/` folder:

```bash
pip install -r scripts/requirements.txt
python scripts/analyze_site.py --engine .
```

This only extracts structure (headings, services, existing posts) — no
judgment yet.

### Step 4 — Bootstrap: the judgment step (separate dispatch)

This is where this skill hands off to the Topic Discovery Agent role
(`topic-engine/agents/topic-discovery-agent.md`) as its own dispatch —
read that file's contract and act as that role: read
`site-profile/site-facts.json` plus the real site pages, write
`site-profile/site-profile.md` (using exactly the `## Industry` and
`## Voice and personality` headings, with concrete example phrasings —
the contract explains why), then propose 3–8 topics into
`registry/topics/`.

### Step 5 — Human approval and export

Show the client-facing human the generated `registry/registry.csv`
(`python scripts/fold_ledger.py --engine .` regenerates it) and get
explicit approve/reject decisions per topic
(`scripts/append_ledger.py --event approved|rejected`). Only after that,
export:

```bash
python scripts/export_topics_csv.py --engine . --out <pipeline-dir>/source-data/topics.csv --run-id EXP-1
python scripts/export_brand_profile.py --engine . --out <pipeline-dir>/source-data/brand-profile.md
```

### Step 6 — Hand back

Confirm `scripts/validate_stage_file.py --pipeline <pipeline-dir>` passes
(from inside a framework clone), and say plainly that running an actual
item through the ten stages — drafting, review, approval, publish — is
`base-framework/SKILL.md`'s job from here, not this skill's.

## What this skill must never do

- Never hand-write a client's voice, industry, or services into a file
  this skill controls — those come from the client's real site
  (`site-profile.md`, Step 4) or from what the human told it directly
  (Step 0), never invented to fill a gap.
- Never skip the human-approval step (Step 5) to "move faster" — every
  topic that reaches the pipeline must have an explicit `approved` ledger
  row.
- Never suggest the generated instance's files live inside this public
  framework repository's own tracked paths for a real client.
