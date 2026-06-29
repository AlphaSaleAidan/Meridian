# Pricing & Commission

## Pricing model — custom per-deal

Meridian no longer uses published fixed tier prices. You set a **custom monthly price per deal** in the portal when generating a proposal. Do NOT quote specific monthly prices before discovery.

When a prospect asks "how much?" — lead with value:
> "We do custom pricing based on what we find. Most merchants see CA$2,800+/mo in found revenue in week one — let me show you that first, then the price question answers itself."

The three plan tiers still define the **feature set** (not a public price):

| Plan | Features | Locations | Cameras | Multi-location | API access |
|------|----------|-----------|---------|----------------|------------|
| **Standard** | All POS analytics agents | 1 | — | — | — |
| **Premium** | Standard + camera intelligence | 1 | Yes | — | — |
| **Command** | Premium + enterprise features | Unlimited | Yes | Yes | Yes |

All plans:
- Month-to-month, no contract
- No setup fee
- Includes 18-month historical backfill
- All POS analytics agents
- Email digest + in-app alerts
- One-click cancel

**Standard** adds: POS integration + the full POS analytics agent fleet (revenue forecasting, peak hours, customer LTV, inventory intelligence, etc.) + email digest. 1 location only.

**Premium** adds (vs Standard): camera intelligence (foot traffic, queue, dwell, zone analytics), customer segmentation, priority support.

**Command** adds (vs Premium): multi-location rollups, custom AI models, dedicated account manager, API access.

## Currency rules

- Canadian merchants → always quote CAD. Use the `CA$` prefix verbally and in writing.
- US merchants → USD.
- Never mix. Billing follows the merchant's country.
- Billing rail: **Stripe** (recurring monthly subscription + QR subscribe link). Not Square.

## Tax (Canada)

GST/HST applies on top of subscription price (it's a digital service). Province-dependent:

| Province | Rate on subscription |
|----------|---------------------|
| BC | 5% GST + 7% PST |
| Alberta | 5% GST |
| Ontario | 13% HST |
| Quebec | 5% GST + 9.975% QST |
| Manitoba | 5% GST + 7% PST |

If asked: "Sales tax is applied automatically based on your province at billing — same as any software subscription."

Don't get into tax debates during the sale. Move on.

## Your commission

**70% of monthly subscription revenue, recurring for the lifetime of the account.**

Pricing is custom per deal, so your exact cut depends on the price you set. Illustrative examples:

| If deal price is… | Your monthly cut | Annual (if retained 12mo) |
|-------------------|-----------------|---------------------------|
| CA$350/mo | CA$245 | CA$2,940 |
| CA$600/mo | CA$420 | CA$5,040 |
| CA$1,200/mo | CA$840 | CA$10,080 |
| $350/mo (US) | $245 | $2,940 |
| $600/mo (US) | $420 | $5,040 |
| $1,200/mo (US) | $840 | $10,080 |

Commission paid every month the account stays active. Churn = lost commission. **Retention is your real job after the close.**

## Upsell paths

| From | To | Trigger | Your uplift |
|------|----|---------|-------------|
| Standard | Premium | Merchant has cameras, asks about foot traffic | depends on custom price delta |
| Premium | Command | Opens a 2nd location | depends on custom price delta |
| Single | Multi | Franchise/multi-unit owner | Often jumps straight to Command |

Natural upsell window: **month 2–3**, after they've seen value from Standard. Don't pitch Premium on day one unless cameras came up in discovery.

## When merchants ask "why is this expensive?"

Never apologize for price. Reframe to ROI:

> "If I show you CA$3,000/mo in revenue you're currently missing, is our monthly fee to capture that worth it? That's what our AI typically finds in week one."

If they push harder, see `50-cheatsheets/objection-handlers.md`.

## What's NOT included in any plan

- Phone agent (separate product — **flat CA$1.50 per phone order**, no percentage of sales; ask if interested, route to product team)
- Custom integration buildouts (Command tier API access lets the merchant build their own; we don't custom-build for one merchant)
- Hardware (cameras, edge devices) — merchant supplies their own; we recommend specific PoE models in `20-camera-integrations/`

---

_Last updated: 2026-05-31_
_Sourced from: docs/playbook/_status/phase-2-decisions.md + services/training_video_pipeline/lesson_content.json (lessons 1.3, 8.1, 8.3) + Phase 3 task spec_
