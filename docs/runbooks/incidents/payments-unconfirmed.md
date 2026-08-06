# SEV-1 — Payments made but orders unconfirmed

Symptom: customers pay the link, money reaches Stripe, but orders sit in
`awaiting_payment` — no receipt SMS, no kitchen ticket, merchant sees nothing.
Cause is almost always the **webhook leg**: Stripe can't reach or can't
authenticate against `POST /api/stripe/connect/webhook`.

## First 5 minutes

1. Stripe Dashboard (the RIGHT account — platform AND phone-order
   acct_1U1ViDQ3LQbieqJG have separate webhook endpoints) → Developers →
   Webhooks → the `api.meridian.tips/api/stripe/connect/webhook` endpoint →
   **recent deliveries**. Failing status codes tell you which branch:
   - **timeouts / 5xx** → backend down or slow → [server-down.md](server-down.md) §B.
   - **400 invalid signature** → signing-secret mismatch: someone rotated the
     endpoint or the env. Fix `STRIPE_CONNECT_WEBHOOK_SECRET` (platform) /
     `STRIPE_PHONE_WEBHOOK_SECRET` (phone acct) on Railway to the dashboard's
     current `whsec_`.
   - **503 "Webhook not configured"** → the env secret is UNSET (fail-closed
     by design since PR #159) — set it.
   - **No deliveries at all** → the endpoint doesn't exist on this account
     (the phone-account activation gap) — create it with the event list from
     PR #448, copy the `whsec_` into Railway.
2. The backend un-records failed events and returns 500 so **Stripe retries
   automatically** (PR #415) — once the endpoint is healthy, the backlog
   usually drains itself. Check deliveries flip to 200.

## Drain anything Stripe gave up on

Stripe retries for ~3 days, so act inside that window. For anything older or
exhausted: Dashboard → the failed delivery → **Resend**. Verify each resend
flips the matching `phone_orders` row to `paid` and the kitchen push fired
(`pos_push_status` on the row / merchant confirms ticket).

Manual last resort (webhook unrecoverable, customer waiting): the signed
simulate pattern — POST the `checkout.session.completed` payload with the
correct `x-vapi`-style signing (see tests/api for the signed-webhook test
helpers) — or flip via `mark_order_paid` through the admin surface. Record
every manually-released order id in the incident timeline.

## Verify end-to-end

One $0.75 demo-line payment (`MERIDIAN_DEMO_TEST_CHARGE_CENTS` path): pay it,
watch the row flip paid + receipt SMS + (Test Kitchen merchant) Square ticket.
That exercises the exact leg that failed.

## Prevent

This leg has three fragile inputs: endpoint existence, secret sync, backend
uptime. After any Stripe-account or secret change, ALWAYS run the $0.75
verify before calling the change done — that rule is what catches this class
before customers do.
