# SpotOn

**Registry key:** `spoton` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP

## What it is
All-in-one restaurant POS + payments + reservations + online ordering platform; major Toast competitor that grew rapidly in US full-service and casual restaurants.

## Vertical & market
- **Primary vertical:** restaurant (multi-product: SpotOn Restaurant, Reserve, Retail, Enterprise)
- **Estimated NA market presence:** Large (top-5 US restaurant POS by 2024-2025; aggressive enterprise + SMB push)
- **Typical merchant profile:** independent FSR, multi-unit casual/fine dining, hospitality groups, stadiums/venues (via Appetize acquisition)
- **Geographic concentration:** US-dominant

## How to spot the merchant uses it
- SpotOn-branded countertop terminals, handhelds, and KDS screens
- Receipt footer "Powered by SpotOn"
- "Order with SpotOn" / SpotOn Reserve booking widgets on restaurant website
- Staff logs into terminal app branded SpotOn Restaurant

## Auth method
Two paths, both partner-gated:
1. **API key** via `x-api-key` request header (per-location scope) — Restaurant/Reserve/Enterprise APIs
2. **OAuth 2.0** via SpotOn Central API for multi-tenant partner apps

Registry currently says `auth_type: "bearer"` — **incorrect**. Must change to header-based `x-api-key` (or OAuth) before any live call attempt.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes (post-partnership) | `/orders` documented on Restaurant + Central API | Config path `/transactions` likely wrong |
| Catalog / items | Yes | `/menu/items` documented | Path naming confirmed |
| Customers | Yes | Loyalty + guest endpoints | |
| Employees | Yes | Labor endpoints | |
| Inventory | Partial | Retail product API | |
| Refunds | Yes | Payment/check endpoints | |

Base URL `https://api.spoton.com/v1` is **unverified** — actual hosts live under `developers.spoton.com` and are split per product (Restaurant, Central, Reserve, Enterprise). Treat current config as a placeholder until validated against assigned API docs.

## Partner program / access requirements
- **Partner program required:** Yes (hard gate)
- **Sign-up URL:** https://www.spoton.com/developer-center/ → "Partner Integration Intake Form"
- **Approval timeline:** Weeks to months — not self-serve. Developer reports describe 26+ days just to receive the intake form after first contact; full approval through sandbox → production app review extends well beyond that
- **Cost / revenue share:** Not publicly disclosed; negotiated per agreement

## Sandbox / test environment
- **Available:** Yes, but only after partner approval
- **URL:** Provided by SpotOn partner ops; not public
- **Notes:** Sandbox key issued first; production key only after app review passes

## Rate limits
Not publicly documented; communicated per partner agreement.

## Webhook / sync model
Hybrid — REST polling for catalog/labor; webhooks documented for order/check events on Central API.

## Connect flow (what the merchant does)
1. Merchant emails their SpotOn customer success manager or sales rep to request API access for Meridian
2. SpotOn enables API access on the merchant's listed venues
3. SpotOn issues Meridian-scoped API key (per location)
4. Merchant pastes key into Meridian connect UI, or completes OAuth handshake if Central API path

## Estimated effort to go LIVE (config → production-ready)
XL — partner agreement is the critical path. Even with engineering ready, real-world precedent suggests 4–12 weeks minimum from intake form submission.

## What blocks LIVE status today
- No SpotOn partner agreement in place
- Registry `auth_type: "bearer"` is wrong — must switch to `x-api-key` header
- Base URL `https://api.spoton.com/v1` is unverified; real hosts are product-specific under `developers.spoton.com`
- Endpoint paths in config not validated against current docs (developer portal is auth-walled — 403 without credentials)
- No customer-facing connect UI built

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401 Unauthorized → **Likely cause:** sending `Authorization: Bearer …` instead of `x-api-key` header → **Fix:** change auth scheme
- **Symptom:** 403 Forbidden on a specific restaurant ID → **Likely cause:** key not scoped to that venue → **Fix:** ask merchant's SpotOn rep to add the venue to the key
- **Symptom:** Endpoint 404 → **Likely cause:** wrong product API (Restaurant vs Reserve vs Central) → **Fix:** route by product type

## Strategic notes
SpotOn is a high-value logo — they compete head-to-head with Toast and are gaining share in mid-market hospitality. Worth the partnership effort, but treat the timeline like an enterprise sales cycle, not an integration task. Start the intake conversation now even if engineering is months out.

## Recommendation
WAIT (start partnership intake in parallel)

**Reasoning:** Public API exists and is well-documented, but every path requires partner approval — no self-serve route. Submit intake form now to start the clock, and prioritize engineering only once we have sandbox credentials and confirmed endpoint surface.

## Sources consulted
- https://developers.spoton.com/central-api/docs/getting-started
- https://developers.spoton.com/restaurant/docs/api-access
- https://developers.spoton.com/central-api/docs/spoton-oauth-integration-guide
- https://developers.spoton.com/reserve/docs/getting-started
- https://developers.spoton.com/enterprise/docs/enabling-api-access
- https://www.spoton.com/developer-center/
- Live API docs accessed: Partial (developer portal returned 403 without partner credentials; details gathered from official portal search excerpts and SpotOn help pages)
