# Lightspeed Retail (X-Series / R-Series)

> Status: **WAVE 1 BUILDING** — config is READY in registry, OAuth UI in development
> Category: retail (boutiques, specialty stores, multi-SKU shops)
> Auth: OAuth (bearer)

## What you tell the merchant

"Lightspeed Retail support is rolling out this month. I can put you on the priority list — you'll be live within 30 days. In the meantime, if you can pull a CSV export of your last 6 months of sales, we can give you a preview of the insights you'll see."

**Don't quote a hard ship date.** Use "within 30 days" or "this month."

## How the merchant connects (when live)

1. From the Meridian portal, **Settings → POS Connections → Connect Lightspeed Retail**
2. They authorize via Lightspeed's OAuth screen at `https://cloud.lightspeedapp.com/oauth/authorize.php`
3. Meridian exchanges the code for refresh + access token (access token expires in 30 min; refresh token is long-lived)
4. Meridian calls `GET /Account.json` (no account_id needed) to auto-discover the merchant's numeric `account_id`
5. We pull from the V3 API at `https://api.lightspeedapp.com/API/V3/Account/{account_id}`

Typical time to connect (projected): **3 minutes**. **Merchants never look up their account ID manually** — we discover it automatically.

**No partner program required** for basic API access — credentials are self-service at `https://cloud.lightspeedapp.com/oauth/register.php`. Marketplace listing (separate, optional) requires contacting [email protected].

**Disambiguation:** Lightspeed sells two retail products. Our config targets **R-Series** (original Lightspeed Retail, still actively sold). **X-Series** (formerly Vend, acquired 2021) uses a different host (`x-series-api.lightspeedhq.com`) and needs a separate connector. A merchant saying "Lightspeed" might mean R-Series, X-Series, Restaurant (K-Series), or Golf — always confirm before quoting integration timing.

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

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| 429 errors during initial backfill | Leaky bucket: 90-req burst (+10 per register beyond first); drip rate 1 req/sec (+0.5/sec per extra register). Some endpoints cost >1 drip | Respect `X-LS-API-Bucket-Level` response header, back off when >80%. Required ≥1s backoff on 429 |
| Empty Sale responses | Missing `?load_relations=["SaleLines","SalePayments"]` query param | Add load_relations to default Sale query |
| Auth works but all calls return 404 | R-Series merchant being routed through X-Series connector (or vice versa) | Ask merchant which product they're on **before** connecting |
| Refresh token rejected after long idle | Merchant revoked app in Lightspeed back-office | Prompt reconnect |

### Edge cases we expect but haven't seen yet
- Account ID not found — wrong region (US vs EU vs AU Lightspeed). Confirm region during onboarding.
- Slow backfill — large catalog + V3 API rate limits. Auto-throttle.

## Sales angle

**Opener:** "Are you on Lightspeed Retail? Their built-in reports are good for what happened — we tell you what to do about it. Dead stock alerts, reorder timing, basket pairings most owners miss."

**Why Lightspeed merchants are good targets:**
- Multi-SKU operations → high data volume → richer insights → easier ROI demo
- Premium tier is natural (CA$685) because of inventory module depth
- They already pay for Lightspeed → they value software → less price resistance

**Why this is the wedge:** Lightspeed Retail merchants are high-value Meridian targets — above-average AOV, multi-channel (often have ecom + physical), and they use Lightspeed's reporting heavily, so they already understand analytics ROI. Pitch is "go beyond Lightspeed Insights" with cross-location benchmarking and AI Q&A. Top-3 specialty retail POS alongside Square and Shopify; typical merchant is a 1–10 location boutique, bike shop, sporting goods, pet store, jewelry, CBD/smoke shop, or gift shop.

**Watch out:** X-Series (formerly Vend) adoption is growing because Lightspeed is actively migrating Vend customers — expect inbound asks. X-Series connector is a separate follow-up.

## What blocks live status today

- **No customer-facing OAuth UI** in Meridian's connect flow
- **No `/Account.json` discovery step** in connector (current config hardcodes `{account_id}` template)
- **No webhook handler** (poll-only is acceptable for v1; Sale/Item/Customer event webhooks are supported by Lightspeed)
- **`supports_orders: false` is intentional** — R-Series Sale creation requires SaleLine + Payment children; v2 work
- Estimated effort to LIVE: **1–2 weeks** (register OAuth app, build connect UI + callback, add `/Account.json` discovery, smoke-test pagination + rate-limit backoff)
- Pre-sell allowed; do not promise specific date

## Reference docs

- API introduction: https://developers.lightspeedhq.com/retail/introduction/introduction/
- Rate limits (leaky bucket): https://developers.lightspeedhq.com/retail/introduction/ratelimits/
- Authentication overview: https://developers.lightspeedhq.com/retail/authentication/authentication-overview/
- Developer signup / OAuth app registration: https://cloud.lightspeedapp.com/oauth/register.php
- Product page: https://www.lightspeedhq.com/pos/retail/

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (lightspeed-retail config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #4) + docs/playbook/_status/pos/lightspeed-retail.md (Phase 1)_
