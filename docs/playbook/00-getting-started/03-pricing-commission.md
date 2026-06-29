# Pricing & Commission

## Pricing model — custom per-deal

Meridian uses **custom per-deal pricing**. You set a monthly price for each merchant when generating a proposal in the portal. There are no published tiers or fixed price points. Do NOT quote specific monthly prices before discovery.

When a prospect asks "how much?" — lead with value:
> "We do custom pricing based on what we find. Most merchants see CA$2,800+/mo in found revenue in week one — let me show you that first, then the price question answers itself."

**One product, one feature set.** Every merchant gets the full POS analytics agent fleet. Cameras, multi-location, and API access are line-item add-ons — priced separately, not plan-gated.

### Base product — POS analytics

All merchants get:
- Month-to-month, no contract
- No setup fee
- 18-month historical backfill
- All 30 POS analytics agents (revenue forecasting, peak hours, customer LTV, inventory intelligence, etc.)
- Email digest + in-app alerts
- One-click cancel
- Standard support (24-hr first response)

### Add-ons (line items on the proposal, not plan tiers)

| Add-on | What it unlocks | When to propose |
|--------|----------------|-----------------|
| **Camera intelligence** | Foot traffic counts, queue length, dwell time, zone heatmaps + all 10 cross-reference agents (POS × camera fusion) | Merchant already has cameras, or opens a location where cameras would help |
| **Multi-location** | Multi-store rollups, location analyst, cross-store comparison | 2+ locations or plans to expand |
| **API access + custom models + dedicated account manager** | Developer API, custom AI tuning, dedicated AM | Larger operator, franchise, or technical buyer |
| **Priority support** | 4-hr first response, 24-hr resolution | Merchant explicitly wants faster support SLA |

Quote each add-on as a separate line when building the proposal. All add-on pricing is custom — schedule a call with the product team if the merchant asks for numbers before you've done discovery.

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

## Add-on upsell triggers

| Signal from merchant | Add-on to propose | Your uplift |
|---------------------|------------------|-------------|
| Merchant has cameras, asks about foot traffic | Camera intelligence add-on | depends on custom price delta |
| Opens a 2nd location | Multi-location add-on | depends on custom price delta |
| Franchise / multi-unit owner | Multi-location add-on; often camera too | Often a significantly larger deal |
| Technical buyer asks about API | API access add-on | depends on custom price delta |

Natural upsell window: **month 2–3**, after they've seen value from the base product. Don't pitch camera intelligence on day one unless cameras came up in discovery.

## When merchants ask "why is this expensive?"

Never apologize for price. Reframe to ROI:

> "If I show you CA$3,000/mo in revenue you're currently missing, is our monthly fee to capture that worth it? That's what our AI typically finds in week one."

If they push harder, see `50-cheatsheets/objection-handlers.md`.

## What's NOT included in the base product

- Phone agent (separate product — **flat CA$1.50 per phone order**, no percentage of sales; ask if interested, route to product team)
- Custom integration buildouts (API access add-on lets the merchant build their own; we don't custom-build for one merchant)
- Hardware (cameras, edge devices) — merchant supplies their own; we recommend specific PoE models in `20-camera-integrations/`

---

_Last updated: 2026-06-29_
_Sourced from: docs/playbook/_status/phase-2-decisions.md + services/training_video_pipeline/lesson_content.json (lessons 1.3, 8.1, 8.3) + Phase 3 task spec_
