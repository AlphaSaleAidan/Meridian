# Dutchie POS

**Registry key:** `dutchie-pos` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP — config has wrong `base_url` (points to ecommerce, not POS)

## What it is
The dominant cannabis dispensary POS in North America (absorbed Greenbits in 2021), used by single- and multi-location licensed dispensaries for in-store checkout, METRC compliance, and inventory.

## Vertical & market
- **Primary vertical:** Cannabis dispensary (regulated retail)
- **Estimated NA market presence:** Dominant in licensed dispensary segment
- **Typical merchant profile:** Single-state or MSO (multi-state operator) licensed cannabis retailer
- **Geographic concentration:** US (state-by-state legal markets) + some Canadian provinces

## How to spot the merchant uses it
- Budtender ringing up sales on iPad with "Dutchie POS" app (often paired with a cash drawer + label printer for METRC tags)
- Online menu / order-ahead site branded "Powered by Dutchie" or hosted on `dutchie.com/embedded-menu/...`
- Receipt or compliance label references METRC package IDs
- Conversational tell: "we're on Dutchie" or "we switched from Greenbits"

## Auth method
HTTP Basic Auth — API key as username, empty password, base64-encoded in `Authorization: Basic` header. Keys are vendor-scoped and issued only via Dutchie Support after partner approval.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Config exists | `/retailers/{retailer_id}/orders` | Endpoint path unverified against live POS API |
| Catalog / items | Config exists | `/retailers/{retailer_id}/products` | Unverified |
| Customers | Config exists | `/retailers/{retailer_id}/customers` | Unverified |
| Employees | Config exists | `/retailers/{retailer_id}/employees` | Unverified |
| Inventory | Not configured | — | Likely needed for cannabis (METRC tracking) |
| Refunds | Not configured | — | |

**Config issue:** Registry has `base_url = https://plus.dutchie.com/api/v1`, but Dutchie Plus is the ecommerce/headless menu product. The documented POS API base is `https://api.pos.dutchie.com`. Endpoint paths in our registry have not been validated against either surface and likely need rewriting before any live call will succeed.

## Partner program / access requirements
- **Partner program required:** Yes — Certified Partner Program (launched Aug 2025)
- **Sign-up URL:** `https://business.dutchie.com/integrations` (vendor application via "Get Started With Dutchie" form)
- **Approval timeline:** Vendor review by Dutchie before any key issuance; merchant must then separately request a key naming our vendor via Dutchie Support — expect multi-week cycle
- **Cost / revenue share:** Not publicly documented

## Sandbox / test environment
- **Available:** Not documented publicly
- **Notes:** `/whoami` endpoint exists for auth verification once a key is issued

## Rate limits
Not publicly documented.

## Webhook / sync model
Not documented publicly — assume poll-only until confirmed with partner team.

## Connect flow (what the merchant does)
1. Meridian must first be an approved Dutchie Certified Partner
2. Merchant logs a ticket with Dutchie Support requesting an API key for Meridian, naming our integration and required scopes
3. Dutchie issues vendor-scoped key directly to merchant
4. Merchant pastes key into Meridian connect screen; we test against `/whoami` before unlocking dashboard

## Estimated effort to go LIVE
XL — partner application + endpoint rewrite + customer-facing connect UI + cannabis compliance review

## What blocks LIVE status today
- Not an approved Dutchie partner
- `base_url` in registry points to ecommerce (`plus.dutchie.com`), not POS (`api.pos.dutchie.com`)
- Endpoint paths and auth header format in registry are unvalidated against real POS API (which uses HTTP Basic, not bearer as registry currently declares)
- No cannabis compliance / banking story on Meridian side

## Common failure modes
- **Symptom:** 401 on every call → **Likely cause:** sending key as `Bearer` token → **Fix:** switch to `Authorization: Basic base64(key + ":")`
- **Symptom:** 404 on `/retailers/...` paths → **Likely cause:** wrong base URL → **Fix:** point to `api.pos.dutchie.com` and revalidate paths against Swagger
- **Symptom:** "Vendor not approved" rejection from Dutchie Support → **Fix:** complete Certified Partner application before merchant requests key

## Strategic notes
Cannabis is a high-revenue-per-merchant vertical (dispensaries process millions/yr in cash-heavy transactions and have weak in-house analytics), but it carries vertical-specific cost: no national banking, federal Schedule I status, state-by-state licensing for Meridian if we touch payments, and ad-platform restrictions on outbound marketing. Dutchie's gatekeeping is real — they actively reject vendors they consider redundant with their first-party analytics. A rep should not promise a Dutchie merchant a live connection today.

## Recommendation
DEFER — unless Meridian commits to cannabis as a named vertical.

**Reasoning:** Dutchie is the right integration to own the dispensary segment, but going live requires a Certified Partner application, a corrected connector, and a deliberate cannabis go-to-market (compliance, banking, marketing). Without that commitment, the registry entry should be marked NEEDS PARTNERSHIP and reps should not pitch Dutchie merchants.

## Sources consulted
- https://api.pos.dutchie.com/ (Dutchie POS API docs)
- https://api.pos.dutchie.com/pages/authentication.html (auth specifics, live)
- https://api.pos.dutchie.com/pages/openapi.html (OpenAPI / Swagger reference)
- https://support.dutchie.com/hc/en-us/articles/27660267271187 (API key request process — 403 on fetch, referenced via search)
- https://business.dutchie.com/integrations (partner program landing)
- https://business.dutchie.com/greenbits (Greenbits → Dutchie consolidation)
- Live API docs accessed: Yes (authentication page); partial elsewhere
