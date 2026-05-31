# RetailEdge (by High Meadow Business Solutions)

**Registry key:** `retail-edge` — see `src/services/pos_connectors/registry.py`

## Status
CSV ONLY — `auth_type: csv_only`, `base_url: ""`, `sms_fallback: true`.

## What it is
Windows PC, locally-installed POS and inventory software for small specialty retailers. One-time license from $495, no required recurring fees; data stays on the merchant's machine.

## Vertical & market
- **Primary vertical:** retail (specialty — fashion, beer/wine/liquor, bakery, beauty supply)
- **Estimated NA market presence:** Small — loyal, long-tenured base; no public merchant count
- **Typical merchant profile:** single-location independent specialty store on a Windows PC at the counter
- **Geographic concentration:** US (vendor HQ Rutland, VT; in market since 1989)

## How to spot the merchant uses it
- Windows desktop at counter (not a tablet) running "RetailEdge"
- "We own our POS outright" / "no monthly fee"
- References to "RECAP" (RetailEdge's integration platform)

## Auth method
N/A — no public API key, OAuth, or token flow. RECAP mediates third-party integration; no public developer docs.

## Data we can pull (per current config)

| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ✓ (CSV) | n/a — `Invoice`, `Date`, `Amount`, `Description`, `Payment` | |
| Catalog / items | ✗ | — | Not mapped |
| Customers | ✗ | — | Not mapped |
| Employees | ✗ | — | Not mapped |
| Inventory | ✗ | — | Not mapped |
| Refunds | ✗ | — | Not mapped |

`supports_orders: false`, `sms_fallback: true`.

## Partner program / access requirements
- **Partner program required:** Unknown — no public developer portal
- **Sign-up URL:** None public; contact High Meadow via retailedge.com
- **Approval timeline:** Unknown
- **Cost / revenue share:** Not disclosed

## Sandbox / test environment
- **Available:** Unknown
- **URL:** N/A
- **Notes:** None

## Rate limits
N/A — no API.

## Webhook / sync model
N/A — file-based CSV export from local Windows install.

## Connect flow (what the merchant does)
1. Export sales report from RetailEdge to CSV
2. Upload to Meridian (or email to SMS-fallback inbox)
3. Meridian parses against the registry column map

## Estimated effort to go LIVE
XL — needs a partnership conversation with High Meadow about RECAP and confirmation that data egress from a local Windows app is contractually permitted.

## What blocks LIVE status today
- No public API documentation
- Locally-installed Windows-only — no cloud endpoint to call
- RECAP technical surface not publicly documented

## Common failure modes
- **Symptom:** Merchant can't find export → **Cause:** unfamiliarity with report module → **Fix:** point to reporting menu
- **Symptom:** Columns don't match → **Cause:** wrong report → **Fix:** confirm `Invoice / Date / Amount / Description / Payment` shape

## Strategic notes
Small, loyal, on-premise Windows base. The one-time-license, local-data posture is the merchant-facing selling point — exactly what makes a cloud integration low-priority and partnership-gated. Lead with CSV; escalate only on a real prospect.

## Recommendation
**DEFER** — keep CSV; do not invest engineering until a real merchant deal asks for it.

**Reasoning:** No public API, local Windows architecture, and a small specialty-retail footprint make proactive build unjustifiable; CSV covers the realistic ingestion path.

## Sources consulted
- https://retailedge.com/
- https://retailedge.com/about-us
- https://retailedge.com/recap
- Live API docs accessed: No — none found publicly
