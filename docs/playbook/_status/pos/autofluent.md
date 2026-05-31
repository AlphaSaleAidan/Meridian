# AutoFluent

**Registry key:** `autofluent` — see `src/services/pos_connectors/registry.py` (lines 515–530)

## Status
CSV ONLY — `auth_type: csv_only`, no `base_url`. No public REST API or developer portal located for AutoFluent. Sold and supported direct by TABS Software (Long Island, NY).

## What it is
Windows-based shop management system from TABS Software for independent auto repair shops and tire dealers — estimates, repair orders, invoicing, inventory, accounting. Mid-tier positioning between entry-level (Mitchell1 Manage) and enterprise (R.O. Writer / Tekmetric).

## Vertical & market
- **Primary vertical:** automotive — independent repair shops and tire stores
- **Estimated NA market presence:** Small-to-Medium — long-tenured product, modest installed base relative to Mitchell1, Tekmetric, Shopmonkey
- **Typical merchant profile:** 3–10 bay independent shop or small multi-location tire dealer, owner-operator, often a long-time TABS customer
- **Geographic concentration:** US

## How to spot the merchant uses it
- Windows desktop UI on the service writer's PC (not browser-native)
- "AutoFluent" branding on printed invoices / estimates
- Tells: "we use AutoFluent," "our system is from TABS"

## Auth method
CSV upload only. No public API key, OAuth, or developer documentation located.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV | `Invoice #`, `Date`, `Total`, `Description` |
| Catalog / items | ✗ | Not mapped |
| Customers | ✗ | Not mapped |
| Employees | Partial (CSV) | `Tech` per-invoice |
| Inventory | ✗ | Not mapped |
| Refunds | ✗ | Not mapped |
| Vehicle context | CSV | `VIN`, `Labor Hrs` |

`supports_orders: False`, `sms_fallback: True`.

## Partner program / access requirements
- **Required:** Unknown — no public developer program located
- **Sign-up URL:** None public; vendor contact is TABS Software direct
- **Approval timeline / cost:** Not publicly documented

## Sandbox / test environment
None located. A real export from a willing shop is the only test fixture.

## Rate limits
N/A — no API.

## Webhook / sync model
N/A — manual CSV upload.

## Connect flow (what the merchant does)
1. In AutoFluent, run the invoice / repair-order export for the date range
2. Save as CSV mapped to registry columns (`Invoice #`, `Date`, `Total`, `Description`, `VIN`, `Labor Hrs`, `Tech`)
3. Upload via Meridian's CSV importer
4. Optional SMS-receipt fallback for missing invoices

## Estimated effort to go LIVE
S for CSV ingest hardening. XL for any API parity — would require a direct partnership conversation with TABS Software with no public path documented.

## What blocks LIVE status today
- No public API — CSV is the ceiling without a TABS partnership
- No customer-facing CSV importer UI tuned to the AutoFluent column set
- Off-ICP vertical — Meridian has no auto-shop dashboards today

## Common failure modes
- **Symptom:** Merchant expects live sync → **Cause:** no API → **Fix:** set CSV expectation up front; offer SMS fallback
- **Symptom:** Uploaded CSV rejected → **Cause:** column headers renamed in export → **Fix:** map against registry `csv_columns`; document exact AutoFluent export name

## Strategic notes
AutoFluent sits in the same "Windows desktop, vendor-direct, no dev portal" tier as NAPA TRACS and R.O. Writer — sticky with long-tenured shops, but every integration path runs through a phone call to TABS Software. Reps should not prospect AutoFluent shops. If an inbound shop runs it, set CSV-only expectations, log the lead, flag for product. Do not promise API timelines.

## Recommendation
DEFER.

**Reasoning:** Off-ICP vertical, no public API, small installed base relative to Tekmetric / Shopmonkey. CSV ingest covers inbound shops; proactive investment is unjustified until Meridian commits to automotive expansion.

## Sources consulted
- `src/services/pos_connectors/registry.py` (lines 515–530)
- Live first-party API docs accessed: No (no public developer portal located)
