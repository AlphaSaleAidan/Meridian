# Shopmonkey

**Registry key:** `shopmonkey` — see `src/services/pos_connectors/registry.py` (lines 257–271)

## Status
READY — config endpoints, base URL, and auth method match published v3 docs. Off-ICP vertical is the real blocker, not the integration.

## What it is
Cloud auto-shop management SaaS (POS + estimates + repair orders + digital vehicle inspection + payments) for independent repair shops, tire stores, and small service chains. Modern competitor to Tekmetric, Mitchell1, and ShopWare.

## Vertical & market
- **Primary vertical:** automotive — independent repair, tire, quick-lube, multi-bay service
- **Estimated NA market presence:** Large within modern cloud auto-shop SaaS; well-funded scale-up
- **Typical merchant profile:** 2–10 bay shop, $500K–$5M revenue, owner-operator or small chain
- **Geographic concentration:** US + Canada

## How to spot the merchant uses it
- Service writer working in a browser app branded "Shopmonkey"
- Customer-facing estimate / approval link sent via SMS with "Shopmonkey" branding in the footer
- In-shop payments funneled through Shopmonkey Payments (Affirm pay-over-time option visible at checkout)
- Conversational tells: "we're on Shopmonkey," "send the estimate through SM," "approve it on your phone"

## Auth method
OAuth 2.0 bearer token. `Authorization: Bearer <API_TOKEN>`. Registry config (`auth_type: header`, `auth_header_name: Authorization`) is correct — note the connector must prepend `Bearer ` to the token value.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `/orders` | v3 confirms `/orders` resource |
| Catalog / items | Yes | `/services` | Shopmonkey models shop offerings as services |
| Customers | Yes | `/customers` | |
| Employees | Yes | `/users` | |
| Inventory | Not configured | `/inventory` (parts/tires/labor/fees exist in API) | Not wired in registry |
| Refunds | Unknown | — | Likely embedded in order payload — needs live validation |
| Vehicles | Not configured | `/vehicles` | Available in API, not in registry — useful for auto context |

`supports_orders: True`; order push (`order_create_endpoint: /orders`) is plausible per docs but unverified against a live shop.

## Partner program / access requirements
- **Partner program required:** No for read-only API access — API keys are self-service inside the shop's account
- **Sign-up URL:** https://shopmonkey.dev (developer portal); merchants generate keys at **Settings → Integration → API Keys → Add New Key**
- **Approval timeline:** Self-service (minutes); no Shopmonkey approval needed for a merchant-issued key
- **Cost / revenue share:** No public developer fee or rev share; formal "marketplace partner" listings appear to be relationship-driven, not open self-serve

## Sandbox / test environment
- **Available:** Not publicly documented as a separate sandbox host
- **URL:** N/A — testing happens against production with a scoped API key
- **Notes:** Use a low-volume test shop account; key cannot be re-viewed after creation, so store it immediately

## Rate limits
Exist but specific numbers not published. Responses surface `X-RateLimit-Limit-Minute`, `X-RateLimit-Remaining-Minute`, and `Retry-After` on 429. Build a token-bucket retry that honors `Retry-After`.

## Webhook / sync model
Hybrid — Shopmonkey exposes a `/webhooks` resource for event subscriptions; current registry config is poll-only. Add webhooks before any high-frequency shop.

## Connect flow (what the merchant does)
1. Shop owner must be on a Shopmonkey plan that exposes the Integration settings
2. In Shopmonkey: **Settings → Integration → API Keys → Add New Key**, copy the token immediately
3. In Meridian: **Settings → Integrations → Connect Shopmonkey** (UI not yet built), paste token + shop/location ID
4. Backfill kicks off against `/orders` paginated by date

## Estimated effort to go LIVE (config → production-ready)
M (1–2 weeks) — config is right; remaining work is the customer-facing connect UI, live endpoint validation against one real shop, webhook wiring, and pagination tuning.

## What blocks LIVE status today
- **No customer-facing connect UI** (same gap as every gated integration)
- **No live shop tested** — endpoint paths and `data` envelope confirmed against docs, not against real traffic
- **No webhook subscription code path** — poll-only today
- **Off-ICP vertical** — even with a clean integration, Meridian has no auto-shop dashboards or persona-tuned analytics

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "401 on every call" → **Likely cause:** missing `Bearer ` prefix or rotated/deleted key → **Fix:** confirm header is `Authorization: Bearer <token>`; have shop regenerate key
- **Symptom:** "429 storms during backfill" → **Likely cause:** ignoring `Retry-After` and per-minute caps → **Fix:** honor `X-RateLimit-Remaining-Minute`; throttle batch size
- **Symptom:** "Empty `data` array" → **Likely cause:** wrong location scoping or date window → **Fix:** verify `/locations` returns the expected shop; widen date filter

## Strategic notes
Shopmonkey is well-funded (~$110M raised through Series C led by ICONIQ Growth, Bessemer, Index) and grew revenue to ~$29.7M ARR in 2024, but Glassdoor reviews reference 2024 layoffs and abrupt headcount cuts — read as "scaled fast, now optimizing," not "in trouble." Net: stable enough to integrate against, but not a vertical Meridian should chase. Different buyer (service manager / shop owner), different KPIs (RO count, hours billed, parts margin) than Meridian's F&B + retail dashboards. Reps should not prospect auto repair shops. If an inbound shop already on Shopmonkey appears, log and flag for product — do not commit a timeline.

## Recommendation
DEFER.

**Reasoning:** Integration is technically straightforward (self-service keys, config matches docs) but the automotive vertical is off-ICP, and Meridian has no auto-shop analytics to deliver value post-connect. Revisit only if Meridian commits to automotive expansion.

## Sources consulted
- https://shopmonkey.dev/overview
- https://shopmonkey.dev/quickstart
- https://shopmonkey.dev/resources/integration
- https://support.shopmonkey.io/hc/en-us/articles/38743124485780-Shopmonkey-API
- https://www.shopmonkey.io/integrations/api-es-webhooks
- https://www.crunchbase.com/funding_round/shopmonkey-io-series-c--4220137f
- https://getlatka.com/companies/shopmonkey
- `src/services/pos_connectors/registry.py` (lines 257–271)
- Live first-party API docs accessed: Yes (developer portal public)
