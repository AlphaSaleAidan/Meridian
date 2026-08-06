# Meridian Situation Response Protocols

One page per event class. Every automated alert email names its protocol file —
open it and run the steps top to bottom. Written to be executable by a human OR
pasted to a Claude session ("run the <name> protocol").

| Protocol | Fires when | Severity |
|---|---|---|
| [server-down.md](server-down.md) | Edge-watchdog DOWN email; portals unreachable; API 5xx | SEV-1 |
| [pay-mismatch.md](pay-mismatch.md) | "underpayment / billing drift" alert (settlement check or billing monitor) | SEV-1 |
| [payments-unconfirmed.md](payments-unconfirmed.md) | Customers pay but orders stay `awaiting_payment` (no receipt, no kitchen ticket) | SEV-1 |
| [phone-fleet-down.md](phone-fleet-down.md) | Demo/merchant lines dead air, calls failing, Vapi errors | SEV-1 |
| [vendor-billing.md](vendor-billing.md) | Vapi credits / Telnyx balance / Stripe account restrictions | SEV-2 (SEV-1 if calls already failing) |

## Severity ladder

- **SEV-1 — money or availability actively broken.** Real customers/merchants
  affected right now. Drop everything; mitigate first, root-cause second.
- **SEV-2 — degradation or imminent breakage.** Nothing lost yet (e.g. vendor
  credit low, one rail degraded with a working fallback). Respond same day.
- **SEV-3 — signal only.** Monitor finding with no customer impact. Fold into
  normal work; never silence the monitor instead of fixing the cause.

## Universal first three steps (every incident)

1. **Scope it**: which surface, which merchants, since when. The fastest scope
   checks are in each protocol's "First 5 minutes".
2. **Mitigate before diagnosing**: every protocol has a rollback/fallback that
   restores service without understanding the bug (env unset, redeploy previous,
   re-point). Take it early — the broken state can be studied later from logs.
3. **Log the timeline as you go** (one line per action, with times). It becomes
   the postmortem and, when merchants were shorted, the make-good ledger.

## Escalation

- Operator on point: Aidan (aidanpierce72@gmail.com — all automated alerts go
  here; override with `MERIDIAN_OPS_ALERT_EMAIL` on Railway).
- Anything involving merchant money (mismatch, unconfirmed payments) also gets a
  **merchant make-good decision** before the incident closes — see
  [pay-mismatch.md §Make-good](pay-mismatch.md).

## Standing defenses (what's already automated)

- **Edge watchdog** (`src/services/edge_watchdog.py`, env-gated): probes the
  Contabo-hosted portals from Railway; one email per DOWN transition + recovery.
- **Billing invariant** (charge time): Stripe sessions can only bill the
  confirmed order total — drifted line items collapse to one exact line.
- **Settlement check** (`mark_order_paid`): underpayment → CRITICAL log + email.
- **Billing monitor** (`src/services/billing_monitor.py`, ON by default): 6-h
  sweeps of completed Stripe sessions on BOTH account keys vs `phone_orders`
  totals; digest email on any shortfall.
- **CI parity ratchet** (`tests/compliance/test_billing_parity_control.py`):
  billed==confirmed across every rail, red before merge.

## After every SEV-1

Within 24h, write the postmortem into the memory system (what fired, what was
the gap, what changed) and add/extend a regression test or monitor so the same
class can't recur silently. "The alert worked" is not a close-out; the class
being impossible is.
