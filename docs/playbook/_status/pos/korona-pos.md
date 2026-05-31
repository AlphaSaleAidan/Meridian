# KORONA POS

**Registry key:** `korona-pos` — see `src/services/pos_connectors/registry.py`

> Note: registry `base_url` is templated as `https://api.koronacloud.com/web/api/v3/accounts/{account_id}`. In practice Korona routes tenants to numbered subdomains (e.g. `https://196.koronacloud.com/web/api/v3`) surfaced by the back-office APIv3 widget. Treat the host as merchant-provided, not hardcoded — see "Connect flow."

## Status
READY (config valid, basic-auth + account_id are merchant-self-service; no customer-facing UI, no order write-back — `supports_orders: false`)

## What it is
Cloud retail POS by German vendor COMBASE (KORONA.cloud); web back-office plus thin terminal client. Strong inventory engine — frequently positioned as the "outgrew Square" upgrade for SMB retail and the default for ticketing/admission venues.

## Vertical & market
- **Primary vertical:** retail (multi-vertical) — convenience, smoke/vape, liquor, quick-service, ticketing/admission, museums, wineries
- **Estimated NA market presence:** Medium — established in smoke/vape and liquor; punches above its weight in ticketing
- **Typical merchant profile:** 1–20 location independent retailer that needs strong inventory + age verification + loyalty; or a single-location attraction with timed-entry ticketing
- **Geographic concentration:** Germany/EU heritage; US presence run out of Las Vegas (COMBASE USA)

## How to spot the merchant uses it
- Back-office URL is `*.koronacloud.com` or app at `appcenter.koronacloud.com`
- Terminal UI shows a "KORONA" wordmark; hardware is generic (HP/Elo all-in-one or tablet)
- Receipt footer often reads "KORONA.pos"
- Tells: "we use KORONA," "we're on COMBASE," smoke-shop owners mentioning age-verification scanning + multi-store inventory in one breath

## Auth method
HTTP Basic auth. Credentials are created per-tenant in the back-office APIv3 widget (login/password with scoped permissions). `Authorization: Basic base64(login:password)`.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | yes | `/receipts` | Read-only in current config |
| Catalog / items | yes | `/products` | |
| Customers | yes | `/customers` | |
| Employees | yes | `/cashiers` | "Cashier" is the Korona term |
| Inventory | yes (via products + separate stock endpoints) | `/products` | Stock-on-hand lives on warehouse/stock endpoints not in current config |
| Refunds | yes | `/receipts` | Returns are negative-total receipts |

`data_key: "results"` matches Korona's pagination envelope. `test_endpoint` is empty — add a cheap probe (e.g. `GET /cashiers?size=1`) before going LIVE.

## Partner program / access requirements
- **Partner program required:** No for tenant-scoped API access — any paying KORONA.cloud merchant can mint credentials themselves
- **Sign-up URL:** Developer portal at `developer.combase.systems` (gated login); marketing entry at `koronapos.com/developers/`
- **Approval timeline:** Self-service for merchant-provisioned creds; AppCenter listing requires contacting COMBASE (`inquiries@combase-usa.com`, +1 833-200-0213)
- **Cost / revenue share:** Not publicly disclosed for AppCenter listing; tenant API access is included in the merchant's KORONA.cloud subscription

## Sandbox / test environment
- **Available:** No dedicated sandbox documented; integrators typically use a trial KORONA.cloud tenant
- **URL:** Trial via `koronapos.com`
- **Notes:** Confirm test-tenant policy with COMBASE before bulk testing

## Rate limits
Not publicly documented. Treat as conservative — exponential backoff on 429, cap concurrency at ~5 req/s per tenant until validated with the merchant's host shard.

## Webhook / sync model
Poll-only in current config. Korona exposes change tracking via `revision` cursors on most resources (incremental sync rather than firehose webhooks).

## Connect flow (what the merchant does)
1. Merchant logs into KORONA back-office → **Settings → Data Exchange** → search "api" → open **APIv3 widget**
2. Widget shows their **Account-ID** and **Endpoint URL** (the numbered subdomain). Merchant clicks **Add** to create an API login/password with read permissions on receipts/products/customers/cashiers
3. Merchant pastes Account-ID, Endpoint, login, password into Meridian connect form (UI to be built)
4. Meridian stores credentials, probes `GET {endpoint}/accounts/{account_id}/cashiers?size=1`, then begins backfill

## Estimated effort to go LIVE (config → production-ready)
S–M (3–7 days): build the 4-field connect form, add the `base_url` override (accept merchant-supplied host), add a real `test_endpoint`, wire pagination on `results` envelope.

## What blocks LIVE status today
- No customer-facing connect UI accepting host + account_id + login + password
- `base_url` hardcodes `api.koronacloud.com` — must accept the merchant's actual numbered host from the APIv3 widget
- `test_endpoint` is empty — add a real liveness probe
- No incremental-sync logic using Korona's `revision` cursor (full-table polling will work for v1)

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401 on every call → **Cause:** wrong host shard (using `api.koronacloud.com` instead of merchant's e.g. `196.koronacloud.com`) → **Fix:** ask merchant to re-read the Endpoint field in the APIv3 widget
- **Symptom:** 403 on `/receipts` but `/cashiers` works → **Cause:** API credential lacks receipt-read permission → **Fix:** merchant edits credential in APIv3 widget, checks receipts scope
- **Symptom:** Empty `results` on `/products` → **Cause:** pagination — missing `page`/`size` query params → **Fix:** default to `size=100` and follow `links.next`

## Strategic notes
Strong ICP fit for Meridian's smoke-shop and convenience vertical — Korona's bread-and-butter is exactly the inventory-heavy, multi-SKU, age-restricted retail where benchmarking and AI Q&A on margin/velocity beat the built-in reports. Liquor and ticketing are bonus expansion lanes. Because creds are merchant-self-service, sales can demo with a live tenant the same day; no partner gating, no 6-week procurement loop.

## Recommendation
**BUILD NOW.**

**Reasoning:** Self-service basic-auth + tenant-owned credentials = zero partnership risk and S–M engineering lift. Strong overlap with Meridian's smoke-shop go-to-market makes this a fast ROI add behind Lightspeed Retail and Clover.

## Sources consulted
- https://manual.koronapos.com/korona-cloud-api-v3/api-setup/
- https://manual.koronapos.com/how-can-i-integrate-with-korona-pos-api-apiv3-widget/
- https://support.korona.de/korona-cloud-api/
- https://koronapos.com/developers/
- https://github.com/COMBASE/cloud-api-v3-js-client
- https://github.com/kr1sp1n/koronacloud
- Registry config: `src/services/pos_connectors/registry.py` (line 667)
- Live API docs accessed: Yes (manual portal); developer portal gated behind login (not accessed)
