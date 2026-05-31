# NAPA TRACS

**Registry key:** `napa-tracs` — see `src/services/pos_connectors/registry.py` (lines 590–605)

## Status
CSV ONLY — `auth_type: csv_only`, no `base_url`. No public REST API located; distributed through the NAPA Auto Parts dealer / NAPA AutoCare channel.

## What it is
Shop management software (estimating, repair orders, invoicing, parts lookup) for independent auto repair shops, sold and supported through the NAPA dealer network. Owned by Genuine Parts Company.

## Vertical & market
- **Primary vertical:** automotive — independent repair shops, NAPA AutoCare centers
- **Estimated NA market presence:** Medium within independent-shop SMS, concentrated where shops have a NAPA jobber relationship
- **Typical merchant profile:** 2–8 bay shop, owner-operator, parts from a local NAPA store
- **Geographic concentration:** US (NAPA dealer footprint)

## How to spot the merchant uses it
- Windows desktop app on the service writer's PC (not browser-based)
- NAPA branding / NAPA AutoCare plaque at the counter
- Parts ordering through NAPA PROLink from inside an estimate
- Tells: "we run TRACS," "our NAPA rep set us up"

## Auth method
CSV upload only. No public API key, OAuth, or developer portal located. Any API access would be partner-mediated through Genuine Parts Company.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV | `RO Number`, `Date`, `Total`, `Service` |
| Catalog / items | ✗ | Not mapped |
| Customers | ✗ | Not mapped |
| Employees | Partial (CSV) | `Technician` per-RO |
| Inventory | ✗ | Lives in NAPA PROLink |
| Refunds | ✗ | Not mapped |
| Vehicle context | CSV | `VIN`, `Hours` |

`supports_orders: False`, `sms_fallback: True`.

## Partner program / access requirements
- **Required:** Unknown — no public program documented
- **Sign-up URL:** None public; contact is local NAPA store / NAPA TRACS support
- **Approval timeline / cost:** Not publicly documented

## Sandbox / test environment
None. A real export from a willing shop is the only test fixture.

## Rate limits
N/A — no API.

## Webhook / sync model
N/A — manual CSV upload (or scheduled drop if shop automates).

## Connect flow (what the merchant does)
1. In TRACS, run the repair-order export for the date range
2. Save as CSV mapped to registry columns (`RO Number`, `Date`, `Total`, `Service`, `VIN`, `Hours`, `Technician`)
3. Upload via Meridian's CSV importer (UI gap below)
4. Optional SMS-receipt fallback for missing ROs

## Estimated effort to go LIVE
S for CSV ingest hardening. XL for API parity — requires a Genuine Parts Company partnership conversation not on the roadmap.

## What blocks LIVE status today
- No public API — CSV is the ceiling without a NAPA partnership
- No customer-facing CSV importer UI tuned to the TRACS column set
- Off-ICP vertical — no auto-shop dashboards on Meridian today

## Common failure modes
- **Symptom:** Merchant expects live connection → **Cause:** no API → **Fix:** set CSV expectation up front; offer SMS fallback
- **Symptom:** Uploaded CSV rejected → **Cause:** column headers renamed → **Fix:** map against registry `csv_columns`; document exact export name

## Strategic notes
NAPA TRACS rides the NAPA dealer relationship — stickier inside NAPA AutoCare than browser-native competitors (Tekmetric, Shopmonkey, Shop-Ware), but the integration path runs through Genuine Parts Company, not a dev portal. Reps should not prospect NAPA AutoCare shops. If an inbound shop runs TRACS, set CSV-only expectations, log the lead, flag for product. Do not promise API timelines.

## Recommendation
DEFER.

**Reasoning:** Off-ICP, no public API, partnership path through a Fortune 500 parts distributor. CSV ingest is fine for inbound shops; proactive investment is unjustified until Meridian commits to automotive expansion.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 590–605)
- Live first-party API docs accessed: No (no public developer portal located)
