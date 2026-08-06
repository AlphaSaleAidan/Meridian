# SEV-2 — Vendor billing / credit alerts

(SEV-1 the moment it causes calls or payments to actually fail — then also run
the matching outage protocol.)

Three vendors gate live service. Each fails in a way that looks like a bug.

## §Vapi — voice credits
- **Symptom:** whole phone fleet stops; assistant-request still returns 200 but
  calls don't connect. Balance is NOT readable via REST — must check
  `dashboard.vapi.ai` → billing (org: Meridian fleet
  `33e99406-207d-41de-ac02-b1a1d9ffe073`, NOT the ResearchChem org).
- **Fix:** card on file + auto-reload ON. Aidan-only (payment method).
- **Prevent:** auto-reload is the guard; if it's ever off, that's the SEV-2.

## §Telnyx — carrier balance + messaging
- **Symptom (voice):** inbound stops routing / number orders fail. Keep the
  account funded (was ~$4.55 historically — thin).
- **Symptom (SMS):** pay-link/receipt texts stuck `queued`. US→US needs 10DLC
  on the from-number (`+16185240389` has none); US→CA delivers. Canadian
  from-number selection exists (`TELNYX_PHONE_NUMBER_CA`) — set it so CA
  customers always get texts. Full US fix = 10DLC brand+campaign (EIN needed)
  or a toll-free verified number.
- **Check balance:** Telnyx portal → Billing.

## §Stripe — account restrictions / payouts
- **Symptom:** charges succeed but payouts pause, or "account needs attention"
  — Stripe wants more verification (common on a newly-activated account like the
  phone-order acct `acct_1U1ViDQ3LQbieqJG`).
- **Fix:** Dashboard → the flagged requirement; Aidan completes verification.
- **Note the phone-account payout trade-off:** existing merchants' Connect
  accounts belong to the OLD platform, so on the phone account their share is a
  direct charge and payout is MANUAL until re-onboarded
  (`STRIPE_PHONE_ONBOARDING=1`). Not an incident — a known state; track which
  merchants are affected.

## General
- All three have a dashboard as the source of truth; API balance reads are
  unreliable (Vapi especially). When a "system is broken" report has no code
  cause, **check vendor balances before deep-diving code** — it's the fastest
  ruled-out class.
- Keys live in `/root/.secrets/` (vapi.env, telnyx.env, stripe.env,
  meridian-phone-stripe.env). Never paste values into chats or the timeline.
