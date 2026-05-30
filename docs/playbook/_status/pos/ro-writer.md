# R.O. Writer

**Registry key:** `ro-writer` — see `src/services/pos_connectors/registry.py` (lines 543–558)

## Status
CSV ONLY — `auth_type: csv_only`, no `base_url`, `supports_orders: False`, `sms_fallback: True`.

## What it is
Long-established Windows-based shop management system for independent auto repair — ROs, estimates, invoicing, parts, labor, technician assignment. Predates the cloud SMS cohort (Tekmetric / Shopmonkey / Shop-Ware).

## Vertical & market
- **Primary vertical:** automotive — independent auto repair
- **NA presence:** Medium (long-tenured; not first-party verified)
- **Merchant profile:** multi-bay shop on a Windows back-office PC
- **Geo:** US-heavy (not first-party verified)

## How to spot the merchant uses it
- Windows desktop app on a back-office PC
- Owner says "R.O. Writer" or "ROW"
- ROs printed with `RO#` and VIN-keyed labor lines

## Auth method
CSV upload only. No API, token, or OAuth. SMS fallback is the alternative.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders | Via CSV | From RO report |
| Items | Via CSV | `items` ← `Service Line` |
| Customers | No | — |
| Employees | Via CSV | `technician` ← `Technician` |
| Inventory | No | — |
| Refunds | No | — |
| Vehicle | Via CSV | `vin`, `labor_hours` |

Columns: `RO#`, `Close Date`, `RO Total`, `Service Line`, `VIN`, `Labor Hours`, `Technician`.

## Partner program / access requirements
- **Required:** Unknown — not first-party verified
- **Sign-up URL / timeline / cost:** N/A (CSV only)

## Sandbox / test environment
N/A — CSV-only. Test with a sample export from a friendly shop.

## Rate limits
N/A — no live API.

## Webhook / sync model
None. Manual / scheduled CSV plus SMS fallback. Freshness: daily-at-best.

## Connect flow (what the merchant does)
1. Shop exports closed-RO report to CSV
2. Owner uploads to Meridian (UI not built)
3. Meridian maps columns per registry and ingests
4. SMS fallback fills gaps

## Estimated effort to go LIVE
N/A — CSV-only. Live-API uplift would be XL, contingent on a vendor partnership not in scope.

## What blocks LIVE status today
- No public API (`base_url` empty)
- No partner relationship referenced
- Off-ICP — no auto-repair dashboards or persona analytics
- Windows-desktop architecture — integration path unclear vs. cloud-native peers

## Common failure modes (for troubleshooting playbook)
- "Import skipped most rows" → export template differs from registry columns → confirm standard closed-RO report; remap if custom
- "Totals look low" → `RO Total` may be pre-tax → standardize on one report view
- "Duplicate ROs on re-upload" → no dedupe on `RO#` → dedupe by `transaction_id` at ingest

## Strategic notes
Off-ICP. Do not prospect auto repair shops. Inbound on R.O. Writer: log lead, accept CSV as stopgap, flag for product. No live-API timeline. Sibling CSV-only auto entries (`alldata-manage`, `mitchell1`, `protractor`) defer together — future work only makes sense as part of an automotive expansion covering cloud-native SMS leaders.

## Recommendation
DEFER.

**Reasoning:** CSV-only by design, off-ICP automotive, and any live-API uplift depends on a vendor partnership out of scope for current Meridian priorities.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 543–558, `ro-writer`)
- `src/services/pos_connectors/registry.py` (lines 559–573, `protractor` sibling)
- `docs/playbook/_status/pos/alldata-manage.md` (sibling)
- Live first-party API docs accessed: No (CSV-only)
