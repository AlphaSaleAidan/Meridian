# Korona POS

> Status: **WAVE 1 BUILDING** — config is READY in registry, connect UI in development
> Category: retail (specialty retail, multi-location, wine/spirits common)
> Auth: Basic auth

## What you tell the merchant

"Korona support is rolling out this month. You'll connect with your Korona Cloud account credentials — same login you use for the admin panel. We import 18 months of receipts and start insights within 24 hours of connect."

## How the merchant connects (when live)

1. From the Meridian portal, **Settings → POS Connections → Connect Korona**
2. They enter their Korona Cloud account ID + admin username + password (basic auth)
3. We test against `/web/api/v3/accounts/{account_id}` and start the receipt backfill

Typical time to connect (projected): **2 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Receipts (transactions) | hourly poll | 18 months |
| Products (catalog) | daily | full history |
| Cashiers (employees) | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.koronacloud.com/web/api/v3/accounts/{account_id}`

## What features they get (when live)

Strong fit for specialty retail:

- Product Velocity (which SKUs move, which are dead)
- Inventory Intelligence (reorder point predictions)
- Basket Analysis (especially valuable for wine/spirits cross-sell)
- Revenue trend + forecasting
- Cashier-level performance comparison
- Customer LTV (where customer accounts exist)
- Seasonality patterns

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Real-time push (hourly poll)

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Auth rejected | Account uses 2FA on Korona Cloud login | Generate an API-only user without 2FA |
| Backfill slow | Receipt volume + rate limits | Expected for high-volume stores |

## Sales angle

**Opener:** "Are you on Korona? You've got receipt-level data most POSes don't expose cleanly — we use that for SKU-level demand forecasting. Most wine/spirits and specialty retail merchants find CA$2K+/mo in over-ordering they can stop."

**Best verticals on Korona:** wine/spirits/liquor, specialty grocery, gift stores, multi-SKU retail.

## What blocks live status today

- Connect UI in development (config side ready in registry)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (korona-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #5)_
