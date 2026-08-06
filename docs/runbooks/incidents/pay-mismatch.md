# SEV-1 — Payment mismatch / billing drift

Fires as: "Phone order underpayment — billing drift" (settlement check, single
order) or "Meridian Billing Monitor: N underpaid phone order(s)" (6-h sweep
digest). Meaning: a customer settled BELOW the total the agent confirmed —
the merchant is being shorted. This class already happened once (2026-08-06:
itemized checkouts dropped tax + topping lines, ~13%+/order).

## First 5 minutes

1. **Stop the bleeding — decide if the rail stays up.** The alert names the
   account (platform/phone) and rail. Options, least to most disruptive:
   - Phone-account split at fault → unset `STRIPE_PHONE_SECRET_KEY` on Railway
     (reverts all phone checkouts to the platform account on next boot).
   - A recent merge at fault → Railway dashboard → redeploy previous SUCCESS.
   - Rail-specific (Square link / Clover HCO) → flip that merchant's
     `payment_link_provider` back to `stripe` (the Stripe rail carries the
     charge-time invariant and cannot underbill).
2. Confirm the invariant layers are actually running (if these are silent the
   alert you got may be the only one):
   `railway logs ... | grep -i "billing monitor started"` and check
   `BILLING INVARIANT VIOLATION` / `UNDERPAYMENT DETECTED` lines around the
   incident window.

## Quantify (before any fix lands)

Every affected order, from Stripe truth (run per account key):

```bash
# completed sessions last 7d with metadata → compare to phone_orders totals
curl -s -u "$STRIPE_KEY:" "https://api.stripe.com/v1/checkout/sessions?limit=100&status=complete&created[gte]=$(date -d '7 days ago' +%s)" \
 | python3 -c "import json,sys; [print(s['id'],(s.get('metadata') or {}).get('pos_order_id'),s['amount_total'],s['currency']) for s in json.load(sys.stdin)['data']]"
```

Cross-check each `pos_order_id` against `phone_orders.total` (Supabase, read-only).
Output: a table of (merchant, order, confirmed¢, paid¢, shortfall¢). This table
IS the make-good ledger and the postmortem evidence — save it.

## Make-good (merchant trust is the product)

- Shortfall was OUR builder bug → Meridian covers it. Per merchant: total the
  shortfall, credit it against Meridian fees (voice_ledger credit) or transfer
  the difference; tell the merchant proactively BEFORE they find it in their
  own reconciliation. Draft for Aidan to send — never silent.
- A customer was OVERcharged (has not happened; invariant makes it hard) →
  refund the delta immediately via Stripe, then the same proactive note.

## Fix + verify

1. Root-cause in the rail builder; fix with a test that encodes the missing
   case; extend `tests/compliance/test_billing_parity_control.py`'s ORDER_MATRIX
   if the drift came from an order shape the matrix lacks.
2. Live-verify like the 2026-08-06 session: create a real Checkout session for
   the failing shape with the real key, assert `amount_total` == confirmed
   total, then EXPIRE the session (`POST /v1/checkout/sessions/{id}/expire`).
   Never leave verify sessions open; never pay them.
3. Watch the next billing-monitor sweep come back clean (or trigger scrutiny
   early by restarting the service — the monitor sweeps at boot).

## Close-out

Postmortem to memory: which layer caught it (charge-time / settlement /
monitor), how long from first bad charge to alert, make-good amounts + dates.
If detection took longer than one sweep interval, tighten
`MERIDIAN_BILLING_MONITOR_INTERVAL`.
