# TireMaster

**Registry key:** `tire-master` — see `src/services/pos_connectors/registry.py` (lines 966–980)

## Status
CSV ONLY — registry entry has `auth_type: csv_only`, empty `base_url`, and `supports_orders: False`. No live API integration exists; ingestion is exported-report upload only, with SMS fallback enabled.

## What it is
Shop management software for independent tire and wheel retailers — point-of-sale, work orders, tire inventory, and back-office accounting tailored to the tire-shop workflow. Built by ASA Automotive Systems, a long-tenured vendor in the independent tire-dealer segment.

## Vertical & market
- **Primary vertical:** automotive — independent tire and wheel shops
- **Estimated NA market presence:** Dominant within the narrower independent-tire-shop niche; not a general auto-repair SMS
- **Typical merchant profile:** independent tire dealer running sales plus light mechanical service, often a long-time ASA customer who treats TireMaster as both POS and inventory system
- **Geographic concentration:** US-heavy

## How to spot the merchant uses it
- ASA / TireMaster branding inside the shop's back-office workstation
- Owner says "we run ASA" or "we're on TireMaster" — the brand and the product are used interchangeably
- Invoices reference `Invoice #`, VIN, and a named technician on tire / wheel line items

## Auth method
CSV upload only. No API base URL, no token, no OAuth — ingestion is via merchant-exported reports mapped to the columns below. SMS fallback (`sms_fallback: True`) is the alternative inbound path.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Via CSV | — | Mapped from exported invoice report |
| Catalog / items | Via CSV (line items only) | — | `items` ← `Service Description` column |
| Customers | Not configured | — | Not in CSV column map |
| Employees | Via CSV (technician) | — | `technician` ← `Technician` column |
| Inventory | Not configured | — | Despite TireMaster's strong inventory module, not in current map |
| Refunds | Not configured | — | |
| Vehicle | VIN | — | `vin` ← `VIN` |

CSV column map (from registry): `Invoice #`, `Date`, `Total`, `Service Description`, `VIN`, `Technician`.

## Partner program / access requirements
- **Partner program required:** Not first-party verified for Meridian's use case; treat as Unknown
- **Sign-up URL:** N/A — no public developer portal referenced in registry
- **Approval timeline:** N/A (CSV only)
- **Cost / revenue share:** N/A (CSV only)

## Sandbox / test environment
- **Available:** N/A — CSV-only ingestion
- **URL:** N/A
- **Notes:** Test by ingesting a sample export from a friendly tire shop

## Rate limits
N/A — no live API call path.

## Webhook / sync model
None. Manual / scheduled CSV export, plus SMS fallback. Treat freshness as daily-at-best.

## Connect flow (what the merchant does)
1. Shop exports the invoice report from TireMaster to CSV
2. Owner uploads the CSV to Meridian (UI not yet built)
3. Meridian maps columns per registry and ingests rows
4. SMS fallback can fill gaps between exports

## Estimated effort to go LIVE
N/A — "LIVE" doesn't apply to a CSV-only connector. Any LIVE-equivalent lift is XL: would require an API partnership with ASA Automotive that is not in scope.

## What blocks LIVE status today
- No public API in current config (`base_url` is empty)
- No partner relationship with ASA Automotive
- Off-ICP vertical — Meridian has no tire-shop-tuned dashboards or persona analytics
- Inventory and customer fields not mapped, despite being TireMaster's strengths

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Import skipped most rows" → **Likely cause:** export template differs from registry column names → **Fix:** confirm the shop exported the standard invoice report; remap if a custom template is in use
- **Symptom:** "Totals look low" → **Likely cause:** `Total` column excludes tire fees, disposal, or shop supplies depending on export view → **Fix:** verify which report view the shop ran; standardize on one
- **Symptom:** "Duplicate invoices on re-upload" → **Likely cause:** no dedupe on `Invoice #` across exports → **Fix:** dedupe by `transaction_id` (`Invoice #`) at ingest

## Strategic notes
Off-ICP. TireMaster is dominant within the independent tire-shop niche, but that niche itself sits outside Meridian's current ICP. Reps should not prospect tire shops. If an inbound tire dealer is on TireMaster, log the lead, accept CSV uploads as a stopgap, and flag for product. Do not commit to any live-API timeline — the path runs through ASA Automotive, not a self-serve developer portal.

## Recommendation
DEFER.

**Reasoning:** CSV-only by design, off-ICP tire-shop vertical, and any live-API uplift depends on an ASA Automotive partnership that is out of scope for current Meridian priorities. Revisit only as part of a committed automotive expansion.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 966–980, `tire-master` entry)
- `src/services/pos_connectors/registry.py` (lines 955–965, `alldata-manage` sibling CSV-only entry for comparison)
- Live first-party API docs accessed: No (no API; CSV-only connector)
