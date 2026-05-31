# Protractor

**Registry key:** `protractor` — see `src/services/pos_connectors/registry.py` (lines 559–574)

## Status
CSV ONLY — registry has `auth_type: csv_only`, empty `base_url`, `supports_orders: False`, `sms_fallback: True`. No live API.

## What it is
Cloud shop management software for independent auto repair shops — work orders, invoicing, VIN-keyed labor lines, technician assignment. Canadian-founded.

## Vertical & market
- **Vertical:** automotive — independent auto repair shops
- **NA market presence:** Medium overall; meaningful Canadian footprint (rep-relevant for the Meridian Canada portal)
- **Typical merchant:** 2–8 bay independent shop on cloud SMS
- **Geographic concentration:** Canada-strong (Canadian product origin), with US distribution
- **Ownership:** Reported acquired into the Autoshop Solutions / Solera auto-repair portfolio. Unverified — confirm before quoting.

## How to spot the merchant uses it
- "Protractor" branding on the back-office browser tab
- Owner mentions "Protractor" — common in Canadian independent shops
- Invoices reference invoice number, VIN, assigned tech, labour hours (Canadian spelling: registry field is `Labour Hours`)

## Auth method
CSV upload only. No base URL, no token, no OAuth. SMS fallback is the alternative inbound path.

## Data we can pull (per current config)
CSV-only. Registry mapping:
- Orders: `transaction_id` ← `Invoice Number`; `timestamp` ← `Invoice Date`; `total_cents` ← `Invoice Total`
- Items (line only): `items` ← `Line Item`
- Employees (tech only): `technician` ← `Assigned Tech`
- Vehicle: `vin` ← `VIN`; `labor_hours` ← `Labour Hours`
- Customers / Inventory / Refunds: not configured

## Partner program / sandbox / rate limits / webhooks
All N/A or Unknown — no public developer portal referenced; CSV-only, no live API. Freshness: daily at best.

## Connect flow
1. Shop exports the invoice report from Protractor to CSV
2. Owner uploads CSV to Meridian (UI not yet built)
3. Meridian maps columns per registry and ingests
4. SMS fallback fills gaps between exports

## Estimated effort to go LIVE
N/A for CSV-only. Live-API uplift would be XL — requires partnership with the current owner. Blockers: no public API in config, no partner relationship, off-ICP vertical, no customer column.

## Common failure modes
- **"Import skipped most rows"** → export template differs from registry columns (note Canadian spelling `Labour Hours`) → confirm shop ran the standard invoice report
- **"Tech column empty"** → export view excludes `Assigned Tech` → have shop add it
- **"Duplicate invoices on re-upload"** → no dedupe on `Invoice Number` → dedupe by `transaction_id` at ingest

## Strategic notes
Off-ICP overall, but **flag the Canadian footprint for the Meridian Canada portal**: Canadian in origin and one of the auto SMS names a Canada-side rep is likely to hear from independent shops, alongside Mitchell1 and ALLDATA Manage. Inbound Canadian shop: log the lead, accept CSV as a stopgap, do not commit to a live-API timeline.

## Recommendation
DEFER. CSV-only by design and off-ICP. Keep warm for Meridian Canada inbound only.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 559–574 `protractor`; 575–589 `alldata-manage` sibling)
- `docs/playbook/_status/pos/_template.md`
- Live first-party API docs: No (CSV-only). Ownership lineage is from public reporting, unverified here.
