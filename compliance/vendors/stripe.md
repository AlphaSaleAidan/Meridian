# Vendor: Stripe
**Document ID:** VEN-005
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Payment processing platform for Meridian's subscription billing and marketplace payments. Meridian uses **Stripe Connect** (destination charges model) to collect platform fees and route payments to connected merchant accounts. Not in Meridian's prior 7-vendor list — **this is a gap now resolved by registration here.**

**Integration paths:** `src/api/routes/stripe_checkout.py`, `src/api/routes/stripe_webhooks.py`, `src/api/routes/stripe_connect.py` (or equivalent per the unified payments PR #155)

**Platform model:** Destination charges with 1.9% platform fee. Stripe Connect (US Stripe account with CAD via FX).

---

## Data Touched

| Data category | Details |
|---|---|
| Payment intents | Amount, currency, status, customer reference — created per subscription or marketplace transaction |
| Subscription data | Plan tier, billing cycle, status for Meridian platform subscriptions |
| Stripe Connect merchant tokens | Connected merchant account IDs (`acct_xxx`), used for destination charge routing |
| Webhook signing secrets | `STRIPE_WEBHOOK_SECRET` stored in Railway env vars and `/root/.secrets/`; used to verify Stripe webhook authenticity |
| Platform fee data | Fee amounts deducted per transaction; auditable in Stripe dashboard |

**What Meridian does NOT store:** Raw card numbers, CVV, bank account numbers. Meridian never handles raw payment method data — all card capture is handled by Stripe.js / Stripe Elements on the client side, then tokenized. Meridian stores only Stripe payment intent IDs and subscription IDs.

---

## Attestation Status

| Attestation | Status | Source |
|---|---|---|
| PCI DSS Level 1 | Stripe is a PCI DSS Level 1 Service Provider (highest certification level) | stripe.com/docs/security |
| SOC 2 Type II | Stripe holds SOC 2 Type II | stripe.com/docs/security |
| ISO 27001 | Verify at Stripe's security page | stripe.com/docs/security |

**Because Meridian uses Stripe.js and never handles raw card data, Meridian's PCI scope is reduced to SAQ A (the most favorable category).** This relies entirely on Stripe being the cardholder data environment.

**Annual evidence action:** Download Stripe's Compliance Overview or Request Stripe SOC 2 report → `compliance/evidence/POL-008/vendor-attestations/stripe-soc2-<year>.pdf`.

---

## DPA Status

Stripe provides a Data Processing Addendum included in the Stripe Master Services Agreement (accepted when creating a Stripe account). Review terms at stripe.com/privacy for GDPR / PIPEDA coverage.

**Action required:** Confirm that Stripe's DPA covers Canadian merchant data (PIPEDA) and any EU customer data that may flow through Meridian's system. Record in `compliance/evidence/POL-008/vendor-attestations/stripe-dpa-status.md`.

---

## What Breaks if Stripe Fails

**Impact: HIGH (revenue collection stops)**

- All new subscription charges fail — no new revenue collected.
- Stripe Connect marketplace payments fail — merchant payouts stop.
- Webhook-driven subscription status updates stop — subscription tier changes and cancellations are delayed.
- Existing active subscriptions are unaffected until their next renewal attempt.
- POS-side Square/Clover integrations are unaffected (separate payment flows).

**Recovery:** Stripe SLA and status at status.stripe.com. Meridian has no payment processor fallback. Revenue impact begins immediately.

---

## Specific Risks & Controls

| Risk | Control | Status |
|---|---|---|
| Stripe webhook spoofing | Webhook signature verification using `STRIPE_WEBHOOK_SECRET` (HMAC-SHA256) on all incoming webhook events | Enforced — verify in `stripe_webhooks.py` |
| Stripe secret key (`sk_live_*`) exposed in code | gitleaks on all PRs; key stored only in Railway env vars and `/root/.secrets/` | Enforced |
| Stripe Connect token used for unauthorized charge | Destination charge model limits what Meridian can do with connected account IDs (Stripe enforces charge scope) | Architecture control |
| Stripe account takeover | Stripe account secured by Aidan Pierce's email + 2FA (verify: hardware key recommended) | Partial — verify 2FA method |

---

## Review Date

TBD — next annual review cycle. Next attestation check: January 2027. Rotate `STRIPE_WEBHOOK_SECRET` and confirm `sk_live_*` is not shared across environments.
