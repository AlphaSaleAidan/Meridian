# Troubleshooting Decision Tree

Start here when you don't know where to start.

```
START
  │
  ├─ Does the merchant have an account in the portal?
  │   ├─ No  → it's a sales/onboarding issue, not a support issue. Check intake form, payment confirmation.
  │   └─ Yes → continue.
  │
  ├─ Is the POS connection green/active?
  │   ├─ No  → [pos-connection-failures.md]
  │   ├─ "It was, now it isn't" → token expiry (esp. Clover). Reconnect from portal.
  │   └─ Yes → continue.
  │
  ├─ Is data flowing (look at "Last sync" timestamp in Settings → POS Connections)?
  │   ├─ Last sync > 2 hours ago, no error → engineering escalation (worker stuck?)
  │   ├─ Last sync > 2 hours ago, error visible → fix the error, see [pos-connection-failures.md]
  │   └─ Last sync recent → continue.
  │
  ├─ Is backfill complete?
  │   ├─ No, in progress → [backfill-stuck.md] for expectations
  │   ├─ Stuck > 2 hours at same % → engineering
  │   └─ Yes → continue.
  │
  ├─ Are insights appearing?
  │   ├─ No  → [insights-not-appearing.md]
  │   ├─ Some, but specific one missing → [insights-not-appearing.md] (per-agent requirements)
  │   └─ Yes but they look wrong → [data-mismatch.md] or [insights-not-appearing.md]
  │
  ├─ Camera issue?
  │   └─ [camera-offline.md]
  │
  ├─ Money/billing issue?
  │   └─ [billing-issues.md]  (treat as High severity by default)
  │
  └─ None of the above → open a ticket, route to CS Manager.
```

## Severity quick-decide

Use this when you're triaging:

| Symptom | Severity |
|---------|----------|
| Login impossible / dashboard down | **Critical** — 1hr response, 4hr resolution |
| Wrong data / agent errors after good data | **High** — 4hr response, 24hr resolution |
| Wrong charge / billing issue | **High** by default |
| Customer says "I'm cancelling" | **Critical** — escalate, save the account if possible |
| "Insight is missing" but they were connected yesterday | High (likely connection) |
| "Insight is missing" and they connected 6 hours ago | Medium (likely needs more data) |
| "Camera offline" — first occurrence | Medium |
| "Camera offline" — recurring or all-cameras | High (network/IT issue at merchant — may need to escalate to their IT) |
| "I don't understand this insight" | Low — education ticket, not a bug |

## When to escalate (vs. handle yourself)

| You handle | Escalate |
|------------|----------|
| Connection reconnect | Worker stuck > 2hr |
| Date range filter / dashboard navigation | Specific transactions missing despite live sync |
| Explaining an insight | Money Left on Table looks wildly wrong |
| Small refund (< CA$50) | Refund > CA$50 |
| Email walk-through | Customer threatens cancel during call |
| Setting/timezone fix | Multi-day issue affecting multiple merchants |

## What to capture in every ticket

Every ticket, even the easy ones, needs:

1. **Merchant business name + business_id**
2. **POS connected** (which one, since when)
3. **Symptom in their words** (quote them)
4. **What you've tried** (so the next person doesn't repeat)
5. **Severity** (per the table above)
6. **Next action + deadline**

This is non-negotiable. Tickets without these get bounced back.

## Don't do these

- Don't tell a merchant "that's a known bug" without offering a workaround. Workaround first, then mention the bug.
- Don't promise a fix timeline you don't control ("engineering will fix this tomorrow") — they won't, and you'll burn trust.
- Don't try to debug a Critical issue alone for > 30 min — escalate.
- Don't refund without checking the cause first. Sometimes refunds mask a real bug we need to find.
- Don't tell a merchant "everyone has this problem" — even if true, it makes them feel like they don't matter.

---

_Last updated: 2026-05-31_
_Sourced from: docs/customer-sop.md (escalation paths + SLAs) + src/errors.py + the symptom catalog across this directory_
