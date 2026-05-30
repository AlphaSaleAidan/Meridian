# Harbortouch

**Registry key:** `harbortouch` — see `src/services/pos_connectors/registry.py` (lines 416–429)

## Status
CSV ONLY — accurate. Shift4 has rebranded Harbortouch to SkyTab; `harbortouch.com/developers` now redirects to SkyTab. No first-party Harbortouch API is being developed; back-office is Lighthouse BMS with CSV/report export. Same Shift4-consolidation dynamic as Revel.

## What it is
Legacy multi-vertical POS (restaurant, bar, retail, salon) sold for years under the "free POS" hardware-bundled model. Acquired by Shift4 in 2017; brand wind-down to SkyTab is effectively complete in 2026, with a further rebrand of SkyTab → "Shift4 Dine" announced for May 2026.

## Vertical & market
- **Primary vertical:** multi-vertical (restaurant-heavy, plus bar, retail, salon)
- **NA presence:** Medium installed base, shrinking — actively migrating to SkyTab
- **Typical merchant:** independent SMB restaurant / bar / small retail, often original "free terminal" lease customer
- **Geo:** US-dominant

## How to spot the merchant uses it
- Older Harbortouch-branded terminal (Elo-style touchscreen) still on the counter
- Owner says "Harbortouch" or "Lighthouse" (the back office)
- Receipts: "Powered by Harbortouch" or "Shift4 Payments"; some sites already swapped to SkyTab-branded receipts mid-migration

## Auth method
CSV upload only. No customer-issuable API key / OAuth for Harbortouch transactional data. Third-party integrations historically went through partner-only Shift4 channels (Lighthouse BMS exports + 1-way partner feeds).

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Trans #`, `Date/Time`, `Amount`, `Description`, `Tender` |
| Catalog | ✗ | Not mapped |
| Customers | ✗ | Not mapped |
| Employees | ✗ | Not mapped |
| Inventory | ✗ | Lighthouse-internal |
| Refunds | ✗ | Inferred from `Amount` sign only |

`supports_orders: False`, `sms_fallback: True` — no order push; SMS-collected receipts handle real-time.

## Partner program / access requirements
No public Harbortouch developer program. The former `harbortouch.com/developers` page now redirects to SkyTab; any partner conversation is the Shift4 Dine partner track (see `skytab.md`).

## Sandbox / test environment
None. Test against a sample Lighthouse CSV export.

## Rate limits
N/A — file upload.

## Webhook / sync model
None. Manual or scheduled CSV drop from Lighthouse. SMS fallback for real-time receipts if the merchant opts in.

## Connect flow (what the merchant does)
1. Lighthouse BMS → reports / exports → transaction CSV
2. Upload CSV in Meridian; registry column map handles `Trans #` / `Date/Time` / `Amount` / `Description` / `Tender`

## Estimated effort to go LIVE
S (1–3 days) — CSV importer is the ceiling; no API path to build.

## What blocks LIVE status today
No first-party Harbortouch API; vendor is sunsetting the brand into SkyTab. Any deeper integration must be pursued under the SkyTab / Shift4 Dine partner track, not Harbortouch.

## Common failure modes
- Columns don't match → Lighthouse export profile differs by vertical → re-map to `Trans #` / `Date/Time` / `Amount` / `Tender`
- Totals look low → tip/refund split varies by export template → re-export with "detailed" template
- Merchant already on SkyTab hardware → route to `skytab.md` connect flow, not this one

## Strategic notes
Same playbook as Revel: Shift4 is consolidating acquired POS brands into SkyTab (soon Shift4 Dine). Harbortouch is further along the sunset curve than Revel. Treat any inbound Harbortouch merchant as a SkyTab migration in flight — land them on Meridian via CSV now so historical data survives the platform switch.

## Recommendation
DEFER — route to SkyTab path.

**Reasoning:** Brand is being phased out into SkyTab/Shift4 Dine; no Harbortouch-specific API will ever ship. Keep the CSV importer for inbound; do not prospect Harbortouch as a category.

## Sources consulted
- https://www.harbortouch.com/developers (redirects to SkyTab — confirms brand wind-down)
- https://www.shift4dinepartners.us/harbortouch/ — official Harbortouch → Shift4 Dine transition page
- https://www.posusa.com/harbortouch-pos-review/ — "Now SkyTab" 2026 review
- https://www.posusa.com/skytab-pos-review/ — SkyTab → Shift4 Dine rebrand May 2026
- https://kb.7shifts.com/hc/en-us/articles/4417519900563-Harbortouch-POS — 7shifts lists it as "Skytab (Harbortouch)"
- `src/services/pos_connectors/registry.py` lines 416–429
- Live first-party Harbortouch API access: No — none exists; partner path is SkyTab
