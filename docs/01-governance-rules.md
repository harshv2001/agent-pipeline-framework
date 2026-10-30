# 01 — Governance Rules

These rules are the base class's "final methods" — every pipeline built on
this framework inherits them and none may override, weaken, or bypass them.
`scripts/validate_stage_file.py` and `scripts/advance_stage.py` enforce the
mechanical parts of these rules; the rest are enforced by how agent prompts
are written (see `docs/04-agent-roles.md`) and by code review of any
pipeline's `spec.md` before it's allowed to run.

## Rule 1 — Sources are read-only, permanently

No agent, in any pipeline, ever writes to, edits, deletes from, reorders, or
otherwise mutates whatever it is reading from — a website, a folder, a
social account, a search result set, an inbox. This holds even for actions
that seem harmless (marking something "read," liking a post to bookmark it,
renaming a file for organization).

Enforcement:

- Every source is declared in a pipeline's `config.yaml` with
  `access: read_only`. Where the underlying connector or MCP server supports
  scoped, read-only credentials, those are what gets configured — not a
  full-access credential the agent is merely instructed not to misuse.
  Where only a general-access credential is available (a personal browser
  session via Claude in Chrome, for instance), the source agent's prompt
  explicitly enumerates the prohibited actions and the human reviewer
  spot-checks for accidental writes during setup.
- `scripts/validate_stage_file.py` rejects any `config.yaml` that declares
  `access: write` (or omits `access`) on anything referenced as a source.
- The Source Agent role (`base-framework/agents/source-agent.md`) has no
  write tools in its allowed tool list at all — this is enforced at the
  agent-definition level, not just by instruction.

## Rule 2 — Everything is staged, nothing skips a stage

An item's life inside a pipeline is a sequence of append-only records in
named stage folders (the "stage-store" — see
`docs/03-stage-store-model.md`). An item moves forward one stage at a time;
a record already written for a completed stage is never edited in place.
Corrections happen by writing a new record that supersedes the old one and
says so, not by overwriting history.

This is what makes "show me exactly what was found, decided, drafted, and
approved for item X" answerable by reading files, months later, without
asking an agent to remember anything.

## Rule 3 — Two independent reviews gate every external action

Before any pipeline output leaves the pipeline's own stage-store — is
posted, published, sent, or written to any location the pipeline doesn't
own — it must pass both:

1. **Agent review** — a reviewer agent that did not produce the content
   checks it against the pipeline's own written policy (see
   `base-framework/agents/agent-reviewer.md`): factual support, brand voice,
   AI-disclosure requirements if applicable, no PII, no claims the source
   material doesn't support. A failure sends the item back for revision, not
   forward.
2. **Human review** — an explicit decision by you, recorded with a
   timestamp and (where the review happened in a live session) the
   substance of what you said. There is no default-approve timeout, no
   "auto-publish if not reviewed within N hours." Un-reviewed items simply
   wait.

Both reviews are for the same, exact content that will be published — see
Rule 4.

## Rule 4 — Approved content cannot be silently altered before publish

Between an item being approved and being executed, the Publisher Agent
verifies the content it's about to publish matches, byte-for-byte (via a
content hash recorded at approval time), what was actually reviewed. If
they don't match, publishing is refused and the item is kicked back to
agent review. This closes the gap where a "final polish" edit after
approval quietly reintroduces something nobody reviewed.

The hash locked at approval covers the review packet's body by
construction (`content_hash`). For a pipeline whose output includes a
non-text artifact finalized at draft time — an image, a rendered page
(`base-framework/agents/content-agent.md`, Contract step 5) — that file is
covered too, as a `manifest_hash` over the body plus every path the
Content Agent lists in the draft's `manifest` field
(`templates/review-packet.template.md`,
`scripts/_common.py:manifest_hash`). `scripts/advance_stage.py
--verify-manifest <item_id>` is the script-enforced check the Publisher
Agent runs before publishing (its Contract step 1) — not a thing to
recompute by eye. A `manifest` is optional: an item with none locked is
still covered for its body text, just not for anything built later, at
publish time, from live destination state (e.g. a destination-specific
index insertion) — closing that gap for a given pipeline means moving that
assembly to draft time, per Contract step 5.

## Rule 5 — Full, append-only audit trail

Every stage transition, every agent's action, every automated review
verdict, and every human decision is written to that pipeline's audit log
(`stage-store/09-audit-log/`) as a new entry. Nothing in the audit log is
ever edited or deleted, including rejected or discarded items — a discarded
item's record says it was discarded and why; it is not removed.

## Rule 6 — Config changes are reviewable like code changes

Because the stage-store and the pipeline definitions live in git, any change
to a pipeline's `config.yaml`, `logic.md`, or `spec.md` is a diff you can
review before it takes effect — the same discipline as reviewing a code
change, applied to the rules that decide what an agent does. Treat editing
a live pipeline's decision logic with the same care as editing its
publishing credentials.

## Rule 7 — A pipeline can only add restrictions, never remove them

A pipeline's `spec.md` may add stages, add review criteria, lower automation
thresholds (e.g., "escalate to human review more often than the base
default"), or restrict which connectors it uses. It may never remove a
stage, weaken a review requirement, or grant an agent role a capability the
base role doesn't have. `docs/02-inheritance-model.md` specifies exactly
which fields are open for this kind of extension and which are fixed.

## What happens on a rule violation

If any script or agent detects an attempted violation of Rules 1, 3, 4, or
7 (the rules that are mechanically checkable), the run halts, the attempted
action is logged as a policy violation in the audit log, and the item is
routed to human review with the violation flagged — it is never silently
corrected and allowed to proceed.
