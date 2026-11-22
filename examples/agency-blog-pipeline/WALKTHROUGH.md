# Walkthrough — works with any AI assistant, or none

This replaces the old single-bash-block "Run it yourself" section. Every
step below is marked **[TERMINAL]** (a literal command — run it exactly
as written, in any shell) or **[ANY AI CHAT]** (open whichever assistant
you already use — Claude, Codex, ChatGPT, Gemini, or Claude Code — paste
the given prompt, and save its reply to the named file). Nothing here
needs a specific assistant or a specific terminal: `[TERMINAL]` commands
are plain Python, no shell-specific syntax (no `$(date ...)`, nothing
that only works in bash), and `[ANY AI CHAT]` steps need nothing but a
chat box you can paste text into and copy text out of — not file access,
not code execution, not a Claude-specific "Skill."

**If your assistant *does* have file/terminal access** (Claude Code,
Codex CLI, a terminal-connected Gemini session), it can just do the
`[ANY AI CHAT]` steps directly against the real files instead of you
copy-pasting — that's what `setup-agency-client/SKILL.md` automates for
Claude Code specifically. This walkthrough is the manual version that
works everywhere else too.

## What you need

- Python 3.9+ and `pip` (for the mechanical scripts — no AI involved in
  these).
- Any chat-based AI assistant, for the steps marked `[ANY AI CHAT]`.
- `git`, only if you'll use the default `output_mode: git_branch` — skip
  it entirely by setting `output_mode: local_files` in `config.yaml`.

## Part 1 — Set up a new client (skip if you're just trying the ClientA demo)

**[TERMINAL]**
```
python examples/agency-blog-pipeline/setup_client.py \
  --name "Acme Bookkeeping" --domain acme.com \
  --service "Bookkeeping|bookkeeping|/services/bookkeeping" \
  --service "Tax Prep|tax-prep|/services/tax-prep" \
  --out ../acme-blog-pipeline
```
Replace the name/domain/services with the real client's. See
`setup_client.py --help` for every option, including `--framework-root`
if you have a clone of this repo to run the pipeline from directly.

**[TERMINAL]** Put a real, static export of the client's site at
`<the --out path>/sample-client-site/` (the generated `README.txt` there
says exactly what's expected).

From here on, "the engine" means `<the --out path>/topic-engine/` and
"the pipeline" means `<the --out path>/pipeline/<slug>-blog-pipeline/`
(or wherever `--framework-root` placed it).

## Part 2 — Bootstrap: read the site

**[TERMINAL]**
```
cd <the engine>
pip install -r scripts/requirements.txt
python scripts/analyze_site.py --engine .
```
This writes `site-profile/site-facts.json` — mechanical extraction only
(headings, services, existing posts). No judgment yet.

**[ANY AI CHAT]** — open `site-profile/site-facts.json` and the real
site's pages, then paste this:

> You are acting as the Topic Discovery Agent described in
> `topic-engine/agents/topic-discovery-agent.md` (paste that file's
> contents here too, or attach it). Here is this client's
> `site-facts.json`: [paste its contents]. Here are the client's raw
> pages: [paste the relevant page text]. Write `site-profile/site-profile.md`
> exactly per that agent file's "Outputs" section — industry and voice,
> using exactly the headings `## Industry` and `## Voice and
> personality`, with at least one concrete example phrasing grounded in
> the real site text, never generic flattery. Then propose 3–8 topics
> following `templates/topic.template.md`'s exact frontmatter shape, each
> grounded in a real service and a real coverage gap.

Save its reply: the `site-profile.md` portion goes to
`site-profile/site-profile.md`; each proposed topic goes to its own file
under `registry/topics/` (ask the assistant for the exact filename,
`TOP-0001.md` style — or run `python scripts/next_topic_id.py --engine .`
yourself for each one before asking it to fill in that id).

**[TERMINAL]** Log a `proposed` ledger row for each topic file you just
saved:
```
python scripts/append_ledger.py --engine . --topic-id TOP-0001 \
  --event proposed --actor "topic-discovery-agent" --run-id BOOTSTRAP-1 \
  --detail "Initial batch"
```

## Part 3 — Human approval, then export

**[TERMINAL]**
```
python scripts/fold_ledger.py --engine .
```
Open the resulting `registry/registry.csv` and decide, per topic:

**[TERMINAL]** for each decision:
```
python scripts/append_ledger.py --engine . --topic-id TOP-0001 \
  --event approved --actor "<your name>" --run-id REVIEW-1 --detail "Approved as proposed"
```
(`--event rejected` instead, same shape, for the ones you don't want.)

**[TERMINAL]**
```
python scripts/export_topics_csv.py --engine . \
  --out <the pipeline>/source-data/topics.csv --run-id EXP-2026-01
python scripts/export_brand_profile.py --engine . \
  --out <the pipeline>/source-data/brand-profile.md
```
This is the engine's entire output into the pipeline — two generated
files, idempotent to re-run later.

## Part 4 — Run one topic through the pipeline

This part needs an AI assistant that can read/write files in the
pipeline folder and, ideally, run the terminal commands too — Claude
Code, Codex, or a terminal-connected assistant session. The underlying
role files (`base-framework/agents/*.md`, this pipeline's
`agents/content-agent.md`) are plain markdown with no Claude-specific
calls, so any such assistant can act as each role in turn; only the
*automatic* dispatch between roles is Claude Code-specific
(`base-framework/SKILL.md`) — elsewhere, you tell your assistant which
role file to act as, one dispatch at a time, same as the `[ANY AI CHAT]`
pattern above.

1. Write a `run-requests/pending/` file (template: base framework's
   `templates/run-request.template.md`) with `scope_value: id=TOP-0001`.
2. **[ANY AI CHAT or terminal-connected assistant]**, one role at a time:
   Source Agent → `01-raw-metadata`, Triage Agent (reads `logic.md`) →
   `02-triage-decisions`, Content Agent (reads `agents/content-agent.md`
   and `source-data/brand-profile.md`) → `03-draft` (plus a hero image —
   `python scripts/generate_hero_svg.py --title "..." --service-ref ... --out stage-store/03-draft/TOP-0001-hero.svg`
   **[TERMINAL]**), Agent Reviewer → `04-agent-review`, Human Liaison →
   `05-pending-human-review`.
3. **[TERMINAL]** You approve:
   ```
   python <framework-root>/scripts/advance_stage.py --pipeline . --approve TOP-0001
   python <framework-root>/scripts/advance_stage.py --pipeline . --verify-manifest TOP-0001
   ```
4. **[TERMINAL]** Publish:
   ```
   python scripts/init_demo_site_repo.py   # first time only, if output_mode: git_branch
   python scripts/publish_output.py --item-id TOP-0001
   python <framework-root>/scripts/advance_stage.py --pipeline . --move TOP-0001 --from 06-approved --to 08-executed --actor "publisher-agent" --detail "staged"
   python tooling/build_status_report.py
   ```

Steps 3–4 are genuinely a scripted, orchestrated "publish run" in this
framework's own design (`docs/diagrams/01-detailed-architecture.md`,
"Publish run — dispatch order") — chaining them by hand here is for
transparency while you're learning the mechanics, not the long-term way
to operate a pipeline you trust.
