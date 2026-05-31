# NorthStar

**Registry key:** `northstar` — see `src/services/pos_connectors/registry.py`

## Status
CSV ONLY — registry sets `auth_type: csv_only`, `base_url: ""`. No API client.

## What it is
Enterprise restaurant POS used in chains. The brief identifies the target as **NorthStar Order Entry** from **Custom Business Solutions (CBS)**, a long-running enterprise restaurant POS.

**Vendor ambiguity to resolve before any outbound:** `frontend/src/data/pos-systems.ts` labels the same registry key as "NorthStar (Fourth)" — Fourth's workforce/analytics platform — not the CBS product. Same brand, different vendor. Confirm which NorthStar the merchant is actually running before quoting integration details.

## Vertical & market
- **Vertical:** restaurant (enterprise / multi-unit chains)
- **NA presence:** Established enterprise footprint; no verified public location count
- **Typical merchant:** multi-unit chain with central IT, not a single-location operator
- **Geo:** US (per available config)

## How to spot it
- Terminals branded "NorthStar Order Entry" or "CBS NorthStar"
- Back-office or reporting tooling referencing CBS / Custom Business Solutions
- If branded "Fourth" or "HotSchedules" alongside NorthStar → likely the Fourth product, not CBS
- Tells: "we're on NorthStar," "our POS is from CBS"

## Auth method
None. `auth_type: csv_only` — Meridian ingests a CSV export. No API key, OAuth, or webhook path in registry.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Check #`, `Date`, `Total`, `Item`, `Payment`, `Server` |
| Catalog / items | not configured | `Item` field rides in the sales export |
| Customers | not configured | — |
| Employees | partial | `Server` field on each check |
| Inventory | not configured | — |
| Refunds | not configured | — |

`supports_orders: False`, `sms_fallback: True` — read-only analytics, SMS daily-totals fallback if CSV breaks.

## Partner program / access
Unknown — no public developer portal or partner program verified for either CBS NorthStar or Fourth NorthStar at the POS-data layer. Both are enterprise sales motions.

## Sandbox
N/A (no API). Validate column mapping against a real NorthStar export before claiming coverage.

## Rate limits / webhook model
N/A — manual CSV upload only.

## Connect flow (merchant side)
1. Pull a sales/check report from NorthStar back office
2. Export to CSV
3. Upload CSV in Meridian's connector UI
4. Meridian maps columns per registry (`Check #`, `Date`, `Total`, `Item`, `Payment`, `Server`)
5. Repeat on agreed cadence; SMS daily totals if export breaks

Exact menu paths not verified — confirm with first onboarded merchant.

## Effort to go LIVE
S on CSV — wiring exists, needs validation against a real export. Beyond CSV: XL (enterprise partnership, vendor identity must be resolved first).

## What blocks LIVE today
- Vendor ambiguity: registry doesn't pin CBS vs. Fourth; frontend says Fourth, brief says CBS
- No validated CSV from a real NorthStar merchant confirming columns match registry
- No confirmed API or partner path for either vendor

## Common failure modes
- **Columns don't match registry** → wrong report or different NorthStar product → screenshot the export, remap columns, confirm vendor
- **Merchant says "we don't have that report"** → likely on the Fourth analytics product, not CBS Order Entry → re-scope

## Strategic notes
Enterprise chain POS with no public API and a contested vendor identity inside our own data. CSV is the only honest path today, and even that needs a real merchant export to validate. Do not promise more than CSV ingestion on a sales call.

## Recommendation
DEFER

**Reasoning:** No API, no verified partner program, and an unresolved vendor conflict between our registry/frontend and the CBS attribution. Keep CSV available for inbound; do not invest engineering or outbound time until a real merchant lands and the vendor is confirmed.

## Sources consulted
- `src/services/pos_connectors/registry.py` (`northstar` entry)
- `frontend/src/data/pos-systems.ts` (`northstar` entry — attributes to Fourth)
- Task brief (attributes to Custom Business Solutions)
- Live API docs accessed: No (no public developer portal identified for either vendor)
