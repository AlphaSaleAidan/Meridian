# Pricing & Commission

## Pricing model — three published tiers

Meridian sells on **three published plan tiers**. Quote from this table — do not invent prices, and do not discount below tier price without written approval. The per-order fee is **fixed per tier** (the old rep fee slider is retired).

### US portal (USD)

| Tier | Monthly | Per-order fee |
|------|---------|---------------|
| Standard | $250/mo | $0/order |
| Premium | $350/mo | $0.65/order |
| Command | $500/mo | $0.45/order |

### Canada portal (CAD)

| Tier | Monthly | Per-order fee |
|------|---------|---------------|
| Standard | CA$350/mo | CA$0/order |
| Premium | CA$500/mo | CA$0.75/order |
| Command | CA$700/mo | CA$0.60/order |

### Minutes licensing (zero-per-order) alternative

For merchants who won't accept a per-order fee, Premium and Command can be closed as a **$0/order minutes plan** at the same tier monthly:

- **Premium** — 600 included agent-call minutes/month
- **Command** — 1,000 included agent-call minutes/month
- Overage: **$0.20/min** past the bucket (both markets), 5-minute per-call cap

The merchant's monthly price does not change between the two models — it's per-order fee vs included-minutes bucket.

## Currency rules

- Canadian merchants → always quote CAD (`CA$`). US merchants → USD. Never mix; billing follows the merchant's country.
- Phone-agent billing runs in CAD internally on both markets — you still QUOTE the table above in the merchant's currency.

## Tax (Canada)

GST/HST applies on top of subscription price (digital service). Province-dependent — "sales tax is applied automatically based on your province at billing." Don't get into tax debates during the sale.

## Your commission — milestone schedule (the One-Pager)

Commission is a **package-based milestone schedule**, not a percentage of revenue. Each closed account pays four fixed lump-sum milestones as the account stays active. You are an independent contractor; payouts are lump-sum and outcome-based.

Milestones split each package's total in fixed weights (13 / 28 / 10 / 6 of 57 units):

| Milestone | Earned when | Weight |
|-----------|------------|--------|
| **M0** | At close, once the merchant's first payment clears. Paid the Friday at least 7 days after close. | 13 units |
| **M1** | Account still active at month 4 | 28 units |
| **M2** | Account still active at month 9 | 10 units |
| **M3** | Account still active at month 12 | 6 units |

Package schedule (CAD):

| Package (list monthly) | Unit value | M0 | M1 | M2 | M3 | Total |
|------------------------|-----------|-----|-----|-----|-----|-------|
| CA$200/mo (minimum) | CA$6.00 | CA$78 | CA$168 | CA$60 | CA$36 | **CA$342** |
| CA$250/mo (starter) | CA$7.50 | CA$97.50 | CA$210 | CA$75 | CA$45 | **CA$427.50** |
| CA$399/mo (middle) | CA$13.75 | CA$178.75 | CA$385 | CA$137.50 | CA$82.50 | **CA$783.75** |
| CA$689/mo (higher) | CA$20.00 | CA$260 | CA$560 | CA$200 | CA$120 | **CA$1,140** |

Deals map to the nearest package by closed monthly price.

Adjustments (applied to M0 only):

- **Upsell** (closed above list): M0 increases by 50% of the difference.
- **Discount** (closed below list): M0 decreases by 100% of the difference (M0 never goes below $0).

**Cancellation stops all future milestones immediately.** M1 is the largest milestone — an account that churns before month 4 pays you M0 only. **Retention is your real job after the close.**

### Market status

- **Canada: LIVE.** Milestones accrue automatically when your deal closes in the portal.
- **US: schedule not yet ratified.** The payout path is built and switches on the moment US comp terms are signed off — until then, do not represent specific US commission amounts. Ask your region lead / admin for current status before quoting your own comp on US deals.

## When merchants ask "why is this expensive?"

Never apologize for price. Reframe to ROI:

> "If I show you CA$3,000/mo in revenue you're currently missing, is our monthly fee to capture that worth it?"

If they push harder, see `50-cheatsheets/objection-handlers.md`.

---

_Last updated: 2026-08-12_
_Sourced from: src/billing/fee_terms.py (CANONICAL_FEE_TERMS + zero-per-order buckets) and src/services/commission_engine.py (One-Pager milestone schedule, migration 046)._
