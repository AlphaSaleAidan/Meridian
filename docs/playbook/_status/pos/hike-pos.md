# Hike POS

**Registry key:** `hike-pos` — see `src/services/pos_connectors/registry.py` (line 679)

## Status
UNCERTAIN — registry says `auth_type: bearer`, but Hike's published developer docs describe **OAuth 2.0** (developer key + per-merchant OAuth grant). Config likely works against an end-user-issued token but won't scale to multi-merchant onboarding without an OAuth flow. Treat as **NEEDS PARTNERSHIP** (developer registration) before LIVE.

## What it is
Australian-founded cloud retail POS (iPad + browser) for SMB specialty retail — apparel, footwear, lifestyle, homewares; strong matrix-variant + multi-location inventory story.

## Vertical & market
- **Primary vertical:** retail — apparel/clothing, footwear, gift, homewares, sporting goods
- **NA market presence:** Small (footprint concentrated AU/NZ; US/CA resellers exist but limited brand awareness vs. Lightspeed Retail / Shopify POS)
- **Typical merchant:** 1–5 location specialty retailer; iPad-based checkout; Shopify/BigCommerce/WooCommerce omnichannel
- **Geography:** Global; HQ Australia, partners listed for AU/NZ/US/CA/UK

## How to spot the merchant uses it
- iPad POS app branded "Hike"; back-office at `*.hikeup.com`
- Receipt or email footer: "Powered by Hike" / "Hike POS"
- Integrations stack: QuickBooks Online, Xero, MYOB + Shopify/BigCommerce/WooCommerce/Neto
- Tell: "we run Hike on iPads" or "Hike syncs to our Shopify"

## Auth method
**OAuth 2.0** per Hike developer docs (app registered in Partner Dashboard → `Developer_key` → OAuth grant per merchant). Registry currently encodes a static `bearer` token — fine for a single hand-issued token, insufficient for production multi-tenant onboarding.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | yes (read) | `/api/v1/sales` | `supports_orders: false` — read-only |
| Catalog / items | yes | `/api/v1/products` | variants/matrix supported by Hike |
| Customers | yes | `/api/v1/customers` | |
| Employees | missing | — | not in registry |
| Inventory | missing | — | add stock/locations endpoint |
| Refunds | likely via `/sales` | `/api/v1/sales` | confirm in API ref |

Test endpoint: `/api/v1/stores`. Data envelope key: `data`.

## Partner program / access requirements
- **Developer registration:** self-service at `developer.hikeup.com` (OAuth keys generated in Partner Dashboard).
- **Reseller/ISV partner program:** Referrer (free, $200/signup) or Reseller ($299, 20% rev share) — not required for API access, but the path for co-marketing.
- **Approval timeline:** self-service dev signup; reseller "instant conditional approval."
- **Cost / rev share:** API access free; reseller 20% rev share if pursued.

## Sandbox / test environment
**Not documented publicly.** Test against a live trial tenant or a partner-provided account; confirm with Hike developer support before LIVE.

## Rate limits
**60 requests/min** per account; single POST payload cap **4 MB** (unlimited elements within that size).

## Webhook / sync model
**Not publicly documented.** Assume **poll-only** until verified via developer docs (`docs.hikeup.com`). Use incremental `/sales` polls keyed on updated-at.

## Connect flow (what the merchant does)
1. Click "Connect Hike" (UI TBD)
2. Redirect to Hike OAuth consent at `developer.hikeup.com` / merchant tenant
3. Merchant authorizes Meridian app; Hike returns auth code → exchange for access token
4. Meridian stores token, polls `/api/v1/sales` on schedule, honoring 60 req/min cap

## Estimated effort to go LIVE
**M (1–2 weeks):** self-service dev registration, build OAuth redirect handler, swap registry from static bearer to OAuth token store, add inventory/employees endpoints, verify webhook availability, paginated `/sales` poller with rate-limit backoff.

## What blocks LIVE status today
- Registry `auth_type: bearer` does not match documented OAuth 2.0 flow — no multi-tenant onboarding
- No connect UI / OAuth callback handler
- Sandbox + webhook support unconfirmed
- Inventory and employees endpoints missing from config

## Common failure modes
- **HTTP 401** mid-sync → token expired/revoked → re-run OAuth refresh
- **HTTP 429** → 60 req/min cap → back off, queue
- **HTTP 413 / payload error on POST** → exceeded 4 MB request → chunk

## Strategic notes
Hike is a credible SMB apparel/specialty retail POS but its NA footprint is small relative to Lightspeed Retail, Shopify POS, and Square for Retail — the platforms Meridian's NA ICP already runs. Off-ICP for current NA pipeline. If a multi-location apparel prospect with AU/NZ stores appears, Hike becomes a tie-breaker integration. The registry config is close enough that a 1–2 week sprint can ship it on demand.

## Recommendation
**DEFER** — off-ICP for NA. Revisit on first inbound apparel/lifestyle prospect that names Hike or has AU/NZ locations.

**Reasoning:** Auth mismatch (bearer vs OAuth) + unconfirmed sandbox/webhooks + small NA footprint make this a low-ROI build today; effort is M and well-scoped when demand materializes.

## Sources consulted
- https://developer.hikeup.com/
- https://docs.hikeup.com/ , /reference/rate-limit , /reference/authorization-1
- https://hikeup.com/au/partners/
- Registry config: `src/services/pos_connectors/registry.py` (line 679)
- Live API docs accessed: Partial (developer landing + rate-limit page reachable; reference pages 403 to anonymous fetch — verified via cached search snippets)
