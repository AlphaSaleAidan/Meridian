# Cashier Live

**Registry key:** `cashier-live` — see `src/services/pos_connectors/registry.py` (`auth_type: csv_only`)

## Status
CSV ONLY — active product in 2026 (live pricing, free-trial CTA, login at `ww2.cashierlive.com`). No public developer API surfaced.

## What it is
Web-based cloud POS for small independent retail with a strong independent-pharmacy focus (also markets "CashierLive RX" for online pharmacy). Browser, iPhone, iPad clients; integrated card processing.

## Vertical & market
- **Vertical:** retail — independent pharmacy primary, general small retail secondary
- **NA presence:** Small — niche in the independent-pharmacy long tail
- **Merchant:** single-location pharmacy or small retail shop, owner-operator; US-heavy

## How to spot it
- Logs in to `ww2.cashierlive.com` in a browser (no thick client)
- iPad or PC at the counter running the web app
- Mentions PMS tie-ins (PK Software, SpeedScript, PSI, QS1) or wholesaler ordering (McKesson, Cardinal Health, AmerisourceBergen)
- Tells: "Cashier Live," "MethCheck"

## Auth method
CSV upload only. No documented public API, OAuth, or partner developer program found.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Receipt #`, `Date`, `Total`, `Product`, `Payment` |
| Catalog | Partial via CSV | Inferred from `Product` column |
| Customers / Employees / Refunds | Not configured | |
| Inventory | Not configured | Vendor advertises module; exportability unverified |

`supports_orders: False`, `sms_fallback: True` — phone agent can't push orders; SMS receipt capture is the real-time fallback.

## Partner program / access requirements
None found. No developer portal or API key issuance. Support: `support@cashierlive.com`, `(615) 398-6599`.

## Sandbox / rate limits / webhooks
None. File upload only. SMS fallback handles real-time receipts if opted in.

## Connect flow
1. Log in to Cashier Live dashboard
2. **Reports → Sales →** select date range → export CSV
3. Upload to Meridian (column mapping uses registry defaults)
4. Repeat weekly (per `frontend/src/data/pos-systems.ts`)

## Estimated effort to go LIVE
S (1–3 days) — CSV importer wiring only. As "live" as architecture permits without a vendor API.

## What blocks LIVE status today
No first-party API surfaced publicly — vendor constraint, not a Meridian gap. A private partner API would require direct outreach.

## Common failure modes
- Columns don't match → re-map; confirm `Receipt #`, `Date`, `Total` present
- Missing inventory / employees → expected; set merchant expectations
- Pharmacy Rx data absent → out of scope; lives in the PMS

## Strategic notes
Off-ICP. Meridian volume sits on Square, Clover, Toast, Shopify. Independent-pharmacy POS is a small regulated niche; the data of real value (Rx fills) lives in the PMS. CSV-only LTV is structurally limited.

## Recommendation
DEFER. Active product, off-ICP, no API path verified. Keep the CSV importer for inbound; do not prospect.

## Sources consulted
- https://cashierlive.com/ (active, pricing, login URL)
- https://cashierlive.com/pharmacy (PMS + wholesaler tie-ins; no API)
- https://www.getapp.com/customer-management-software/a/cashier-live/ (2026)
- https://www.g2.com/products/cashierlive-pharmacy-pos/reviews (2026)
- `src/services/pos_connectors/registry.py` (key: `cashier-live`)
- `frontend/src/data/pos-systems.ts` (lines 3884–3936)
- Live first-party API access: No
