# Leaf Logix

**Registry key:** `leaf-logix` — see `src/services/pos_connectors/registry.py`

## Status
**CSV ONLY** (registry-correct), effectively **DEPRECATED**. Dutchie acquired Leaf Logix in March 2021; `leaflogix.com` 301-redirects to `business.dutchie.com/leaflogix` with "LeafLogix is no longer available, but its spirit lives on in Dutchie POS." Remaining tenants are on a migration path to Dutchie POS.

## What it is
Seed-to-sale cannabis ERP — retail POS, inventory, METRC compliance, cultivation, manufacturing, distribution. Historically the back office of choice for MSOs like GTI, Harvest, Columbia Care.

## Vertical & market
- **Vertical:** cannabis (ERP-first, POS-secondary)
- **NA presence:** Shrinking — legacy MSO base, no new sales
- **Profile:** MSO with multi-license ops (retail + cultivation + processing)
- **Geographic:** US state-regulated; some intl MSO exposure (Colombia, Caribbean, Africa)

## How to spot the merchant uses it
- "We're on Leaf Logix" or "Leaf Logix on the back office, Dutchie on the floor"
- Back-office dashboard branded Leaf Logix
- Reports with `Sale ID`, `Sale Date`, `METRC Tag`, `State License` columns
- "Seed-to-sale" + MSO language

## Auth method
**CSV upload only** (`auth_type: "csv_only"`). No public REST API documented; `apitracker.io` profile has every field blank. Any current "API" access routes through Dutchie's partner program.

## Data we can pull (per current config)
- **CSV (mapped):** orders (`Sale ID`, `Sale Date`, `Total`, `Product Name`) + compliance (`METRC Tag`, `State License`)
- **Not mapped:** customers, employees, inventory, refunds
- Registry: `supports_orders: False`, `sms_fallback: True`

## Partner program / access requirements
N/A — product is sunset; no integrator onboarding. Cannabis partnership work routes through **Dutchie** (see `dutchie-pos.md`).

## Sandbox / test environment
None. Use a hand-built CSV matching the mapping.

## Rate limits
N/A — CSV upload.

## Webhook / sync model
**Manual CSV upload only.** No webhooks, no polling.

## Connect flow (what the merchant does)
1. Log in to Leaf Logix back office → Reports → Sales
2. Export the date range as CSV
3. Upload to Meridian; we parse against the `leaf-logix` mapping
4. SMS fallback if the merchant prefers to text the export

## Estimated effort to go LIVE
**S (1–3 days)** for CSV path — mapping already in registry; only upload UI/parser glue needs verification. **XL** for any API path — no standalone API surface exists.

## What blocks LIVE status today
- No customer-facing "connect Leaf Logix" UI; merchants must use generic CSV upload
- Column mapping unverified against a real export (field names only, no sample)
- Shrinking TAM — tenants migrating to Dutchie POS

## Common failure modes
- **Symptom:** "My Leaf Logix login doesn't work" → **Cause:** tenant migrated to Dutchie POS → **Fix:** redirect to Dutchie POS connect flow
- **Symptom:** CSV missing-column error → **Cause:** wrong report or template changed → **Fix:** confirm "Sales" report; validate against `csv_columns`

## Strategic notes
Legacy footprint inside Dutchie, not a live integration target. Land Dutchie POS as the cannabis integration; Leaf Logix CSV is a courtesy bridge for un-migrated tenants. Cannabis caveats from Treez/Dutchie writeups apply: federal banking restrictions, regulated patient/member PII, deliberate "Meridian for Cannabis" GTM decision.

## Recommendation
**WAIT** — keep the CSV-only registry entry; no engineering investment in a Leaf Logix API path.

**Reasoning:** Product is sunset; cannabis investment belongs on Dutchie POS. CSV mapping is cheap insurance for legacy tenants.

## Sources consulted
- leaflogix.com (301 → business.dutchie.com/leaflogix; "no longer available")
- business.dutchie.com acquisition announcement (Mar 2021)
- newcannabisventures.com (MSO customers: GTI, Harvest, Columbia Care)
- softwareconnect.com/cannabis-erp/leaf-logix (flagged "Discontinued")
- apitracker.io/a/leaflogix (API profile blank — no public surface)
- `src/services/pos_connectors/registry.py` (`leaf-logix` entry)
- `frontend/src/data/pos-systems.ts` (`apiAvailable: false`)
- `docs/playbook/_status/pos/dutchie-pos.md` (successor)
- Live API docs accessed: No (none exist publicly)
