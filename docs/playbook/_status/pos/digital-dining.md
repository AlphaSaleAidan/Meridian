# Digital Dining

**Registry key:** `digital-dining` — see `src/services/pos_connectors/registry.py` (lines 457–470)

## Status
CSV ONLY — registry `auth_type: "csv_only"`, `supports_orders: False`, `sms_fallback: True`.

## What it is
Long-established Windows-based restaurant POS (table-service heritage; FOH/BOH, server banking, gift/loyalty). Owned by Heartland / Global Payments.

## Vertical & market
- **Vertical:** restaurant — full-service / table-service
- **NA presence:** Medium and shrinking — mature base, displaced by Toast, SpotOn, Heartland Restaurant, Aloha
- **Merchant:** single-location and small-chain operators, often 10+ years on the platform; US-heavy
- **Hardware:** on-prem Windows terminals, local DB

## How to spot the merchant uses it
- Windows thick client at host stand / server stations (not iPad / browser)
- Owner says "Digital Dining" or "DD"; may reference Heartland post-acquisition
- Payments typically through Heartland / Global Payments

## Auth method
CSV upload only. No partner-issuable API key or OAuth surface configured.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Ticket #`, `Date`, `Total`, `Menu Item`, `Pay Type` |
| Catalog / items | Partial | Item names via `Menu Item` per ticket row |
| Customers / Employees / Inventory / Refunds | ✗ | Not mapped |

Order push impossible; SMS fallback handles real-time receipts.

## Partner program / access requirements
Not configured. Any API path would route through Heartland / Global Payments' partner program, not a Digital Dining-specific endpoint — unverified.

## Sandbox / test environment / rate limits / webhooks
None / sample CSV / N/A (file upload) / none. Manual or scheduled CSV export from the Windows back office.

## Connect flow (what the merchant does)
1. Back-office reporting: run a ticket / sales detail report for the date range
2. Export CSV with `Ticket #`, `Date`, `Total`, `Menu Item`, `Pay Type`
3. Upload in Meridian; mapping uses registry defaults

## Estimated effort to go LIVE
S (1–3 days) for the CSV importer — the architectural ceiling. An API path would be XL (Heartland partnership scope, unverified).

## What blocks LIVE status today
No first-party API wired. Real-time integration depends on a Heartland / Global Payments partnership not validated for Digital Dining specifically.

## Common failure modes
- Columns don't match → re-map; confirm `Ticket #`, `Date`, `Total`
- Totals low → widen filter (voids/comps excluded, single revenue center)
- Item rollup wrong → re-export at ticket-detail granularity

## Strategic notes
Heartland cross-sells newer Heartland Restaurant / Toast / SpotOn over Digital Dining. Installed base skews older operators slow to switch — useful for inbound, poor outbound target. If we ever pursue Heartland-portfolio API access, treat Digital Dining as one SKU under that umbrella.

## Recommendation
DEFER. CSV-only by current config; any API path is gated by an unverified Heartland partnership. Keep the importer for inbound merchants already exporting; do not prospect.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 457–470) — `digital-dining` entry
- Internal precedent: `mitchell1.md` and other CSV-ONLY DEFER entries
- Live first-party API access: No
