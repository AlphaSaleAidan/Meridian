# Lightspeed Restaurant (K-Series)

**Registry key:** `lightspeed-restaurant` — see `src/services/pos_connectors/registry.py`

## Status
OUTDATED CONFIG — base URL and auth method in registry do not match any current Lightspeed Restaurant product (K-, O-, or U-Series). Needs config fix AND customer-facing OAuth UI before LIVE.

## What it is
Cloud restaurant POS for full-service, quick-service, hotels, and hospitality groups — sold globally by Lightspeed (NYSE/TSX: LSPD) under the "Lightspeed Restaurant" brand, formerly known as Kounta (AU), iKentoo (EU), and Upserve (US).

## Vertical & market
- **Primary vertical:** restaurant (full-service, QSR, bars, hotel F&B, multi-unit groups)
- **Estimated NA market presence:** Medium-Large (consolidated rollup of Kounta/iKentoo/Upserve/Breadcrumb; strong in US independent + multi-unit, large in EU/AU)
- **Typical merchant profile:** independent full-service restaurants, multi-location groups, hospitality venues, hotel F&B
- **Geographic concentration:** global — strong AU (Kounta heritage), EU (iKentoo heritage), US (Upserve heritage)

## How to spot the merchant uses it
- iPad-based terminals; cloud UI at `https://*.lightspeed.app` or legacy `*.kounta.com` / `*.upserve.com` / `*.ikentoo.com`
- Login URLs: `my.lightspeed.app`, `manager.lsk.lightspeed.app`
- Receipt footer often says "Powered by Lightspeed" (post-rebrand) or legacy Kounta/Upserve
- Conversational tells: "Kounta", "iKentoo", "Upserve", "K-Series", "O-Series"

## Auth method
**OAuth 2.0 authorization-code grant** (K-Series, current). Refresh tokens valid 14 days. Bearer access token in `Authorization` header. NOT a simple API-key bearer scheme — the registry's `auth_type: bearer` is wrong; needs `oauth_authorization_code` (a flow `GenericRESTConnector` doesn't currently support — `oauth_client_credentials` is the closest existing option but is not the same flow).

## Data we can pull (per current config vs. actual K-Series API)
| Type | Available | Actual K-Series endpoint | Notes |
|------|-----------|--------------------------|-------|
| Orders / transactions | ✓ | `/financial/v1/...` and `/financialV2/...` (Get Sales, Get Daily Financials, Get Aggregated Sales) | Registry's `/transactions` is wrong |
| Catalog / items | ✓ | `/items/v1/...` and rich-items endpoints | Registry's `/items` is approximately right, path prefix is wrong |
| Customers | UNCERTAIN | Not surfaced as a top-level resource in K-Series docs reviewed | Registry's `/customers` likely returns 404 |
| Employees | ✓ | `/staff/v1/businessLocations/{id}/userTypes/POS` | Registry's `/employees` is wrong path |
| Inventory | UNCERTAIN — not validated | — | |
| Refunds | UNCERTAIN | Likely surfaced inside sales/financial endpoints | |
| Order create | ✓ | Order & Pay: Create Local Order, Create To Go Order | Registry's `/orders` is wrong path |

## Partner program / access requirements
- **Partner program required:** Yes — required for production access
- **Sign-up URL:** Partner Application form via `api-portal.lsk.lightspeed.app` (must select "Restaurant" when asked which product)
- **Approval timeline:** UNCERTAIN — Lightspeed does not publish SLAs; community evidence suggests weeks, not days. Explicit approval by Lightspeed Partnerships or Hospitality Product team required
- **Cost / revenue share:** UNCERTAIN — not publicly disclosed; partner must sign API Terms of Use Agreement
- Merchants can also request access directly via their Account Manager (faster path for single-merchant POCs)

## Sandbox / test environment
- **Available:** Yes
- **URL:** `https://api.trial.lsk.lightspeed.app` (demo accounts provisioned via Developer Portal after partner approval)
- **Notes:** No self-serve sandbox — gated by partner approval

## Rate limits
UNCERTAIN — not documented on the public API overview page reviewed.

## Webhook / sync model
**Hybrid** — REST polling + webhooks (K-Series exposes webhooks for Staff, Reservations, Order & Pay, PMS).

