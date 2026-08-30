# Stripe

> Status: **LIVE**
> Category: payments-led / multi-vertical (any merchant running payments on Stripe)
> Auth: Stripe App OAuth (the merchant installs the Meridian app into their own Stripe account)

## What Stripe connect is — and is not

Stripe is a **payment processor, not a full POS**. A Stripe charge carries the
total, the refund state, the payment method, and the timestamp — **no line
items, no menu, no employee attribution, no customer records**. So a Stripe
connection powers Meridian's **revenue-level analytics only**. Set this
expectation up front; it is the single most important thing to get right in
the pitch.

Sell Stripe connect when the merchant runs their payments on Stripe (Stripe
Terminal counter setups, Stripe-based ordering stacks) or when they have no
supported POS — it is the fastest on-ramp to real numbers. If they later move
to Square or Clover, the full connect unlocks the rest.

## What you tell the merchant

"You already run your payments through Stripe. Connect it once — you'll log
into your own Stripe account and approve read-only access — and Meridian
imports eighteen months of your revenue history. You get your real revenue
trends, your true peak hours, and seasonality from day one. It reads your
charge history; it can't touch your money or your Stripe settings."

## How the merchant connects

1. From the Meridian portal, **Settings → POS Connections → Connect Stripe**
2. A Stripe tab opens; they sign into **their own** Stripe account (never yours, never Meridian's)
3. They approve the Meridian app install (read-only charge access — the app declares `charge_read`)
4. Stripe redirects back; the historical backfill of their charge history starts automatically
5. Connection status shows on Settings → POS Connections

Typical time to connect: **about 2 minutes**. Backfill window: **18 months of
charges**. Access tokens live one hour and refresh automatically on a rolling
one-year refresh token — the merchant does not re-log-in.

## What data we pull

| Data | What it carries | Backfill |
|------|-----------------|----------|
| Charges | total, created time, payment-method type, card brand/last-4 where Stripe provides it | 18 months |
| Refunds | full refunds map to voided sales; partial refund amounts are tracked | 18 months |

That's the complete list — Stripe has no catalog, team, or customer objects to
pull for a merchant's in-store business.

## What features they get

Everything that runs on transaction totals:

- Revenue trend + forecasting
- Peak hours (from charge timestamps)
- Day-of-week + seasonality
- Payment-mix view (card vs other payment-method types)

## What features they DON'T get

Be straight about this — it's the difference between a happy account and a
refund conversation:

- **No product-level anything**: no product velocity, basket analysis, menu
  pricing, or per-item margins (charges have no line items)
- **No employee performance** (no team data)
- **No customer LTV / churn** (no customer records)
- **No phone-order injection** — the AI phone agent drops finished orders into
  Square or Clover; a Stripe connection cannot receive orders
- Camera intelligence still works (it's POS-independent), and walk-in
  conversion can cross-reference charge counts

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Install page 404s or "app not found" | The app is distributed through a channel install link until Stripe marketplace review completes (`STRIPE_POS_AUTHORIZE_URL` on the backend must point at it) | Escalate — this is a backend config item, not a merchant problem |
| Merchant approved but no data appears | Backfill still running, or the charge history is thin | Check Settings → POS Connections status; a low-volume merchant's backfill finishes fast and dashboards just look sparse |
| Disconnected after weeks | Refresh failed or the merchant uninstalled the app from their Stripe dashboard | One-click reconnect — same flow as first connect |
| Merchant connected the wrong account | They were signed into a different Stripe account in the browser | Have them sign out of Stripe, reconnect, and sign into the business account |

## Sales angle

**Opener:** "You're already sitting on eighteen months of revenue history in
Stripe. Two minutes of connecting and Meridian turns it into your real peaks,
trends, and seasonality — without touching your payment setup."

**Why Stripe matters:** it catches merchants no POS integration reaches —
Stripe Terminal counters, custom ordering stacks, service businesses. Zero
hardware talk, zero "will this break my register" objection: it's a read-only
app install on an account they already have.

**The honest upsell:** "This gets you the revenue picture. When you want
per-product margins, basket analysis, or the phone agent dropping orders
straight into a register, that's what the Square and Clover connections add."

## Never say

- That Meridian is a payment processor or can move/settle money — the app is read-only charge access
- That Stripe connect provides menu, product, staff, or customer insights — it cannot
- Anything about the merchant's Stripe fees or rates — that's between them and Stripe

## What blocks live status today

Nothing — the app is uploaded to the Meridian Integrations Stripe account, the
install round-trip is validated, and the 18-month backfill engine is in
production (`src/stripe_pos/`). Marketplace listing review is in progress;
until it completes, installs run through Stripe's channel install link (a
backend config detail, invisible to the merchant flow).

## Reference docs

- Stripe Apps OAuth: https://docs.stripe.com/stripe-apps/api-authentication/oauth
- App manifest / permissions: `stripe-app/stripe-app.json` in this repo

---

_Last updated: 2026-08-13_
_Sourced from: src/pos_connect/registry.py (stripe config) + src/stripe_pos/ (client, sync_engine, mappers, tokens) + src/api/routes/pos_connect.py_
