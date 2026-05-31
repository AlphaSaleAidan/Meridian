# Lightspeed Retail (X-Series / R-Series)

> Status: **WAVE 1 BUILDING** — config is READY in registry, OAuth UI in development
> Category: retail (boutiques, specialty stores, multi-SKU shops)
> Auth: OAuth (bearer)

## What you tell the merchant

"Lightspeed Retail support is rolling out this month. I can put you on the priority list — you'll be live within 30 days. In the meantime, if you can pull a CSV export of your last 6 months of sales, we can give you a preview of the insights you'll see."

**Don't quote a hard ship date.** Use "within 30 days" or "this month."

## How the merchant connects (when live)

1. From the Meridian portal, **Settings → POS Connections → Connect Lightspeed Retail**
2. They authorize via Lightspeed's OAuth screen (account ID + scopes)
3. We pull from the V3 API at `https://api.lightspeedapp.com/API/V3/Account/{account_id}`

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Sales | hourly poll | 18 months |
| Items / catalog | daily | full history |
| Employees | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.lightspeedapp.com/API/V3/Account/{account_id}`

## What features they get (when live)

Strong retail suite — Lightspeed is built for inventory-heavy multi-SKU retail:

- Inventory Intelligence (demand forecasting by SKU)
- Basket Analysis (what sells together — merchandising insight)
- Product Velocity (dead stock detection)
- Seasonality + day-of-week patterns
- Customer LTV (Lightspeed has customer IDs)
- Pricing Power analysis
- Revenue trend + forecasting

## What features they DON'T get (yet)

- Real-time order creation (`supports_orders: False` in registry) — analytics-only for now
- Webhooks not configured in current registry — hourly poll

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Account ID not found | Wrong region (US vs EU vs AU Lightspeed) | Confirm region during onboarding |
| Slow backfill | Large catalog + V3 API rate limits | Auto-throttle |

## Sales angle

**Opener:** "Are you on Lightspeed Retail? Their built-in reports are good for what happened — we tell you what to do about it. Dead stock alerts, reorder timing, basket pairings most owners miss."

**Why Lightspeed merchants are good targets:**
- Multi-SKU operations → high data volume → richer insights → easier ROI demo
- Premium tier is natural (CA$685) because of inventory module depth
- They already pay for Lightspeed → they value software → less price resistance

## What blocks live status today

- OAuth UI in development (config side is ready in registry — `lightspeed-retail` entry)
- Pre-sell allowed; do not promise specific date

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (lightspeed-retail config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #4)_
