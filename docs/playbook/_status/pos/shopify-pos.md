# Shopify POS

**Registry key:** `shopify-pos` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN — config targets REST Admin API `2024-01`, which is well past Shopify's 12-month support window. REST is now "legacy" (as of 2024-10-01) and new public apps must use GraphQL Admin API (since 2025-04-01). Endpoints likely still respond but are unsupported; migration plan required before we list this as LIVE.

## What it is
Shopify's in-store point of sale running on Shopify POS Go, iPad, and dedicated hardware, fully integrated with the merchant's Shopify online store — same catalog, inventory, customers, and Admin API surface as the e-commerce backend.

## Vertical & market
- **Primary vertical:** retail (also growing in food & beverage, especially specialty coffee, bakeries, and quick-serve)
- **Estimated NA market presence:** Large — Shopify is one of the dominant SMB commerce platforms; POS attach is highest among omnichannel retailers and DTC brands opening physical retail
- **Typical merchant profile:** Omnichannel retailer with an existing Shopify online store opening a flagship/pop-up, or a multi-location boutique using Shopify POS Pro
- **Geographic concentration:** Global (US, CA, UK, AU heaviest)

## How to spot the merchant uses it
- Shopify POS Go handheld (black bar-shaped reader with screen) or Shopify-branded card reader docked to an iPad
- Merchant logs in at `<shop>.myshopify.com/admin` or `admin.shopify.com`
- Receipt footer often reads "Powered by Shopify" with a `shop.app` or `<shop>.myshopify.com` URL
- Conversational tells: "my Shopify store," "Shopify Plus," "POS Pro," "the same catalog as our website"

## Auth method
OAuth 2.0 via a Shopify app install. Merchant approves scopes, Shopify returns an offline access token, and we send it as `X-Shopify-Access-Token` on every Admin API call. Custom apps (single-merchant, installed from the Shopify admin) skip the App Store review path and produce the same token.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `GET /admin/api/2024-01/orders.json` | Both POS and online orders flow through here; filter by `source_name=pos` to isolate in-store |
| Catalog / items | Yes | `GET /admin/api/2024-01/products.json` | Shared with online store |
| Customers | Yes | `GET /admin/api/2024-01/customers.json` | |
| Employees | Configured | `GET /admin/api/2024-01/users.json` | Shopify Plus only on REST; non-Plus shops 403 |
| Inventory | Not in config | — | Available via `inventory_levels.json`; needs adding |
| Refunds | Not in config | — | Available via `orders/{id}/refunds.json`; needs adding |

## Partner program / access requirements
- **Partner program required:** Yes for distribution — free Shopify Partners account
- **Sign-up URL:** https://partners.shopify.com
- **Approval timeline:** Self-service partner account is instant. **Custom app** (per-merchant) ships same day. **Public app** on the Shopify App Store requires review (typically 2–6 weeks)
- **Cost / revenue share:** Free to build; App Store listings carry Shopify's standard 0%/15%/20% revenue share tiers (custom apps avoid this entirely)

## Sandbox / test environment
- **Available:** Yes
- **URL:** Free Shopify Partners development stores via Partner Dashboard (`partners.shopify.com → Stores → Add store → Development store`)
- **Notes:** Dev stores are fully featured, can install draft apps, cannot transact real money

## Rate limits
REST Admin API: **2 req/sec** sustained, leaky-bucket up to **40 req burst** (standard); **4 req/sec / 80 burst** on Shopify Plus. GraphQL uses a cost-based budget (1000 points/app/shop refilling at 50/sec). Respect `X-Shopify-Shop-Api-Call-Limit` header and back off on HTTP 429.

## Webhook / sync model
Hybrid recommended. Shopify webhooks (`orders/create`, `orders/updated`, `orders/paid`, `inventory_levels/update`, `app/uninstalled`) for real-time, plus periodic incremental poll using `updated_at_min`. We are currently poll-only — webhook subscription not yet wired.

## Connect flow (what the merchant does)
1. In Meridian: **Settings → Integrations → Connect Shopify**
2. Merchant enters their `<shop>.myshopify.com` domain
3. Redirected to Shopify; signs into the store admin
4. Reviews requested scopes (`read_orders`, `read_products`, `read_customers`, `read_inventory`) → clicks **Install app**
5. Redirected back to Meridian with offline access token stored; backfill starts (catalog → customers → orders → inventory)

## Estimated effort to go LIVE
**M (1–2 weeks)** — bump API version, build OAuth UI, register webhooks. **L (1+ months)** if we also migrate to GraphQL Admin API (recommended for longevity).

## What blocks LIVE status today
- REST `2024-01` is out of support — bump to current stable (`2026-04` at time of writing) or migrate to GraphQL Admin API
- No customer-facing OAuth install flow built in Meridian UI
- No webhook subscription / verification code yet (HMAC-SHA256 with app secret)
- For App Store distribution, app must pass Shopify review; custom apps unblock pilot merchants immediately

## Common failure modes (for troubleshooting playbook)
- **Symptom:** `406 Not Acceptable` or "Unsupported API version" → **Cause:** version path stale → **Fix:** bump `base_url` to current stable
- **Symptom:** `401 Invalid API key or access token` → **Cause:** merchant uninstalled the app, or token rotated → **Fix:** prompt re-install; subscribe to `app/uninstalled` webhook to detect proactively
- **Symptom:** Missing POS-only orders → **Cause:** querying all orders without source filter → **Fix:** filter `source_name=pos` (vs `web`, `shopify_draft_order`)
- **Symptom:** 429 + `Retry-After` → **Cause:** burst over 40 calls → **Fix:** honor header, throttle to 2 req/sec

## Strategic notes
Distinguish two surfaces sharing one Admin API: **Shopify POS** (in-store, `source_name=pos`) vs **Shopify online checkout** (`source_name=web` / `shopify_draft_order`). Same OAuth covers both — a merchant selling online and in-store gets unified analytics from a single connect. Lead with this for omnichannel prospects: Meridian becomes their single source of truth across channels. For pilot/single-merchant deals, ship a **custom app** to skip App Store review; reserve the public listing for scaled distribution.

## Recommendation
BUILD NOW (after version bump) — Shopify's install base in retail is too large to skip, and the integration path is well-understood. Plan the GraphQL migration as a follow-up so we're not rebuilding in 12 months when REST loses more surface area.

**Reasoning:** Huge TAM in retail and growing in F&B, self-serve OAuth, no partner gate for custom apps. Only real risk is leaning on the legacy REST API — fix that first.

## Sources consulted
- https://shopify.dev/docs/api/admin
- https://shopify.dev/docs/api/admin-rest (REST legacy notice, 2024-10-01)
- https://shopify.dev/docs/api/usage/versioning (12-month support window)
- `src/services/pos_connectors/registry.py` (key: `shopify-pos`)
- Live API docs accessed: Yes
