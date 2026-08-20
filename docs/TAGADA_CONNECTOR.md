# Tagada Connector — storefront order ingest for the online-store trades

**Status: SPEC** (2026-08-20). Nothing here is built; the demo surfaces that
this feeds (`Today's orders`, `Subscriptions` tab) ship on `feat/pannrr-crm`'s
sibling branch `feat/peptide-pack` with deterministic demo data in exactly the
shapes below.

## Why

Meridian's ingest is POS-shaped: Square (live) and Clover connect a till.
The peptide pack — and any online-store trade after it — has no till. Its
revenue arrives through a storefront, and today Meridian cannot see it, which
makes every number on that trade's Today page a demo claim.

Tagada (tagada.io, "Ecommerce OS": checkout + multi-processor payments +
subscriptions + payment-triggered messaging) is the storefront stack the first
real merchant is already on: **Aidan's own peptide business runs on it**, so
the connector can be built and validated against live data we control before
it is sold to anyone.

## What already exists (verified 2026-08-20)

- **Account**: org `researchchem-1786744164869323869`, store
  `store_59ce792f1ac7` ("ResearchChem"), dashboard app.tagada.io. Login is a
  6-digit email code to the account email — no password.
- **Sandbox**: the store's only processor is Tagada's **Sandbox processor**
  ("ResearchChem Main Flow" routes to it). Test checkouts accept any card
  (e.g. 4242…), so end-to-end order flow can be exercised without money.
- **API token**: `meridian-connector-readonly` — role "Support" (**read-only**),
  no expiry. Stored at `/root/.secrets/tagada.env` with org/store ids.
  Read paths verified against the live API via `@tagadapay/node-sdk`:
  `orders.list`, `subscriptions.list`, `stores.list` all authenticate and
  return `{ data, total, page, pageSize, totalPages, hasMore }`.
- **Docs**: https://docs.tagada.io (REST reference, Node SDK, webhooks, and a
  CRM MCP exposing orders/subscriptions/customers/payments to agents).

## Architecture

Webhook-first, poll-backfilled — the same shape as the Square connector
(`src/api/routes/webhooks.py`, `bookings_square.py`), so the operational
story (retries, idempotency, reconciliation) is one story, not two.

```
Tagada store ──webhook──▶ POST /api/webhooks/tagada     (FastAPI, new route)
                              │  verify X-TagadaPaySignature (HMAC-SHA256,
                              │  "sha256=<hex>", timingSafeEqual)
                              │  enqueue → return 2xx fast
                              ▼
                    tagada_events (raw, idempotent on event id)
                              ▼
              normalizer → orders / subscriptions rows on the org
                              ▼
        dashboards read what they already read (revenue, orders feed,
        subscriptions book) — merchant-keyed, market-converted
```

- **Webhooks** (push, the live path). Register per store via
  `tagada.webhooks.create({ storeId, url, eventTypes })` → returns endpoint id
  + **signing secret** (store beside the merchant's connector row, encrypted,
  same treatment as Square webhook secrets). Events we consume:
  - `order/paid`, `order/refunded`, `order/failed` → the orders feed and the
    day's takings. (`order/created` is noise for analytics — an unpaid cart.)
  - `payment/succeeded`, `payment/refunded` → reconciliation only.
  - `subscription/created`, `subscription/canceled`, `subscription/paused`,
    `subscription/resumed`, `subscription/pastDue`, `subscription/rebillSucceeded`,
    `subscription/rebillDeclined` → the Subscriptions tab, MRR, churn flags.
- **Backfill/reconcile** (pull, the trust path). Nightly + on-connect:
  `GET /orders` and `GET /subscriptions` paged by `page`/`pageSize` until
  `hasMore` is false, upserting by Tagada id. Webhooks can be missed;
  the poll makes the ledger converge anyway.

## Data mapping

| Tagada | Meridian |
|---|---|
| order (paid) | order row: id, placed_at, customer name/email, line items, total cents, channel `web`, status `paid` → frontend `WorkspaceOrder` (already defined, `frontend/src/lib/demo-orders.ts`) |
| order refunded | status `refunded` (feed shows struck-through total) |
| subscription | `SubscriptionsPage` row: plan, cadence, price cents, status (`active`/`past_due`/`paused`), next rebill date, started_at (tenure) |
| store | connector row: org_id ↔ tagada store id, api key ref, webhook secret ref |

Money: Tagada amounts land in the store's currency; store minor units as-is
and tag the currency — do NOT reuse the demo's US-cents-times-multiplier
trick, which is a demo convention, not bookkeeping.

## Frontend (mostly already done)

- `Today's orders` feed: swap `demoOrdersFor(...)` for
  `GET /api/dashboard/orders?day=` when the org has a Tagada connection;
  identical shape, no screen change. Tile figures (web orders, awaiting
  shipment) derive from the same rows.
- `Subscriptions` tab (trades: peptides, mobiledetailing): swap the seeded
  book for `GET /api/dashboard/subscriptions`; pause/resume/cancel buttons
  call through only once we hold a **write-scoped** token (see Open items).
- Connection UI: a "Connect your storefront" card in Settings → the v1.5
  Integrations Hub provider list (PR #499) gets a `tagada` provider; verified
  means a real round-trip (`stores.list` succeeds), per that PR's rule.

## Security

- Webhook route verifies `X-TagadaPaySignature` before parsing; unsigned or
  bad-signature requests are dropped with 401 and never enqueued.
- Per-merchant API keys encrypted at rest (same vault treatment as Square
  tokens); never in env for multi-tenant use. Aidan's own key stays in
  `/root/.secrets/tagada.env` for development against ResearchChem only.
- Read-only role for ingest; the write-scoped token (subscription actions,
  webhook registration) is minted separately and only when Phase 3 lands.

## Phases

1. **Ingest read path** (backend day-ish): connector row + nightly backfill
   poll → orders/subscriptions tables → the two dashboard endpoints. Proves
   on ResearchChem sandbox checkouts.
2. **Webhooks** (half day): endpoint registration (needs write token or
   one-time manual registration from the dashboard), signature verification,
   idempotent event ingest, reconcile job.
3. **Actions** (half day): pause/resume/cancel subscription from the tab via
   Tagada's `subscriptions` write endpoints; needs admin-scoped token and a
   confirm dialog — these touch real billing.
4. **Onboarding**: Integrations Hub card; merchant pastes an access token
   from their Tagada dashboard (Settings → Access Tokens), we verify with
   `stores.list` and register the webhook.

## Open items

- The stored token is **read-only**: webhook registration and subscription
  actions need an admin-scoped token — mint one when Phase 2 starts, not
  before (least privilege until then).
- Sandbox vs prod hosts: docs name `crm.tagadapay.dev` for sandbox, but the
  live org already carries a Sandbox *processor*, which is what test orders
  actually need. Treat the single org + sandbox processor as the test rig.
- Rate limits and event-payload schemas are not documented on the pages
  fetched; confirm against `api-support@tagadapay.com` or the API reference
  before Phase 2 sizing hardens.
