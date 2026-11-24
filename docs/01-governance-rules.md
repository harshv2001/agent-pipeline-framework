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
  spot-checks for accidental writes during setup — this case is
  prompt-level enforcement with a human backstop, not a credential
  boundary; see "What these guarantees actually mean" below.
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
says so, not by overwriting history. "Never edited in place" describes
what this framework's own scripts do, not a permission boundary — see
"What these guarantees actually mean" below for exactly what that does
and doesn't rule out.

This is what makes "show me exactly what was found, decided, drafted, and
approved for item X" answerable by reading files, months later, without
asking an agent to remember anything.

## Rule 3 — Two independent reviews gate every external action

"Independent" here means a separate automated review stage followed by a
separate human approval stage — same model, same session, same
credentials as the rest of the pipeline. It is not a separate model,
isolated credentials, or an independently enforced security boundary
between the two; what makes it independent is that the Agent Reviewer is
a fresh dispatch with no memory of the Content Agent's own reasoning
(`base-framework/agents/agent-reviewer.md`, "Inputs": "Not given: any
explanation from the Content Agent... this dispatch must be independent
— reviewing the draft as it would look to a first-time reader"), and
that the human decision is a genuinely separate, explicit act, never
inferred or defaulted.

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
item's record says it was discarded and why; it is not removed. Same
caveat as Rule 2: this is what `scripts/_common.py:append_audit_log` does
(always appends, never rewrites), not a write-protection on the file
itself — see "What these guarantees actually mean" below.

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

## What these guarantees actually mean

This document uses "read-only," "append-only," and "immutable" to
describe three different strengths of enforcement. Conflating them is
exactly the kind of gap an outside reader would be right to flag, so
here's each one stated precisely:

- **Cryptographically checked, every time** — Rule 4's content hash,
  and only that. `scripts/advance_stage.py --verify-manifest` re-hashes
  the approved content immediately before publish and refuses on any
  mismatch, including a single-character edit. This is the one
  guarantee here that this framework's own tooling cannot be talked
  into silently violating.
- **Enforced by what the scripts choose to do, not by a permission
  boundary** — "append-only" and "immutable" (Rules 2 and 5;
  `docs/03-stage-store-model.md`, "Immutability by stage"). No script
  this framework ships ever rewrites a stage-store record once written
  — `advance_stage.py` only ever creates new files or appends new
  audit-log entries. But nothing stops a human (or a compromised
  credential) with ordinary git write access from hand-editing a
  historical file directly; git itself enforces nothing here. The real
  guarantee is "this framework's own codepath never does this," not
  "this cannot be done." If you need the stronger version, add git
  branch protection or a write-once storage backend on top — this
  framework doesn't provide it on its own.
- **Enforced at the tool-grant level where the connector allows it,
  otherwise prompt-level with a human spot-check as the backstop** —
  Rule 1's read-only sources. Where a connector exposes a genuinely
  read-only credential or tool (most MCP servers, most APIs), the
  Source Agent's tool grant has no write capability at all for that
  connector — code-enforced, not just instructed. Where only a
  general-access credential is available and the connector is
  something like a browser session (Claude in Chrome against a
  logged-in account, for instance), the agent's own tools can
  technically perform a write action on that account; what stops it is
  the prompt's explicit prohibition plus a human's spot-check during
  setup, not a credential boundary. This is a real, known risk
  category, not a hypothetical one — it's why a browser-connector
  source should always be treated as the weaker case and reviewed
  accordingly, never assumed equivalent to a scoped API credential.

If a pipeline you're building needs something stronger than "this
framework's own tooling doesn't do it" — a compliance requirement that
data literally cannot be altered, not just isn't altered by this code —
that's outside what this framework closes on its own.

## What happens on a rule violation

If any script detects an attempted violation of Rules 1, 3, 4, or 7 (the
rules that are mechanically checkable), it halts and refuses to proceed —
no publish, no stage transition, no silent correction. For Rule 4
specifically, `scripts/advance_stage.py --verify-manifest` (and its
self-contained duplicate, `examples/agency-blog-pipeline/pipeline/
clienta-blog-pipeline/scripts/publish_output.py`'s
`verify_approved_content()`) appends the violation to that pipeline's
audit log itself, as `event: violation`, the moment it detects a mismatch
— an earlier version of this framework left that logging step to the
dispatched role's own discretion (a separate `--event` call it could
forget to make), which is exactly the kind of prompt-level-only
enforcement "What these guarantees actually mean" above warns against
relying on for a rule this document calls mechanically checkable.

What does *not* happen automatically: the item is not moved anywhere.
A hash-mismatched item stays exactly where it was found —
`06-approved`, already past both reviews — it is not "routed to human
review," since it's already been through one; claiming otherwise would
misdescribe what actually happened. Unsticking it is a deliberate,
separate human act: read the violation entry, decide what changed, and
run `scripts/advance_stage.py --revise --from-stage 06-approved
<item_id> --reason "..."` (reject-with-feedback into `07-rejected`, plus
a new versioned `03-draft` for a fresh agent-review-then-human-review
pass) or leave it rejected outright. Nothing re-approves it
automatically, and nothing — including this framework's own
scripts — ever hand-edits the `06-approved` record to make it match
again; Rule 2's "never edited in place" holds here too.

Rules 1 and 3 (a prohibited write attempt, a review stage skipped) are
caught by tool-grant limits and `ALLOWED_TRANSITIONS` respectively, not
by a standalone verification script with an audit log of its own to
write to — logging those as `event: violation` is still the acting
role's own responsibility (`base-framework/agents/archivist-agent.md`,
Contract step 4), the same prompt-level discipline as everything else
in "What these guarantees actually mean."
