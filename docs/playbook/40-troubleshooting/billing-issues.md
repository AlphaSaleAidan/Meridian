# Billing Issues

Money problems get heat. Treat all billing tickets as **High severity** by default.

## Symptom: "I'm in Canada but I was charged USD"

This is a real bug we've fixed before (Stripe billing country wasn't set correctly at subscription creation).

| Cause | Fix |
|-------|-----|
| Account country wasn't set when subscription created | Update country in Settings → Account, then we re-issue the Stripe invoice in CAD |
| Old account from before the fix | Manual re-issue via Stripe; CS Manager handles |

**What to say:** "That was a known bug — fully fixed now. I'll refund the USD charge today and re-issue in CAD via Stripe. New invoice goes out within 1 business day."

## Symptom: "I cancelled and was still charged"

| Cause | Fix |
|-------|-----|
| Cancellation took effect after billing date (we bill monthly on signup anniversary) | Confirm cancel date vs billing date; pro-rate refund if cancel was before |
| Cancellation didn't actually save | Check Settings → Subscription; if still active, cancel now + refund |
| Two-step cancellation not completed | Some flows require a confirmation email click — check if they did |

**What to say:** "Let me check the timestamps. Cancellation is supposed to take effect immediately and pro-rate. If we billed after your cancel timestamp, that's a refund." Issue the refund within 24 hours, no debate.

## Symptom: "My invoice doesn't match what I was quoted"

| Cause | Fix |
|-------|-----|
| Quoted USD, billed CAD (or vice versa) | Confirm what you (the rep) said in the close. If you quoted CA$343 and they got billed USD $299, that's actually a savings — explain. If reversed, manual adjust. |
| Tax wasn't disclosed | GST/HST adds 5–15% depending on province; this is automatic — confirm with merchant |
| Upgrade applied mid-cycle | Pro-rated; explain the math |
| Quoted Standard, billed Premium | Plan upgrade got triggered somewhere; check Settings → Subscription history |

**What to say:** "Let me walk through the math line by line." Be patient. Most billing disputes resolve when you show them the breakdown.

## Symptom: "Why is GST/HST showing? You didn't tell me about tax"

Subscription is a digital service → GST/HST applies. By province:

| Province | Rate |
|----------|------|
| BC | 5% GST + 7% PST |
| Alberta | 5% GST only |
| Ontario | 13% HST |
| Quebec | 5% GST + 9.975% QST |
| Manitoba | 5% GST + 7% PST |
| Saskatchewan | 5% GST + 6% PST |
| Atlantic provinces (NB/NS/NL/PE) | 15% HST |

**What to say:** "Sales tax is applied automatically based on your province — same as any software subscription. The pre-tax amount is what was quoted; tax is on top, set by [their province] at [rate]." Don't apologize; this is standard.

## Symptom: "I want to downgrade / change plans"

| Action | Effective when |
|--------|---------------|
| Downgrade (Premium → Standard) | Next billing cycle (we don't pro-rate downgrades) |
| Upgrade (Standard → Premium or Command) | Immediate, pro-rated on next invoice |
| Pause | Not currently offered; cancel + restart later |

**Rep alert:** if a merchant wants to downgrade, **find out why first**. Often it's a feature they didn't realize they had (cameras, multi-location), or a single bad experience. Retention saves your commission.

## Symptom: "Charged a setup fee I didn't agree to"

We don't charge setup fees. If this is appearing, it's a bug. Refund immediately, escalate to engineering.

## Symptom: "Charged for cameras but I'm on Standard"

| Cause | Fix |
|-------|-----|
| Standard accidentally upgraded to Premium | Check subscription history; refund + reset |
| Camera was added during trial and converted at billing | We don't offer trials currently; if this appears, it's a bug |

## Refund authority

| Amount | Who can approve |
|--------|----------------|
| < CA$50 | You (rep) |
| CA$50–CA$500 | CS Manager |
| > CA$500 | CS Director |

Issue small refunds immediately; don't let billing disputes fester. They're churn risk.

## Cancellation flow

When a merchant says they want to cancel, follow:

1. **Acknowledge** ("Sorry to hear that — let me make sure I get this right")
2. **Find the real reason** ("What pushed you to this decision today?")
3. **Address the real issue** (often it's not price — could be onboarding, a feature gap, a support issue)
4. **If they still want to cancel**, process it. Don't argue. Bad cancellations turn into bad reviews.
5. **Schedule a 90-day check-in** ("If anything changes, you know how to reach me — I'll text you in 90 days to see how things are going")
6. **Update the lead in portal** as Closed Lost with notes

## Why this matters for your commission

Cancellations kill recurring commission. At 70% recurring, every month a merchant stays active earns you money. **Retention is your real job** after the close.

Most cancellations within the first 90 days trace back to:
1. Wrong fit (POS wasn't actually supported live)
2. No first-week value (insights didn't land or weren't reviewed)
3. Promised features that don't exist

Avoid all three at the close → retention takes care of itself.

---

_Last updated: 2026-05-31_
_Sourced from: docs/customer-sop.md (sections 4 Support, 6 Role-Based Access, 7 Email Sequence) + docs/playbook/00-getting-started/03-pricing-commission.md + recent fix commit 389f567 (CAD billing fix) + general billing operations_

_[NEEDS AIDAN INPUT] — Confirm refund authority limits per rep tier. Currently using placeholder thresholds (<$50 rep, $50–$500 CS Manager, >$500 CS Director). Adjust if actual policy differs._
