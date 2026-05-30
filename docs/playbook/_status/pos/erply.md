# Erply

**Registry key:** `erply` — see `src/services/pos_connectors/registry.py` (line 716)

## Status
READY (config valid, read-only — `supports_orders: false`, no connect UI). Likely **NEEDS PARTNERSHIP** for production-scale rate limits.

## What it is
Cloud retail POS + inventory/ERP (Estonian-founded, US HQ Bonita Springs FL); strong on multi-location inventory, B2B/wholesale, matrix items.

## Vertical & market
- **Vertical:** retail — specialty, apparel, multi-location chains, B2B/wholesale
- **NA presence:** Small-to-Medium (stronger in EU and chain/franchise than SMB single-store)
- **Typical merchant:** 3–50 location retailer, wholesaler, or franchise that outgrew Square/Shopify POS
- **Geography:** Global; meaningful EU footprint, growing US chain presence

## How to spot the merchant uses it
- Back-office URL: `<clientcode>.erply.com` (numeric client code as subdomain — distinctive)
- POS app branded "Erply" or "Berlin POS" (newer browser POS); receipts: "Powered by Erply"
- Tell: staff reference a "client code" at login; "we use Erply for inventory across our stores"

## Auth method
API key (header) — `sessionKey` + `clientCode`. Sessions obtained via `verifyUser` POST (username/password); **expire ~1 hour** (403 / error 1054/1055 = re-auth). Cache and refresh on expiry; never call `verifyUser` per request.

## Data we can pull (per current config)
| Type | Available | Endpoint |
|------|-----------|----------|
| Orders / transactions | yes | `/?request=getSalesDocuments` |
| Catalog / items | yes | `/?request=getProducts` (matrix items) |
| Customers | yes | `/?request=getCustomers` |
| Employees | yes | `/?request=getEmployees` |
| Inventory | missing | add `getProductStock` / `getWarehouses` |
| Refunds | yes | `getSalesDocuments` (negative docs / credit notes) |

## Partner program / access requirements
- **Required:** Not for basic access (merchants can issue dev credentials); recommended for ISVs (partner code, sandbox, higher limits).
- **Sign-up:** No self-service portal — email `partners@erply.com` / `support@erply.com` (+1-518-855-6293). Assume 2–4 weeks. Cost/rev share not public.

## Sandbox / test environment
Yes via partner accounts; auth API sandbox at `api-auth-eu10.erply.com`. Use `getServiceEndpoints` to discover the merchant's regional cluster (EU/US).

## Rate limits
**1000 requests/hour/account** — hard cap, error 1002 on overrun, no backoff. Plan paginated incremental sync. Partners can request higher limits.

## Webhook / sync model
Poll-only on Classic API. Use `dateTimeFrom` on `getSalesDocuments` for hourly/daily incremental polls.

## Connect flow (what the merchant does)
1. Click "Connect Erply" (UI TBD)
2. Enter **client code** + Erply username/password (no OAuth)
3. Meridian POSTs `verifyUser` to `https://<clientcode>.erply.com/api/`, stores `sessionKey` + creds encrypted
4. Worker refreshes on 1054/1055

## Estimated effort to go LIVE
**M (1–2 weeks):** credential UI, session caching + auto-refresh, inventory endpoints, pagination respecting the 1000/hr cap, `getServiceEndpoints` regional routing.

## What blocks LIVE status today
- No connect UI (password capture, not OAuth); no session refresh logic
- No `getServiceEndpoints` discovery — config assumes one host per tenant
- Inventory endpoint missing from registry; partnership not formalized

## Common failure modes
- **403 or 1054/1055 mid-sync** → session expired → re-run `verifyUser`, retry
- **Error 1002 on all calls** → 1000/hr cap hit → halt; resume next hour; request partner-tier limit
- **DNS / 404 on `<clientcode>.erply.com/api/`** → wrong regional cluster → call `getServiceEndpoints` first
- **Empty `records` but `recordsTotal > 0`** → missing pagination → pass `pageNo` + `recordsOnPage` (max 100)

## Strategic notes
**Engineering callout — query-string-as-endpoint is unusual.** Erply's Classic API is a single endpoint (`/api/`) dispatched on the `request=` parameter (canonically POST form-data; GET works for reads). The registry treats each `?request=X` as a distinct REST path — fine for read-only use, won't extend to creates/updates. Build a thin Erply-specific request builder, don't retrofit the generic REST connector.

Merchant base skews mid-market chains and B2B/wholesale, not SMB single-store. Fewer logos but higher ACV; multi-location complexity is exactly what Meridian's cross-store benchmarking addresses.

## Recommendation
**WAIT** — defer behind larger NA verticals; revisit on first multi-location chain inbound.

**Reasoning:** Config is correct and effort is M, but NA SMB footprint is small vs. Lightspeed/Square/Shopify, and the 1000/hr cap + 1-hr session refresh add real operational cost. Build on demand when a chain prospect names Erply, and formalize partnership then.

## Sources consulted
- https://learn-api.erply.com/ , /getting-started
- https://wiki.erply.com/article/1320-authentication-api , /article/1720-authenticate
- https://erply.com/erply-api
- Registry config: `src/services/pos_connectors/registry.py` (line 716)
- Live API docs accessed: Yes
