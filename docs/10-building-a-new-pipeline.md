# 10 — Building a New Pipeline

A step-by-step walkthrough, illustrated against one of the four cases from
the original request — "scan a LinkedIn search for relevant posts, decide
which are worth engaging with by writing an original post in response, get
it reviewed, publish to LinkedIn." **This is illustration only — none of
this pipeline's files have actually been created in this delivery** (see
`README.md`, "Status"). Treat the snippets below as what you'd write, not
as something already sitting in `pipelines/`.

Steps 0–5 (everything up to but not including creating scheduled tasks) can
be mechanized from a single natural-language brief by the
`pipeline-builder` skill (`base-framework/pipeline-builder/SKILL.md`) —
it runs this same walkthrough end to end and refuses to hand back a
pipeline that doesn't pass `validate_stage_file.py --pipeline
pipelines/<name>` clean. This section remains the authoritative reference
for what "done" looks like at each step, whether you use that skill or
write the files by hand; Steps 6–8 (creating scheduled tasks, dry-running,
and going live) are deliberately outside what that skill does, since those
are externally-consequential actions this framework never automates on
your behalf.

## Step 0 — Assemble your own context pack for this build (recommended)

Before drafting `spec.md`, apply the same discipline the Content Agent
uses at runtime (step 0 of `base-framework/agents/content-agent.md`) to
the task of *building the pipeline itself*: what does this build actually
need to accomplish, what's explicitly out of scope, what existing pipeline
or brand-voice doc should it pattern-match against, and what does "ready
to scaffold" mean. This is the `context-pack-builder` skill
(https://github.com/ViksyaHQ/context-pack-builder) used as an authoring
tool rather than a runtime one — separate from the pipeline it produces,
useful precisely because a half-specified pipeline design is the same
starved/drowned failure mode this framework is built to catch downstream.
Not required, but cheap, and it tends to surface the Step 4 judgment calls
early instead of midway through writing `logic.md`.

## Step 1 — Write the purpose, one paragraph

Before touching any template, write down in plain language what "done"
looks like for one item. This is what goes in `spec.md`'s `purpose` field,
and forces the scope decision up front:

> Scan a defined LinkedIn search for posts from a specific list of accounts
> discussing enterprise AI transformation. For posts that raise a point
> worth responding to publicly, draft an original LinkedIn post that adds a
> distinct perspective — never a bare reaction or a summary of the source
> post. Publish only after agent and human review.

## Step 2 — Scaffold the folder

```
python scripts/scaffold_pipeline.py linkedin-search-to-original-post
```

This creates `pipelines/linkedin-search-to-original-post/` with `spec.md`,
`logic.md`, and `config.yaml` copied from `templates/` and the ten empty
`stage-store/` folders.

## Step 3 — Declare the source and destination in `spec.md` and `config.yaml`

Source: a LinkedIn search connector — check the MCP registry first
(`docs/08-connectors-and-tooling.md`); if none exists, `browser` via Claude
in Chrome against a saved search URL, `access: read_only`. Destination: a
LinkedIn posting connector or, absent one, `browser`, `action_scope:
create_draft_post` (never account-level access) — draft, not publish
directly, since the human review gate means "publish" from the pipeline's
own perspective is really "hand a reviewed, approved draft to a step a
human can still stop."

**Fixed or runtime scope?** Most pipelines fix `source.scope` once, here,
and never change it — an account handle or a folder path rarely needs to
vary per run. If this pipeline's search or read target should legitimately
change from run to run (a rotating term supplied by a separate process),
set `source.scope_source: runtime` instead and see
`docs/05-execution-model.md`, "Runtime-parameterized sources," for what
that adds (a `run-requests/` handoff and one extra orchestrator step
either side of the Source Agent dispatch). Don't reach for `runtime` by
default — it's the exception, for the pipelines that actually need it.

## Step 4 — Write `logic.md`

This is the one file that requires actual judgment, not boilerplate. For
this example, following `templates/logic.template.md`'s schema:

- **Decision inputs**: post author, post text, engagement count, whether
  this account has been engaged with in the last N days (avoid over-engaging
  the same accounts).
- **Decision rules** (ordered): discard if the post is promotional /
  product-launch content with no discussion angle; discard if this account
  was engaged with in the last 7 days; escalate to human review directly
  (skip drafting) if the post touches a competitor by name; otherwise
  proceed if the post makes a claim or takes a position substantive enough
  to respond to.
- **Default action**: discard (a pipeline should default to doing less, not
  more).
- **Prohibited**: never proceed on a post solely because of high engagement
  with no substantive content — that's optimizing for visibility, not
  for the stated purpose.

## Step 5 — Decide on role overrides

The Content Agent likely needs this brand's voice and any "no hype"
vocabulary rules as an override (`templates/agent-override.template.md`),
appended to the base Content Agent prompt — this override also feeds the
context pack's "Contracts & constraints" section (step 0 of
`base-framework/agents/content-agent.md`), so a competitor-mention rule
stated here shows up there too, rather than needing to be stated twice.
The Agent Reviewer likely needs an added checklist item specific to this
pipeline: "flags any claim about a competitor for mandatory human review
regardless of agent-review verdict."

Before moving on, run
`python scripts/validate_stage_file.py --pipeline pipelines/linkedin-search-to-original-post`
— this checks `config.yaml` against the governance schema and flags any
unfilled template placeholder still left in `spec.md`, `logic.md`,
`config.yaml`, or an `agents/*.md` override (the exact check
`base-framework/SKILL.md` runs before any run, so it's better to hit it
now than on the first scheduled fire).

## Step 6 — Create the scheduled tasks

Create a discovery-run scheduled task (e.g., daily) and a publish-run
scheduled task (e.g., a few hours after, giving you a review window)
using the scheduled-task tools — never a session-local cron
(`docs/05-execution-model.md`). Record both trigger IDs back into
`config.yaml`.

## Step 7 — Dry-run before trusting the schedule

Run a discovery run manually in an interactive session first, against real
data, and read the resulting `05-pending-human-review` packets yourself
before the schedule is live. This is where a `logic.md` that looked right
on paper usually reveals an edge case (an ambiguous account, a repost with
no original commentary) worth handling explicitly in the decision rules
rather than discovering it silently in production.

## Step 8 — Review, approve, watch the publish run

Once comfortable, let the schedule run. Review async
(`docs/06-review-and-notification.md`) as digests arrive. Spot-check the
first several `08-executed` receipts against what actually appears on
LinkedIn — the framework verifies the content hash matches what was
approved, but only you can confirm the destination did what the receipt
claims.

## Applying this to the other three examples

- **X post**: identical shape, swap the source/destination connector and
  the brand-voice override for X's format constraints (thread structure,
  character limits).
- **Website update**: source is likely a folder of drafts or a CMS
  connector; destination is a git commit to the website repo (a
  `filesystem`/`connector` output, `action_scope: commit_to_path`) — note
  this makes the *publish* step itself just another reviewed git commit,
  consistent with how you already work with 11ty/Cloudflare Pages.
- **Blog creation**: same as the LinkedIn case, but the Content Agent does
  full drafting rather than a short reactive post, and the Agent Reviewer's
  policy weighs more heavily on factual support and citation, given the
  longer form.
- **The "simple" republishing case** (read an already-reviewed article,
  post it to the blog/X/LinkedIn): source is the reviewed-articles folder
  itself (`filesystem`, `read_only`); `logic.md` is close to "proceed if not
  already published to this channel, discard otherwise"; the Content Agent's
  job is reformatting for the destination, not generating new material —
  everything else in the pipeline (both review gates, the audit log, the
  publish-run mechanics) is unchanged. This is the concrete demonstration of
  the point made in `docs/00-overview-and-philosophy.md`: "simple" is a
  thin `logic.md` and a light Content Agent step, not a different pipeline
  shape.
