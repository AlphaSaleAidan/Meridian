# Pricing & Commission

## The three plans

| Plan | USD/mo | CAD/mo | Locations | Cameras | Multi-location | API access |
|------|--------|--------|-----------|---------|----------------|------------|
| **Standard** | $299 | CA$343 | 1 | — | — | — |
| **Premium** | $599 | CA$685 | 1 | Yes | — | — |
| **Command** | $1,199 | CA$1,370 | Unlimited | Yes | Yes | Yes |

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

| Plan | MRR | Your monthly cut | Annual (if retained 12mo) |
|------|-----|-----------------|---------------------------|
| Standard CA | CA$343 | CA$240 | CA$2,880 |
| Premium CA | CA$685 | CA$480 | CA$5,760 |
| Command CA | CA$1,370 | CA$959 | CA$11,508 |
| Standard US | $299 | $209 | $2,508 |
| Premium US | $599 | $419 | $5,028 |
| Command US | $1,199 | $839 | $10,068 |

Commission paid every month the account stays active. Churn = lost commission. **Retention is your real job after the close.**

## Upsell paths

| From | To | Trigger | Your uplift |
|------|----|---------|-------------|
| Standard | Premium | Merchant has cameras, asks about foot traffic | +CA$239/mo recurring |
| Premium | Command | Opens a 2nd location | +CA$479/mo recurring |
| Single | Multi | Franchise/multi-unit owner | Often jumps straight to Command |

Natural upsell window: **month 2–3**, after they've seen value from Standard. Don't pitch Premium on day one unless cameras came up in discovery.

## When merchants ask "why is this expensive?"

Never apologize for price. Reframe to ROI:

> "If I show you CA$3,000/mo in revenue you're currently missing, is CA$343 to capture it worth it? That's what our AI typically finds in week one."

If they push harder, see `50-cheatsheets/objection-handlers.md`.

## What's NOT included in any plan

- Phone agent (separate product, separate pricing — ask if interested, route to product team)
- Custom integration buildouts (Command tier API access lets the merchant build their own; we don't custom-build for one merchant)
- Hardware (cameras, edge devices) — merchant supplies their own; we recommend specific PoE models in `20-camera-integrations/`

---

_Last updated: 2026-05-31_
_Sourced from: docs/playbook/_status/phase-2-decisions.md + services/training_video_pipeline/lesson_content.json (lessons 1.3, 8.1, 8.3) + Phase 3 task spec_
