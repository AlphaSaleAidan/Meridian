# Lightspeed Retail

**Registry key:** `lightspeed-retail` — see `src/services/pos_connectors/registry.py`

> Important disambiguation: the registry config targets the **R-Series API** (`api.lightspeedapp.com/API/V3/Account/{account_id}`). Lightspeed sells two retail products under the "Lightspeed Retail" umbrella — **R-Series** (original Lightspeed Retail, still actively sold) and **X-Series** (formerly Vend, acquired 2021, uses `x-series-api.lightspeedhq.com`). Our config covers R-Series only. X-Series merchants require a separate connector.

## Status
READY (config valid, no customer-facing OAuth UI, read-only — `supports_orders: false`)

## What it is
Cloud-based retail POS for SMB specialty stores; iPad + Mac/PC front-of-house, web back-office for inventory, purchasing, and reporting.

## Vertical & market
- **Primary vertical:** retail (specialty / SMB)
- **Estimated NA market presence:** Large (top-3 specialty retail POS alongside Square and Shopify POS)
- **Typical merchant profile:** 1–10 location boutique, bike shop, sporting goods, pet store, jewelry, CBD/smoke shop, gift shop
- **Geographic concentration:** Global; strongest in US, Canada, Europe, Australia

## How to spot the merchant uses it
- iPad terminal in a black hard case with cash drawer; receipt printer is typically Star or Epson
- Back-office login URL: `*.lightspeedapp.com` or `*.retail.lightspeed.app`
- Receipt footer: "Powered by Lightspeed" (R-Series) or no footer
- Tells: "We're on Lightspeed Retail," "we use Lightspeed for inventory," historical "we came over from Merchant OS"

## Auth method
OAuth 2.0 (authorization code flow). Refresh tokens are long-lived; access tokens expire in 30 min.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | yes | `/Sale.json` | Includes line items via `?load_relations=["SaleLines"]` |
| Catalog / items | yes | `/Item.json` | |
| Customers | yes | `/Customer.json` | |
| Employees | yes | `/Employee.json` | |
| Inventory | yes (via Item) | `/Item.json` | Stock counts on Item resource |
| Refunds | yes | `/Sale.json` | Negative-total Sales |

## Partner program / access requirements
- **Partner program required:** No for basic API access; yes to be listed in the Lightspeed app marketplace
- **Sign-up URL:** `https://cloud.lightspeedapp.com/oauth/register.php` (self-service client_id/secret)
- **Approval timeline:** Self-service for credentials; marketplace listing requires contacting `[email protected]`
- **Cost / revenue share:** Free for API credentials; marketplace listing terms not public

## Sandbox / test environment
- **Available:** Not documented as a separate sandbox; developers typically use a trial account
- **URL:** Standard signup at lightspeedhq.com (14-day trial of live R-Series)
- **Notes:** Confirm with Lightspeed dev support; many integrators use a dedicated trial tenant

## Rate limits
Leaky bucket: 90-request burst (+10 per register beyond first); drip rate 1 req/sec (+0.5/sec per extra register). Some endpoints cost >1 drip. 429 requires ≥1s backoff. Source: developers.lightspeedhq.com/retail/introduction/ratelimits/

## Webhook / sync model
Webhooks supported (Sale, Item, Customer events). Current config is poll-only — adding webhook handler is a follow-up enhancement.

## Connect flow (what the merchant does)
1. Merchant clicks "Connect Lightspeed Retail" in Meridian (UI to be built)
2. Redirected to `https://cloud.lightspeedapp.com/oauth/authorize.php?...`
3. Logs into Lightspeed back-office and approves Meridian's requested scopes
4. Lightspeed redirects back with `code` → Meridian exchanges for refresh + access token
5. Meridian calls `/Account.json` (no account_id needed) to discover the merchant's `account_id`, then stores it

**`account_id` discovery:** Merchants don't manually look this up — call `GET https://api.lightspeedapp.com/API/Account.json` with the access token; response contains the numeric Account ID. Store and template into every subsequent URL.

## Estimated effort to go LIVE (config → production-ready)
M (1–2 weeks): register OAuth app, build connect UI + callback, add `/Account.json` discovery step, smoke-test pagination + rate-limit backoff.

## What blocks LIVE status today
- No customer-facing OAuth UI in Meridian connect flow
- No `/Account.json` discovery step in connector (current config hardcodes `{account_id}` template)
- No webhook handler (poll-only is acceptable for v1)
- `supports_orders: false` is correct — R-Series Sale creation is non-trivial (requires SaleLine + Payment children); leave for v2

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 429 errors during initial backfill → **Cause:** ignoring leaky bucket → **Fix:** respect `X-LS-API-Bucket-Level` response header, back off when >80%
- **Symptom:** Empty Sale responses → **Cause:** missing `?load_relations=["SaleLines","SalePayments"]` → **Fix:** add load_relations to default query
- **Symptom:** Auth works, all calls 404 → **Cause:** R-Series merchant being routed through X-Series connector (or vice versa) → **Fix:** ask merchant which product they're on before connecting
- **Symptom:** Refresh token rejected after long idle → **Cause:** merchant revoked app in Lightspeed back-office → **Fix:** prompt reconnect

## Strategic notes
Lightspeed Retail merchants are high-value Meridian targets: above-average AOV, multi-channel (often have ecom + physical), use Lightspeed's reporting heavily — they already understand analytics ROI. The pitch is "go beyond Lightspeed Insights" with cross-location benchmarking and AI Q&A.

Watch out: a merchant saying "Lightspeed" might mean R-Series, X-Series, Restaurant (K-Series), or Golf — always confirm before quoting integration timing. X-Series adoption is growing because Lightspeed is actively migrating Vend customers; expect inbound asks. Build the X-Series connector next (separate registry entry).

## Recommendation
**BUILD NOW** (in current sprint).

**Reasoning:** Config is valid against current R-Series API, OAuth credentials are self-service (no partner approval blocking), and the merchant base is large + analytics-friendly. Effort is M — a single backend dev can ship the connect UI and account discovery in ~1 week. X-Series (former Vend) is a separate follow-up; do not conflate.

## Sources consulted
- https://developers.lightspeedhq.com/retail/introduction/introduction/
- https://developers.lightspeedhq.com/retail/introduction/ratelimits/
- https://developers.lightspeedhq.com/retail/authentication/authentication-overview/
- https://www.lightspeedhq.com/partners/developers/
- https://www.lightspeedhq.com/pos/retail/
- Registry config: `src/services/pos_connectors/registry.py` (line 122)
- Live API docs accessed: Yes
