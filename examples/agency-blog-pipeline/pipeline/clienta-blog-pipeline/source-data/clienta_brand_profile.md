---
client: ClientA
exported_from: ../../topic-engine/site-profile/site-profile.md
exported_at: '2026-11-22T00:00:00Z'
---

# ClientA — Brand Profile (pipeline's own copy)

Copied from the topic-engine's site read at export time, so this pipeline
never has to reach back into `topic-engine/` at run time — the topic
engine is optional to re-run, and this pipeline's own `source-data/`
should be self-contained once a batch of topics has been handed off.

## Voice

- Direct and plain-English, deliberately anti-jargon: say "you're
  spending more than you're bringing in," never "a negative variance in
  operating cash flow."
- Warm, a little informal, reassuring — financial anxiety is the real
  starting point for most readers, not an afterthought.
- Confident and specific rather than salesy: concrete claims (a rolling
  13-week forecast, books closed within two weeks), never broad
  adjectives like "expert," "trusted," or "best-in-class."
- "We" voice throughout, never "I" or a named individual.

## Industry / audience

Financial back-office services (bookkeeping, cash flow forecasting,
fractional CFO advisory) for small businesses — specifically five to
thirty people: service businesses, small SaaS teams, and agencies that
have outgrown a spreadsheet but aren't ready for a full-time finance
hire.

## Visual palette (for hero images — see agents/content-agent.md)

- Navy `#1B2A41` (headings, primary)
- Parchment `#F7F4EE` (background)
- Teal `#2E8B7B` (accent)

No literal client logo in any hero image or inline diagram — palette and
simple geometric motifs only (same discipline as the private framework's
Viksya pipelines use for their own brand palette).

## Services (for CTA/backlink accuracy)

| service_ref | name | url |
|---|---|---|
| `bookkeeping` | Monthly Bookkeeping | `/services/bookkeeping` |
| `cash-flow-forecasting` | Cash Flow Forecasting | `/services/cash-flow-forecasting` |
| `fractional-cfo` | Fractional CFO Advisory | `/services/fractional-cfo` |
