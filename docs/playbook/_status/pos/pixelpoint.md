# PixelPoint POS (PAR Technology)

**Registry key:** `pixelpoint` — see `src/services/pos_connectors/registry.py`

## Status
**CSV ONLY.** Registry: `auth_type: csv_only`, `base_url: ""`, `supports_orders: False`, `sms_fallback: True`. Column map: `Transaction ID / Date Time / Total / Item / Payment`.

## What it is
PAR's mid-market restaurant POS — historically Windows on-premise for table-service and hospitality. Same parent as Brink, separate product line and go-to-market.

## Vertical & market
- **Vertical:** restaurant — table-service, casual dining, bars, hospitality
- **NA presence:** Medium — long-tenured base; not PAR's growth product (Brink is)
- **Typical merchant:** independents and small chains, mid-market — broader than Brink's enterprise-QSR ICP
- **Geography:** US-primary, international via PAR channel partners

## How to spot it
- Operator says "PixelPoint" or "PAR PixelPoint" (rarely "PAR" alone — that's Brink)
- Windows back-office UI; on-premise server in the back room
- PAR-branded hardware (EverServ) common
- Tell: talks about a local reseller / VAR, not a corporate PAR rep

## Auth method
**CSV upload only.** PixelPoint is not listed in the "Other PAR Products" API-portal section on `developers.partech.com` alongside Brink, RM DataCentral, and PAR Pay — no public developer portal located. Programmatic access would route through PAR partnerships, same channel as Brink.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | CSV only | n/a | Transaction ID, Date Time, Total, Item, Payment |
| Catalog / items | not configured | — | |
| Customers | not configured | — | |
| Employees | not configured | — | |
| Inventory | not configured | — | |
| Refunds | not configured | — | |

## Partner program / access
- **Required:** Assumed yes — same PAR channel as Brink; no separately published PixelPoint partner program found
- **Contact:** `api.support@partech.com` / PAR partnerships
- **Timeline:** Unknown; assume Brink-style enterprise B2B
- **Cost / rev share:** Not publicly disclosed

## Sandbox
Unknown — no public sandbox located. Would need PAR partnerships to confirm.

## Rate limits
N/A — CSV path only.

## Webhook / sync model
**N/A.** CSV upload, with `sms_fallback: True` for daily totals.

## Connect flow
1. Merchant pulls a transactions report from PixelPoint back-office
2. Uploads CSV in Meridian's connector UI
3. Meridian maps columns per registry
4. If CSV fails or merchant can't self-serve, fall back to SMS daily totals

## Estimated effort to go LIVE
- **CSV path:** S — already configured; validate against a real export
- **API path:** XL — needs PAR partnership and confirmed API surface; Brink-style build, not a self-serve OAuth flip

## What blocks LIVE today
- No PixelPoint API client and no confirmed public API surface
- No validated PixelPoint CSV on file to verify column names
- No PAR partnership in place

## Common failure modes
- **"I'm on PAR"** → could be Brink, PixelPoint, or RM DataCentral → ask: "cloud or server in the back?" Server = PixelPoint; cloud = Brink
- **CSV columns don't match** → PixelPoint reports are configurable per install → request a screenshot of the export screen and remap

## Strategic notes
Siblings, different shapes: **Brink = enterprise QSR cloud SOAP**, **PixelPoint = mid-market hospitality on-prem**. Any PAR conversation opened for Brink should put PixelPoint in scope — same org, same contracts, low marginal cost. Solo PixelPoint engineering is hard to justify.

## Recommendation
**DEFER.** If engineering is pursued, bundle with the Brink / PAR partnership.

**Reasoning:** No public API, no committed prospect, and PAR's partnership gate is the same as Brink's — pursuing PixelPoint alone duplicates enterprise-sales effort that only pays off when bundled.

## Sources consulted
- `src/services/pos_connectors/registry.py` (`pixelpoint` entry)
- https://developers.partech.com/ (PixelPoint not in "Other PAR Products" portals)
- https://apitracker.io/a/partech-pixelpoint
- Sibling entry: `docs/playbook/_status/pos/brink.md`
- Live API docs accessed: No (no public PixelPoint developer portal located)