## Connect flow (what the merchant does) — TO BUILD
1. Merchant clicks "Connect Lightspeed Restaurant" in Meridian
2. Redirect to Lightspeed OAuth authorize URL (K-Series authorization-code flow) with our `client_id` and requested scopes (`orders-api`, `financial-api`, `items`, `staff-api`)
3. Merchant logs into Lightspeed and approves
4. Lightspeed redirects back with `code` → we exchange for access + refresh tokens at `/oauth/token`
5. Store refresh token (encrypted); auto-rotate access token; refresh-token rotation required every 14 days

## Estimated effort to go LIVE
**L (1+ months)** — driven primarily by partner-approval wait, plus engineering: (a) fix registry config, (b) extend `GenericRESTConnector` or add OAuth-authorization-code support, (c) build customer-facing OAuth redirect UI, (d) refresh-token rotation cron, (e) endpoint-path corrections + integration tests against a demo account.

## What blocks LIVE status today
- Registry `base_url` `https://api.lightspeedrestaurant.com/v1` does not resolve to any current Lightspeed product (no DNS response observed)
- Registry `auth_type: bearer` is wrong — real flow is OAuth 2.0 authorization-code
- Endpoint paths (`/transactions`, `/items`, `/employees`, `/customers`, `/orders`) do not match K-Series API structure
- No partner approval obtained → no `client_id`/`client_secret` issued
- No customer-facing OAuth connect UI built
- `GenericRESTConnector` likely lacks authorization-code flow (only `bearer`, `header`, `basic`, `query`, `oauth_client_credentials`, `csv_only` are listed in registry docstring)

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Cannot resolve host api.lightspeedrestaurant.com" → **Likely cause:** stale registry base URL → **Fix:** update to `https://api.lsk.lightspeed.app` (or O-Series equivalent if merchant is on legacy O-Series — confirm product line first)
- **Symptom:** Merchant says "I use Upserve / Kounta / iKentoo" → **Likely cause:** legacy brand on K-Series or U-Series → **Fix:** ask which dashboard URL they log into; route U-Series merchants to the existing `upserve` connector
- **Symptom:** 401 after 14 days → **Likely cause:** refresh token expired → **Fix:** force re-auth; build proactive refresh-token rotation
- **Symptom:** Endpoint returns 404 → **Likely cause:** registry path is wrong → **Fix:** consult K-Series OpenAPI at `api-docs.lsk.lightspeed.app`

## Strategic notes
Lightspeed Restaurant is the consolidated brand for what used to be **four separate POS products** (Kounta, iKentoo, Upserve, Breadcrumb). Globally significant footprint — easily top-10 restaurant POS by merchant count when combining heritage brands. The K-Series API is modern and well-documented; the friction is the partner-approval gate, not the tech. There is also an O-Series (legacy iKentoo lineage) and the existing `upserve` registry entry for U-Series — be careful to route merchants to the right connector based on their dashboard URL. Sales reps should not promise "instant connect" — this is OAuth + partner-gated, so expect a 2-4 week stand-up per new merchant until we have partner-level credentials.

## Recommendation
**BUILD NOW** (but start the partner application immediately — it is the long pole).

**Reasoning:** Global merchant base across four heritage brands gives high TAM and Meridian already has `upserve` (U-Series) and needs K-Series to cover the rest. Partner approval is gating and slow, so submit the application this week even if engineering work waits — config fix + OAuth UI is ~1-2 weeks of work that should land before approval comes through.

## Sources consulted
- https://api-docs.lsk.lightspeed.app/ (K-Series API reference)
- https://api-portal.lsk.lightspeed.app/quick-start/intro (Developer Portal intro)
- https://api-docs.lsk.lightspeed.app/authentication (OAuth2 flow, scopes)
- https://api-portal.lsk.lightspeed.app/guides/tutorials/developer-portal (partner access)
- https://o-series-support.lightspeedhq.com/hc/en-us/articles/31329293014427-OAuth-2-0-Process (O-Series, for disambiguation)
- https://developers.lightspeedhq.com/resto-api/introduction/gettingstarted/ (legacy resto-api docs, for disambiguation)
- Live curl probe of `api.lightspeedrestaurant.com` — no DNS response
- Live API docs accessed: Yes
