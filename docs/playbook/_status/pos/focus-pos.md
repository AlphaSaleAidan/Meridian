# Focus POS

**Registry key:** `focus-pos` — see `src/services/pos_connectors/registry.py`

## Status
CSV ONLY

## What it is
Enterprise-tier on-premise restaurant POS common in mid-market full-service. Vendor: Restaurant Magic / Choice Restaurant Group.

## Vertical & market
- **Primary vertical:** restaurant (full-service tilt)
- **Estimated NA market presence:** Medium
- **Typical merchant profile:** multi-unit full-service, established independents
- **Geographic concentration:** US (primary)

## How to spot the merchant uses it
- "Focus" branding on back-office / manager terminal
- On-premise server box in back-of-house (not pure cloud / tablet)
- Tells: "we run Focus," "our Focus reseller," Restaurant Magic back-office reporting

## Auth method
**CSV upload only.** Registry sets `auth_type: csv_only`, no `base_url`, no API client.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | CSV only | n/a | Check Number, Date, Total, Item Name, Payment Method, Server |
| Catalog / items | not configured | — | Item Name inline on tx rows |
| Customers | not configured | — | |
| Employees | partial via CSV | — | Server per check |
| Inventory | not configured | — | |
| Refunds | not configured | — | |

`supports_orders: False`, `sms_fallback: True`.

## Partner program / access requirements
- **Partner program required:** Unknown
- **Sign-up URL:** N/A
- **Approval timeline:** Unknown
- **Cost / revenue share:** Unknown

## Sandbox / test environment
- **Available:** N/A (CSV path)
- **URL:** N/A
- **Notes:** Validation needs a real Focus export from a live merchant

## Rate limits
N/A (CSV upload)

## Webhook / sync model
N/A — batch CSV only.

## Connect flow (what the merchant does)
1. Run a sales / check report in Focus back-office
2. Export to CSV
3. Upload in Meridian connector UI
4. Meridian maps columns per registry
5. If CSV fails, fall back to SMS daily-totals

## Estimated effort to go LIVE
**CSV path:** S (1–3 days) pending real-export validation.
**API path:** Unknown; treat as XL until researched.

## What blocks LIVE status today
- No validated CSV export from a real Focus merchant — registry columns assumed
- No API path researched or implemented
- No partner relationship with Restaurant Magic on file

## Common failure modes
- **Symptom:** Headers don't match registry → **Cause:** report-template variation → **Fix:** screenshot export config, remap
- **Symptom:** Merchant can't find export → **Cause:** on-premise install, only reseller has back-office admin → **Fix:** route via reseller or fall back to SMS

## Strategic notes
On-premise, back-office-heavy system in a segment dominated by rep-led, reseller-mediated cycles. CSV is viable per-merchant but does not scale without a Restaurant Magic or reseller channel. No public self-service developer program reviewed.

## Recommendation
**DEFER**

**Reasoning:** CSV serves one-off merchants, but enterprise on-prem footprint means scale needs a partner / reseller channel not yet scoped. Revisit on demand.

## Sources consulted
- `src/services/pos_connectors/registry.py` (entry: `focus-pos`)
- Live API docs accessed: No
