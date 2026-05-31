# Bolt On Technology

**Registry key:** `bolt-on` — see `src/services/pos_connectors/registry.py` (lines 981–994)

## Status
CSV ONLY — `auth_type: csv_only`, no `base_url`, `supports_orders: False`, `sms_fallback: True`.

## What it is
Customer-texting and digital vehicle inspection (DVI) software for independent auto repair shops — two-way SMS, photo/video DVI to the customer's phone, appointment reminders. Layered on a shop management system (Mitchell1, ALLDATA Manage), not a replacement.

## Vertical & market
- **Vertical:** automotive — independent auto repair
- **NA presence:** Medium-to-Large in add-on tooling; widely paired with Mitchell1
- **Typical merchant:** 2–10 bay shop already on an SMS, adding Bolt On for texting + DVI
- **Geography:** US-heavy

## How to spot it
- Inspection results sent as a mobile link with photos/video
- Two-way SMS thread for confirms, status, approvals
- Owner mentions "Bolt On" or "Mobile Manager" alongside their SMS vendor

## Auth method
CSV upload only. No base URL, token, or OAuth. SMS fallback is the alternative.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | Via CSV | From exported RO report |
| Catalog / items | Via CSV (line items) | `items` ← `Service` |
| Customers / Employees / Inventory / Refunds | Not configured | Not in CSV map |
| Vehicle | VIN | `vin` ← `VIN` |

CSV columns (registry): `RO #`, `Date`, `Total`, `Service`, `VIN`.

## Partner program / access requirements
- **Required:** Unknown — not first-party verified
- **Sign-up URL / timeline / cost:** N/A (CSV only)

## Sandbox / test environment
N/A — test via a sample export from a friendly shop.

## Rate limits
N/A — no live API.

## Webhook / sync model
None. Manual CSV export plus SMS fallback. Daily-at-best freshness.

## Connect flow (what the merchant does)
1. Shop exports the RO report to CSV
2. Owner uploads CSV to Meridian (UI not yet built)
3. Meridian maps columns per registry and ingests
4. SMS fallback fills gaps between exports

## Estimated effort to go LIVE
N/A. Uplift is XL — needs a Bolt On partnership not in scope.

## What blocks LIVE status
- No public API in config (empty `base_url`)
- No partner relationship with Bolt On
- Off-ICP — no auto-repair-tuned dashboards
- Thin CSV map (no customer, technician, labor-hours) vs. Mitchell1

## Common failure modes
- "Import skipped rows" → custom export template → use standard RO export; remap if custom
- "Totals look low" → `Total` may be pre-tax or parts-excluded → standardize on one view
- "Duplicate ROs on re-upload" → no cross-export dedupe → dedupe by `RO #`

## Strategic notes
Off-ICP. Bolt On is an add-on (texting + DVI), not the system of record — transactions originate in Mitchell1, ALLDATA Manage, or similar. Reps should not prospect auto repair shops. On inbound, ask which SMS sits underneath, log both, accept CSV as a stopgap, flag for product. Do not commit to a live-API timeline.

## Recommendation
DEFER.

**Reasoning:** CSV-only by design, off-ICP vertical, and Bolt On is an add-on rather than the system of record — any uplift starts with the underlying SMS, as part of a committed automotive expansion.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 981–994, `bolt-on`)
- `src/services/pos_connectors/registry.py` (lines 960–980, `mitchell1` sibling)
- Live first-party API docs accessed: No (no API)
