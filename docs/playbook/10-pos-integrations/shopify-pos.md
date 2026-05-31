# Shopify POS

> Status: **WAVE 1 BUILDING** — current registry pins API version `2024-01` (legacy); GraphQL migration planned
> Category: retail (omnichannel — physical + online)
> Auth: API key (X-Shopify-Access-Token header)

## What you tell the merchant

"Shopify POS connection is rolling out this month. You'll install Meridian from the Shopify app store, approve access, and we'll pull both your in-store and online orders together — full unified view. First insights within 24 hours."

## How the merchant connects (when live)

1. Shopify admin → **Apps → Add Meridian**
2. Approve the install (scopes: read_orders, read_products, read_customers, read_users)
3. We receive the shop domain + access token, start backfill against `/admin/api/2024-01/`

Typical time to connect (projected): **2 minutes** (Shopify app install is one-click).

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

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Unsupported API version` warning | We're on `2024-01` which Shopify deprecates over time | Engineering bumping API version this wave |
| Missing online orders | Merchant has separate Shopify admin (multi-store) | Connect each shop domain separately |

## Sales angle

**Opener:** "Are you on Shopify POS? You've got two stores in one — the website and the physical register — but most owners run them like separate businesses. We unify them. Same customer LTV, same inventory view, both channels."

**Why Shopify merchants are high-value:**
- Omnichannel is a real wedge — competitors don't unify well
- Higher AOV than pure-POS retail → bigger commission per close
- Comfortable with subscriptions (already pay Shopify monthly)

## What blocks live status today

- API version bump from legacy `2024-01` → current stable
- GraphQL migration plan (REST is being deprecated by Shopify in stages)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (shopify-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #6)_
