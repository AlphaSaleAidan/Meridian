# AccuPOS

**Registry key:** `accu-pos` — see `src/services/pos_connectors/registry.py` (lines 729–742)

## Status
CSV ONLY — `auth_type: csv_only`, `supports_orders: False`, `sms_fallback: True`. No real-time API wired.

## What it is
Windows POS for small retail and restaurants, sold on tight bidirectional sync with QuickBooks (Desktop/Online) and Sage 50/100. Accounting is the headline, not the POS surface.

## Vertical & market
- **Primary vertical:** multi-vertical (registry `category: multi_vertical`) — small retail + small restaurant/bar
- **Estimated NA market presence:** Small — niche, accountant-led selection
- **Typical merchant profile:** single-location independent already running QuickBooks or Sage; owner picked the POS because the bookkeeper asked for it
- **Geographic concentration:** US / Canada

## How to spot the merchant uses it
- Windows touchscreen terminal (not iPad, not browser tab)
- Owner says "it syncs to QuickBooks" or "my accountant set it up"
- AccuPOS or AccuShift branding on the till; AccuCOUNT for inventory

## Auth method
CSV upload only. No public REST/OAuth for third parties; integrations are accounting-bridge (QB/Sage), not a partner-app surface.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Transaction ID`, `Date`, `Total`, `Description`, `Payment Method` |
| Catalog / Customers / Employees / Refunds | ✗ | Not mapped |
| Inventory | ✗ | Lives in AccuCOUNT / accounting |

## Partner program / access requirements
None known for transactional API access. Sales/reseller program exists but is not a developer surface.

## Sandbox / test environment
None. Validate against a sample export.

## Rate limits
N/A — file upload.

## Webhook / sync model
None. Manual CSV export, or SMS fallback for real-time receipts if the merchant opts in (`sms_fallback: True`).

## Connect flow (what the merchant does)
1. In AccuPOS back office, run a sales/transactions report for the period
2. Export to CSV
3. Upload in Meridian; registry default column map applies

## Estimated effort to go LIVE
S (1–3 days) — CSV importer wiring only. No API path to build against.

## What blocks LIVE status today
Vendor constraint: no third-party transactional API. Not a Meridian gap.

## Common failure modes
- Columns don't match → re-map; confirm `Transaction ID`, `Date`, `Total` present
- Totals look low → report scoped to one register / one shift → re-export at store level
- `Payment Method` blank → older AccuPOS build → fall back to SMS-collected receipts

## Strategic notes
Off-ICP for Meridian's Square/Clover/Toast SMB focus. Center of gravity is the accountant, not the POS — any pitch competes with QuickBooks-native dashboards the bookkeeper already trusts. Small installed base caps LTV.

## Recommendation
DEFER. Small market, off-ICP, no API path, and the accounting value prop overlaps the bookkeeper's existing tooling. Keep the CSV importer for inbound; do not prospect.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 729–742)
- Live first-party API access: No — no public AccuPOS transactional API for third parties
