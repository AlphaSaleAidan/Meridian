# ALLDATA Manage

**Registry key:** `alldata-manage` — see `src/services/pos_connectors/registry.py` (lines 575–589)

## Status
CSV ONLY — registry entry has `auth_type: csv_only`, no `base_url`, and `supports_orders: False`. No live API integration exists; ingestion is exported-report upload only, with SMS fallback enabled.

## What it is
Shop management software for independent auto repair shops — work orders, estimates, invoicing, parts lookup, and labor-time integration, marketed alongside ALLDATA Repair (the OEM service-info library that the brand is best known for). Older product lineage than the modern cloud SMS cohort (Tekmetric / Shopmonkey / Shop-Ware).

## Vertical & market
- **Primary vertical:** automotive — independent auto repair shops, collision adjacent
- **Estimated NA market presence:** Dominant in independent repair tooling alongside Mitchell1 (both are long-tenured brands with deep penetration in the segment); Manage specifically is one slice of that footprint, not the whole of it
- **Typical merchant profile:** 2–8 bay independent shop, often a long-time ALLDATA Repair subscriber who added Manage to keep service info and shop management under one vendor
- **Geographic concentration:** US-heavy
- **Ownership:** AutoZone subsidiary

## How to spot the merchant uses it
- ALLDATA branding inside the shop's back-office workstation (service info and SMS share the same shell)
- Owner mentions "ALLDATA" generically — disambiguate Repair (info) vs. Manage (SMS) vs. Manage Online
- Invoices / ROs reference work order numbers and VIN-keyed labor lines

## Auth method
CSV upload only. No API base URL, no token, no OAuth — ingestion is via merchant-exported reports mapped to the columns below. SMS fallback (`sms_fallback: True`) is the alternative inbound path.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Via CSV | — | Mapped from exported work-order report |
| Catalog / items | Via CSV (line items only) | — | `items` ← `Description` column |
| Customers | Not configured | — | Not in CSV column map |
| Employees | Not configured | — | Technician not in current map (Mitchell1 entry has it; Manage entry does not) |
| Inventory | Not configured | — | |
| Refunds | Not configured | — | |
| Vehicle | VIN + labor hours | — | `vin` ← `VIN`, `labor_hours` ← `Hours` |

CSV column map (from registry): `Work Order #`, `Date`, `Total`, `Description`, `VIN`, `Hours`.

## Partner program / access requirements
- **Partner program required:** Not first-party verified for Meridian's use case; treat as Unknown
- **Sign-up URL:** N/A — no public developer portal referenced in registry
- **Approval timeline:** N/A (CSV only)
- **Cost / revenue share:** N/A (CSV only)

## Sandbox / test environment
- **Available:** N/A — CSV-only ingestion
- **URL:** N/A
- **Notes:** Test by ingesting a sample export from a friendly shop

## Rate limits
N/A — no live API call path.

## Webhook / sync model
None. Manual / scheduled CSV export, plus SMS fallback. Treat freshness as daily-at-best.

## Connect flow (what the merchant does)
1. Shop exports the work-order report from ALLDATA Manage to CSV
2. Owner uploads the CSV to Meridian (UI not yet built)
3. Meridian maps columns per registry and ingests rows
4. SMS fallback can fill gaps between exports

## Estimated effort to go LIVE
N/A — "LIVE" doesn't apply to a CSV-only connector. The work to lift this to LIVE-equivalent is XL: would require an API partnership with ALLDATA / AutoZone that is not in scope.

## What blocks LIVE status today
- No public API in current config (`base_url` is empty)
- No partner relationship with ALLDATA / AutoZone
- Off-ICP vertical — Meridian has no auto-repair-tuned dashboards or persona analytics
- Customer column map is thinner than the Mitchell1 sibling entry (no technician field)

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Import skipped most rows" → **Likely cause:** export template differs from registry column names → **Fix:** confirm the shop exported the standard work-order report; remap if a custom template is in use
- **Symptom:** "Totals look low" → **Likely cause:** `Total` column is pre-tax or excludes parts depending on export view → **Fix:** verify which report view the shop ran; standardize on one
- **Symptom:** "Duplicate work orders on re-upload" → **Likely cause:** no dedupe on `Work Order #` across exports → **Fix:** dedupe by `transaction_id` (`Work Order #`) at ingest

## Strategic notes
Off-ICP. ALLDATA the brand is dominant in independent repair — but the dominance is in the service-info product (ALLDATA Repair), not specifically in Manage as a standalone SMS. Reps should not prospect auto repair shops. If an inbound shop is on ALLDATA Manage, log the lead, accept CSV uploads as a stopgap, and flag for product. Do not commit to any live-API timeline — the path runs through AutoZone, not a self-serve developer portal.

## Recommendation
DEFER.

**Reasoning:** CSV-only by design, off-ICP automotive vertical, and any live-API uplift depends on a partnership with AutoZone that is out of scope for current Meridian priorities. Revisit only as part of a committed automotive expansion that also covers Mitchell1, Tekmetric, Shop-Ware, and Shopmonkey.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 575–589, `alldata-manage` entry)
- `src/services/pos_connectors/registry.py` (lines 499–514, `mitchell1` sibling CSV-only entry for comparison)
- Live first-party API docs accessed: No (no API; CSV-only connector)
