---
client: ClientA
produced_by: topic-discovery-agent v1
created_at: 2026-11-22T00:00:00Z
based_on: site-profile/site-facts.json, index.html, about.html, services.html, blog/index.html
---

# ClientA — Site Profile

## Industry

Financial back-office services for small businesses: monthly
bookkeeping, cash flow forecasting, and fractional CFO advisory. The site
is explicit about its segment — "five to thirty people" — and about who
it's *not* for ("not ready to hire a full-time CFO"), so the audience is
specifically small service businesses, small SaaS teams, and agencies
that have outgrown ad hoc bookkeeping but aren't yet big enough for an
in-house finance hire.

## Voice and personality

- **Direct and plain-English, deliberately anti-jargon.** The About page
  states this as policy, not just style: "we'd rather say 'you're
  spending more than you're bringing in' than 'there is a negative
  variance in operating cash flow.'" Any drafted content should translate
  finance concepts into plain consequences, not display financial
  vocabulary.
- **Warm, a little informal, reassuring.** "Books that make sense,"
  "no jargon you have to Google afterward," "we talk like people, not
  auditors." The tone treats financial anxiety as the real starting
  point for most readers, not an afterthought.
- **Confident without being salesy.** Claims are concrete and specific
  (a rolling 13-week forecast, closed books within two weeks) rather than
  broad adjectives ("expert," "trusted," "best-in-class" do not appear
  anywhere on the site — avoid them in drafted copy too).
- **"We" voice throughout**, never "I" or a named individual, even on the
  About page's founder story.

## Services (ground topics in these — `service_ref` values)

| service_ref | name | url |
|---|---|---|
| `bookkeeping` | Monthly Bookkeeping | `/services/bookkeeping` |
| `cash-flow-forecasting` | Cash Flow Forecasting | `/services/cash-flow-forecasting` |
| `fractional-cfo` | Fractional CFO Advisory | `/services/fractional-cfo` |

## Existing blog coverage (check new topics against this)

| title | url |
|---|---|
| How Often Should a Small Business Reconcile Its Books? | `/blog/how-often-reconcile-books` |
| 5 Signs You Need a Fractional CFO (Not a Full-Time One) | `/blog/signs-you-need-fractional-cfo` |

Both existing posts sit under Fractional CFO / Bookkeeping. **Cash Flow
Forecasting has no existing post at all** — the clearest, most literal
coverage gap in the current blog.
