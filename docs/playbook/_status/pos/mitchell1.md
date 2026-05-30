# Mitchell1

**Registry key:** `mitchell1` — see `src/services/pos_connectors/registry.py` (lines 499–514)

## Status
CSV ONLY — confirmed against vendor docs. No third-party transactional API for Manager SE.

## What it is
Mitchell1 Manager SE — Windows/SQL shop management for independent mechanical auto repair; ProDemand is the bundled OEM repair-info lookup. Snap-on-owned. Manager SE is the transactional surface (ROs, invoicing, labor, parts).

## Vertical & market
- **Vertical:** automotive — independent mechanical auto repair
- **NA presence:** Dominant in the legacy/independent segment; the incumbent Tekmetric/Shopmonkey/Shop-Ware displace
- **Merchant:** 2–8 bay independent shop, owner-operator, often 10+ years on Manager SE; US-heavy

## How to spot the merchant uses it
- Windows desktop thick client at the counter (not a browser tab)
- Owner says "Manager SE," "Mitchell," or "ProDemand for labor times"
- Stack: Accounting Link→QuickBooks, Nexpart, PartsTech, SocialCRM

## Auth method
CSV upload only. No partner-issuable API key or OAuth for Manager SE transactional data. Mitchell1's "API Request" program is gated and scoped to **ProDemand / TruckSeries** (Website UI Integration, Website Launcher, Labor Times Data API) — not RO data.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `RO Number`, `Date Closed`, `Total`, `Labor Description`, `VIN`, `Hours`, `Technician` |
| Catalog / Customers / Refunds | ✗ | Not mapped |
| Employees | Partial | Technician name via RO line |
| Inventory | ✗ | Local SQL only |

`supports_orders: False`, `sms_fallback: True` — order push impossible; SMS-collected receipts are the fallback.

## Partner program / access requirements
No program for Manager SE data integration. ProDemand has one but is the wrong product surface. ProDemand-only sign-up: `https://mitchell1.com/resources/api-request/`.

## Sandbox / test environment
None. Test against a sample CSV.

## Rate limits
N/A — file upload.

## Webhook / sync model
None. Manual or scheduled CSV drop. SMS fallback handles real-time receipts if the shop opts in.

## Connect flow (what the merchant does)
1. Manager SE: **Followup Reports** → `*MM – Create Data Export File` → filter → CSV (or **Custom Data Export** from SQL to Excel, saved as CSV)
2. Shop uploads CSV in Meridian; column mapping uses registry defaults

## Estimated effort to go LIVE
S (1–3 days) — CSV importer wiring only. As "live" as the architecture permits; no API to build.

## What blocks LIVE status today
No first-party API — vendor constraint, not a Meridian gap. Importer UX must handle the shop's manual export cadence.

## Common failure modes
- Columns don't match → re-map; confirm `RO Number`, `Date Closed`, `Total` present
- Totals low → filter excluded internal ROs / warranty → widen filter
- Missing VIN / technician → shop ran customer-summary report → re-run with RO-detail template

## Strategic notes
Off-ICP. Meridian sells F&B + retail SMBs on Square/Clover/Toast; Mitchell1 is legacy Windows auto repair. Largest installed base in the segment but a different buyer, and CSV-only LTV is structurally limited. For any future automotive push, pair with Tekmetric / Shop-Ware / Shopmonkey — Mitchell1 is the legacy-incumbent leg and hardest to instrument in real time.

## Recommendation
DEFER. Off-ICP and no API path possible (vendor constraint). Keep the CSV importer for inbound auto-shop leads already exporting from Manager SE; do not prospect.

## Sources consulted
- https://mitchell1.com/manager-se/
- https://mitchell1.com/support/web-intent/ — API Request scope
- https://mitchell1.com/resources/api-request/ — ProDemand/TruckSeries only
- https://kb.mitchell1.com/articles/id-321/ — Followup Reports CSV export
- https://kb.mitchell1.com/articles/id-200/ — Custom Data Export from SQL
- `src/services/pos_connectors/registry.py` (lines 499–514)
- Live first-party API access: No — no Manager SE API for third parties
