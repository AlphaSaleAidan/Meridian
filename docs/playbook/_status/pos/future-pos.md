# Future POS

**Registry key:** `future-pos` — see `src/services/pos_connectors/registry.py`

## Status
CSV ONLY — registry sets `auth_type: csv_only`, `base_url: ""`. No API client.

## What it is
Long-established Windows-based restaurant POS. Common in casual dining, bars, and country clubs running on-prem Windows terminals with a back-office manager app.

## Vertical & market
- **Vertical:** restaurant (casual dining, bars, country clubs)
- **NA presence:** Established but niche; no public location count
- **Typical merchant:** independent or small-chain hospitality on Windows terminals plus Future POS Manager
- **Geo:** US

## How to spot it
- Windows terminals with the "Future POS" boot screen
- Back-office app branded "Future POS Manager"
- Receipts / KDS referencing Future POS
- Tells: "we're on Future POS," "we export from Sales Analysis"

## Auth method
None. `auth_type: csv_only` — Meridian ingests CSV from Future POS Manager. No API key, OAuth, or webhook path in registry.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Receipt Number`, `Transaction Date`, `Grand Total`, `Item Description`, `Tender Type` |
| Catalog / items | not configured | Item Description rides in the sales export |
| Customers / Employees / Refunds | not configured | — |
| Inventory | not configured | Frontend notes a separate Stock Count export exists |

`supports_orders: False`, `sms_fallback: True` — read-only analytics, SMS daily-totals fallback.

## Partner program / access
Unknown — no public developer portal or partner program identified. No sign-up URL, timeline, or cost on record.

## Sandbox
N/A (no API). Validate column mapping against a real Future POS Manager export.

## Rate limits / webhook model
N/A — manual CSV upload only. Frontend notes weekly cadence.

## Connect flow (merchant side)
1. Open Future POS Manager
2. Reports → Sales Analysis → export to CSV
3. Upload CSV in Meridian's connector UI
4. Meridian maps columns per registry
5. Repeat on agreed cadence; SMS daily totals if export breaks

## Effort to go LIVE
S on CSV — already wired; needs validation against a real export. Beyond CSV: UNKNOWN.

## What blocks LIVE today
- No validated CSV from a real Future POS merchant confirming columns match registry
- No one-click onboarding template for the Sales Analysis export
- No confirmed API or partner path beyond CSV

## Common failure modes
- **Columns don't match registry** → different report or version → screenshot the export, remap columns
- **Merchant can't find the export** → non-manager login → require Manager-level login

## Strategic notes
On-prem Windows POS in a slow-moving vertical with a small addressable base. CSV is the only honest path today.

## Recommendation
DEFER

**Reasoning:** No public API, no partner program identified, niche on-prem base. Keep CSV live for inbound; do not invest engineering or partnership time proactively.

## Sources consulted
- `src/services/pos_connectors/registry.py` (`future-pos` entry)
- `frontend/src/data/pos-systems.ts` (`future-pos` entry)
- Live API docs accessed: No (no public developer portal identified)
