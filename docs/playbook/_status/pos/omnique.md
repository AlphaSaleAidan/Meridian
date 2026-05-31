# Omnique

**Registry key:** `omnique` — see `src/services/pos_connectors/registry.py` (lines 936–951)

## Status
CSV ONLY — `auth_type: csv_only`, no `base_url`. No first-party public REST API located. Frontend metadata flags `apiAvailable: false`.

## What it is
Cloud-based tire and auto shop management software (estimates, repair orders, invoicing, parts) used by independent tire and auto repair shops.

## Vertical & market
- **Vertical:** automotive — independent tire/auto repair shops
- **NA market presence:** Small vs leaders (Tekmetric, Shopmonkey, Shop-Ware); tire-leaning
- **Typical merchant:** independent tire/auto shop on an Omnique subscription
- **Geography:** US (per omnique.com); frontend marks `canadaAvailable: true`, unverified

## How to spot the merchant uses it
- Service writer working out of the Omnique web dashboard (omnique.com)
- Tire-shop tells: "we run Omnique"
- (Hardware / receipt cues not first-party verified.)

## Auth method
CSV upload only. No public API key, OAuth, or developer portal located. Any API access is partner-mediated per Omnique support.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders | CSV | `Invoice Number`, `Date`, `Total`, `Description` |
| Catalog | ✗ | Not mapped |
| Customers | ✗ | Not mapped |
| Employees | CSV | `Tech` per-invoice |
| Inventory | ✗ | Frontend claims yes — unverified |
| Refunds | ✗ | Not mapped |
| Vehicle | CSV | `VIN`, `Labor` hours |

`supports_orders: False`, `sms_fallback: True`.

## Partner program / access
- **Required:** Yes (per frontend metadata) — no public developer portal located
- **Sign-up URL / timeline / cost:** None public; contact Omnique support

## Sandbox
None located. Real shop export is the only test fixture.

## Rate limits
N/A — no API.

## Webhook / sync model
N/A — manual CSV upload (SMS-receipt fallback for missing invoices).

## Connect flow (what the merchant does)
1. Log in to Omnique dashboard
2. Reports → Sales → export date range as CSV
3. Upload via Meridian's CSV importer (UI gap below)
4. Optional SMS-receipt fallback

## Estimated effort to go LIVE
S for CSV ingest hardening. XL for API parity — requires an Omnique partnership conversation not on the roadmap.

## What blocks LIVE status today
- No public API — CSV is the ceiling without an Omnique partnership
- No customer-facing CSV importer UI tuned to Omnique's column set
- Off-ICP vertical — no auto-shop dashboards on Meridian today

## Common failure modes
- **Merchant expects live sync** → no API → set CSV expectation up front; offer SMS fallback
- **Uploaded CSV rejected** → headers renamed → map against registry `csv_columns` (`Invoice Number`, `Date`, `Total`, `Description`, `VIN`, `Labor`, `Tech`)

## Strategic notes
Smaller, tire-leaning player behind Tekmetric, Shopmonkey, and Shop-Ware in install base and behind NAPA TRACS in channel reach. Auto repair is outside Meridian's core ICP (F&B + retail SMBs on Square/Clover/Toast). Reps should not prospect Omnique shops. Inbound: set CSV-only expectations, log the lead, flag for product — do not promise API timelines or a sandbox demo.

## Recommendation
DEFER (off-ICP automotive).

**Reasoning:** Off-ICP, no public API, partner-gated, smaller than auto-shop leaders we already defer on. CSV covers inbound; proactive investment is unjustified until Meridian commits to automotive.

## Sources consulted
- `src/services/pos_connectors/registry.py` (entry `omnique`, lines 936–951)
- `frontend/src/data/pos-systems.ts` (entry `omnique`, lines 2472–2524)
- https://www.omnique.com (vendor site, surface-level only)
- Live first-party API docs accessed: No (no public developer portal located)
