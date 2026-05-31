# AutoVitals

**Registry key:** `autovitals` — see `src/services/pos_connectors/registry.py` (lines 952–965)

## Status
CSV ONLY. Registry has `auth_type: csv_only`, empty `base_url`, `supports_orders: False`, `sms_fallback: True`. No live API; ingest is exported-report upload only.

## What it is
Digital vehicle inspection (DVI) and shop workflow software for independent mechanical auto repair — photo/video inspections, customer-approval flows, recommended-service tracking. Typically a frontend layered on top of a shop management system (SMS) rather than the transactional system of record.

## Vertical & market
- **Vertical:** automotive — independent mechanical auto repair
- **NA presence:** Well-known within the DVI tooling segment for independent shops
- **Merchant:** 2–8 bay independent shop using AutoVitals as the inspection/customer-facing layer, with Mitchell1 Manager SE or ALLDATA Manage as the back-office SMS
- **Geo:** US-heavy

## How to spot the merchant uses it
- Customer receives a texted inspection link with photos and green-yellow-red service grades
- Service writer works from a tablet doing photo-based inspections
- Owner mentions "AutoVitals" or "DVI" alongside their SMS (Mitchell1 / ALLDATA)
- Paired with — not replacing — Mitchell1 or ALLDATA

## Auth method
CSV upload only. No API base URL, no token, no OAuth. SMS fallback enabled.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | Via CSV | Mapped from exported RO report |
| Catalog / items | Via CSV (line items only) | `items` ← `Service` |
| Customers / Employees / Inventory / Refunds | ✗ | Not in column map |
| Vehicle | VIN | `vin` ← `VIN` |

CSV column map: `RO #`, `Date`, `Total`, `Service`, `VIN`. No technician column (the `tire-master` sibling entry has one; this does not).

## Partner program / access requirements
Not first-party verified; treat as Unknown. No public developer portal referenced in current registry config.

## Sandbox / test environment
N/A — CSV-only. Test with a sample export from a friendly shop.

## Rate limits
N/A — no live API path.

## Webhook / sync model
None. Manual or scheduled CSV upload plus SMS fallback. Freshness daily-at-best.

## Connect flow (what the merchant does)
1. Shop exports RO report from AutoVitals (or upstream SMS) to CSV
2. Owner uploads CSV in Meridian (UI not yet built)
3. Meridian maps columns per registry and ingests

## Estimated effort to go LIVE
N/A — does not apply to a CSV-only connector. API uplift would be XL and depends on a partnership not in scope.

## What blocks LIVE status today
- No public API in current config (empty `base_url`)
- No partner relationship verified
- Off-ICP vertical — Meridian sells F&B + retail SMBs on Square/Clover/Toast
- Thinner column map than `tire-master` (no technician field)

## Common failure modes
- **Symptom:** "Import skipped rows" → export template differs from registry → confirm standard RO export; remap if custom
- **Symptom:** "Totals low" → `Total` excludes parts or is pre-tax → standardize on one report view
- **Symptom:** "Duplicate ROs on re-upload" → no dedupe on `RO #` → dedupe by `transaction_id` at ingest

## Strategic notes
Off-ICP. AutoVitals is the inspection/customer-facing layer, not the transactional system of record — the underlying SMS (Mitchell1 / ALLDATA / Tekmetric / Shop-Ware / Shopmonkey) owns RO data. Do not prospect auto repair. If an inbound shop arrives on AutoVitals, accept the CSV stopgap and log for product. Any committed automotive push should target the SMS layer first.

## Recommendation
DEFER.

**Reasoning:** CSV-only by design, off-ICP automotive, and AutoVitals is a frontend rather than the SMS system of record — RO-level economics live in the underlying Mitchell1 / ALLDATA system.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 952–965, `autovitals` entry)
- `src/services/pos_connectors/registry.py` (lines 966–980, `tire-master` sibling CSV-only entry for comparison)
- `docs/playbook/_status/pos/mitchell1.md`, `docs/playbook/_status/pos/alldata-manage.md` (paired SMS context)
- Live first-party API docs accessed: No (no API; CSV-only connector)
