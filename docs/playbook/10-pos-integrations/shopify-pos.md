# Shopify POS

> Status: **WAVE 1 BUILDING** — current registry pins API version `2024-01` (legacy); GraphQL migration planned
> Category: retail (omnichannel — physical + online)
> Auth: API key (X-Shopify-Access-Token header)

## What you tell the merchant

"Shopify POS connection is rolling out this month. You'll install Meridian from the Shopify app store, approve access, and we'll pull both your in-store and online orders together — full unified view. First insights within 24 hours."

## How the merchant connects (when live)

1. In Meridian: **Settings → Integrations → Connect Shopify**, merchant enters their `<shop>.myshopify.com` domain
2. Redirected to Shopify; signs into the store admin
3. Reviews requested scopes (`read_orders`, `read_products`, `read_customers`, `read_inventory`) → clicks **Install app**
4. Redirected back to Meridian with offline access token stored; backfill starts (catalog → customers → orders → inventory)

Typical time to connect (projected): **2 minutes** (Shopify app install is one-click).

**Partner program:** free Shopify Partners account at https://partners.shopify.com — self-service signup is instant. **Custom apps** (per-merchant, installed from the merchant's admin) ship same day and skip the App Store review. **Public app** on the Shopify App Store requires Shopify review (typically 2–6 weeks). For pilot/single-merchant deals, ship a custom app; reserve the public listing for scaled distribution.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders (POS + online) | hourly poll → webhooks (planned) | 18 months |
| Products | daily | full history |
| Users (staff) | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://{shop_domain}/admin/api/2024-01` (legacy REST — migrating to GraphQL)

## What features they get (when live)

Shopify merchants get the omnichannel cross-view — almost nobody else gives them this:

- Online vs in-store revenue split
- Inventory Intelligence across both channels
- Customer LTV unified across web + POS
- Basket analysis (online basket vs in-store basket — different patterns)
- Product velocity
- Revenue forecasting (with channel breakouts)
- Discount/promo ROI

## What features they DON'T get

- Marketing attribution (UTM-level) — Shopify ad attribution lives elsewhere; we ingest order data only
- Real-time alerts (hourly poll until webhooks ship)

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `406 Not Acceptable` or "Unsupported API version" | Our registry pins `2024-01`, which is past Shopify's 12-month support window | Engineering bumping to current stable + planning GraphQL migration |
| `401 Invalid API key or access token` | Merchant uninstalled the app, or token rotated | Prompt re-install; subscribe to `app/uninstalled` webhook to detect proactively |
| Missing POS-only orders | Query pulled all orders without source filter | Filter `source_name=pos` (vs `web`, `shopify_draft_order`) |
| 429 + `Retry-After` header | Burst over the leaky-bucket limit (40 standard / 80 Plus) | Honor header; throttle to 2 req/sec standard, 4 req/sec on Plus |

### Edge cases we expect but haven't seen yet
- Missing online orders because merchant has multiple separate Shopify admins (multi-store) — connect each shop domain separately.

## Sales angle

**Opener:** "Are you on Shopify POS? You've got two stores in one — the website and the physical register — but most owners run them like separate businesses. We unify them. Same customer LTV, same inventory view, both channels."

**Why Shopify merchants are high-value:**
- Omnichannel is a real wedge — competitors don't unify well
- Higher AOV than pure-POS retail → bigger commission per close
- Comfortable with subscriptions (already pay Shopify monthly)

**Why this is the wedge:** Shopify POS and Shopify online checkout share one Admin API — same OAuth covers both. A merchant selling online and in-store gets unified analytics from a single connect (filter `source_name=pos` for in-store, `source_name=web` / `shopify_draft_order` for online). Lead with this for omnichannel prospects: Meridian becomes their single source of truth across channels. POS attach is highest among omnichannel retailers and DTC brands opening physical retail; growing in F&B (specialty coffee, bakeries, quick-serve).

## What blocks live status today

- **REST `2024-01` is out of support** — bump to current stable (`2026-04` at time of writing) or migrate to GraphQL Admin API (recommended for longevity, since REST is now "legacy" as of 2024-10-01 and new public apps must use GraphQL since 2025-04-01)
- **No customer-facing OAuth install flow** built in Meridian UI
- **No webhook subscription / verification code** yet (HMAC-SHA256 with app secret) — `orders/create`, `orders/updated`, `orders/paid`, `inventory_levels/update`, `app/uninstalled`
- **Inventory + refunds endpoints** not in registry yet (`inventory_levels.json`, `orders/{id}/refunds.json`)
- For App Store distribution, app must pass Shopify review; **custom apps unblock pilot merchants immediately**
- Estimated effort to LIVE: **1–2 weeks** for REST bump + OAuth UI + webhooks; **1+ month** for full GraphQL migration

## Reference docs

- Admin API: https://shopify.dev/docs/api/admin
- REST legacy notice (2024-10-01): https://shopify.dev/docs/api/admin-rest
- Versioning policy (12-month window): https://shopify.dev/docs/api/usage/versioning
- Partner signup: https://partners.shopify.com

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (shopify-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #6) + docs/playbook/_status/pos/shopify-pos.md (Phase 1)_
