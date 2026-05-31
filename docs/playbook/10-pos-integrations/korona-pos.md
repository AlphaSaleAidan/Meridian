# Korona POS

> Status: **WAVE 1 BUILDING** — config is READY in registry, connect UI in development
> Category: retail (specialty retail, multi-location, wine/spirits common)
> Auth: Basic auth

## What you tell the merchant

"Korona support is rolling out this month. You'll connect with your Korona Cloud account credentials — same login you use for the admin panel. We import 18 months of receipts and start insights within 24 hours of connect."

## How the merchant connects (when live)

1. Merchant logs into KORONA back-office → **Settings → Data Exchange** → search "api" → open the **APIv3 widget**
2. Widget shows their **Account-ID** and **Endpoint URL** (a numbered subdomain, e.g. `196.koronacloud.com` — NOT the generic `api.koronacloud.com`). They click **Add** to create an API login/password with read scopes on receipts/products/customers/cashiers.
3. From the Meridian portal, **Settings → POS Connections → Connect Korona** — they paste Account-ID, Endpoint, login, password
4. We probe `GET {endpoint}/accounts/{account_id}/cashiers?size=1` and start the receipt backfill

Typical time to connect (projected): **2 minutes** once they have the APIv3 widget open.

**No partner program required** for tenant-scoped API access — any paying KORONA.cloud merchant can mint credentials themselves. Developer portal: https://koronapos.com/developers/. AppCenter listing (optional) requires contacting COMBASE ([email protected]).

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Receipts (transactions) | hourly poll | 18 months |
| Products (catalog) | daily | full history |
| Cashiers (employees) | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.koronacloud.com/web/api/v3/accounts/{account_id}`

## What features they get (when live)

Strong fit for specialty retail:

- Product Velocity (which SKUs move, which are dead)
- Inventory Intelligence (reorder point predictions)
- Basket Analysis (especially valuable for wine/spirits cross-sell)
- Revenue trend + forecasting
- Cashier-level performance comparison
- Customer LTV (where customer accounts exist)
- Seasonality patterns

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Real-time push (hourly poll)

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on every call | Wrong host shard — using generic `api.koronacloud.com` instead of merchant's numbered host (e.g. `196.koronacloud.com`) | Have merchant re-read the Endpoint field in the APIv3 widget; we accept merchant-supplied host |
| 403 on `/receipts` but `/cashiers` works | API credential lacks receipt-read scope | Merchant edits the credential in the APIv3 widget, checks the receipts scope |
| Empty `results` on `/products` | Pagination — missing `page`/`size` query params | Default `size=100`, follow `links.next` |

### Edge cases we expect but haven't seen yet
- Auth rejected because account uses 2FA on the Korona Cloud login — generate an API-only user without 2FA.
- Backfill slow due to receipt volume + rate limits — expected for high-volume stores.

## Sales angle

**Opener:** "Are you on Korona? You've got receipt-level data most POSes don't expose cleanly — we use that for SKU-level demand forecasting. Most wine/spirits and specialty retail merchants find CA$2K+/mo in over-ordering they can stop."

**Best verticals on Korona:** wine/spirits/liquor, specialty grocery, gift stores, smoke/vape, ticketing/admission (museums, wineries), multi-SKU retail.

**Why this is the wedge:** Korona is frequently positioned as the "outgrew Square" upgrade for SMB retail — strong inventory engine, age verification, multi-store. Punches above its weight in ticketing (timed-entry venues, museums, wineries). Bread-and-butter is exactly Meridian's smoke-shop and convenience vertical: inventory-heavy, multi-SKU, age-restricted retail where benchmarking + AI Q&A on margin/velocity beat the built-in reports. Because creds are merchant-self-service, sales can demo with a live tenant the same day — no partner gating, no procurement loop.

## What blocks live status today

- **No customer-facing connect UI** accepting host + account_id + login + password (4-field form)
- **`base_url` hardcodes `api.koronacloud.com`** — must accept the merchant's actual numbered host from the APIv3 widget (engineering fix)
- **`test_endpoint` is empty** — add a real liveness probe (e.g. `GET /cashiers?size=1`)
- **No incremental-sync logic** using Korona's `revision` cursor — full-table polling works for v1
- Estimated effort to LIVE: **3–7 days**

## Reference docs

- API setup guide: https://manual.koronapos.com/korona-cloud-api-v3/api-setup/
- APIv3 widget walkthrough: https://manual.koronapos.com/how-can-i-integrate-with-korona-pos-api-apiv3-widget/
- Support docs: https://support.korona.de/korona-cloud-api/
- Developer landing: https://koronapos.com/developers/
- Reference JS client: https://github.com/COMBASE/cloud-api-v3-js-client

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (korona-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #5) + docs/playbook/_status/pos/korona-pos.md (Phase 1)_
