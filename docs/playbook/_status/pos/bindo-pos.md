# Bindo POS

**Registry key:** `bindo-pos` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN — vendor pivoted to Asia-Pacific; configured API host (`api.bfriendo.com`) cannot be publicly verified as Bindo-owned.

## What it is
Cloud-based iPad POS originally launched in NYC (2010) for SMB retail; now primarily marketed in Hong Kong / Greater China for restaurants and retail.

## Vertical & market
- **Primary vertical:** Retail + restaurant (multi-vertical)
- **Estimated NA market presence:** Small (vendor's center of gravity moved to APAC after 2021 HKT-led Series A)
- **Typical merchant profile:** Single-location SMB retail / F&B; in HK also used by taxis (PAX A930 partnership)
- **Geographic concentration:** Hong Kong / Greater China; minor US legacy footprint

## How to spot the merchant uses it
- iPad-based POS with "Bindo" branding on login screen
- Receipt footer or admin URL referencing `bindolabs.com`
- HK merchants: may mention HKT, Octopus, or WeChat Pay integration
- US merchants are most likely on a legacy install; ask when they last received a vendor update

## Auth method
API key in header — `X-Api-Key` (per registry config)

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | configured | `/orders` | `supports_orders: False` flag in registry — pull path not enabled |
| Catalog / items | configured | `/products` | |
| Customers | configured | `/customers` | |
| Employees | not configured | — | |
| Inventory | not configured | — | |
| Refunds | not configured | — | |

Test endpoint: `/stores`. Data envelope key: `data`.

## Partner program / access requirements
- **Partner program required:** Unknown — public API portal is `apidoc.bindo.co`; the registry's `api.bfriendo.com/v2` host is not referenced in any public Bindo documentation found
- **Sign-up URL:** Unknown
- **Approval timeline:** Unknown
- **Cost / revenue share:** Unknown

## Sandbox / test environment
- **Available:** Unknown
- **URL:** N/A
- **Notes:** Confirm directly with vendor; do not assume the configured host is live

## Rate limits
Unknown — not documented publicly.

## Webhook / sync model
Unknown — assume poll-only until confirmed.

## Connect flow (what the merchant does)
Not defined — no customer-facing UI built. Would require merchant to obtain an API key from Bindo support and paste it.

## Estimated effort to go LIVE (config → production-ready)
L (1+ months) — vendor contact required, host/auth must be revalidated, `supports_orders` flag must be flipped after the orders path is exercised against a real tenant.

## What blocks LIVE status today
- `bfriendo.com` host in registry is not confirmed as a Bindo-operated domain in any public source
- `supports_orders: False` in config — the primary signal we sell to reps is disabled
- No customer-facing OAuth/connect UI
- Vendor's NA support presence appears thin post-2021 pivot to HK

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401/403 from `api.bfriendo.com` → **Likely cause:** wrong host or stale key → **Fix:** confirm correct base URL with vendor; the documented portal is `apidoc.bindo.co`
- **Symptom:** Merchant has Bindo but no API key → **Likely cause:** legacy plan without API access → **Fix:** escalate to Bindo support; may require plan upgrade

## Strategic notes
Bindo's funding (HKT-led 2021 Series A, ~$6M; ~$59M total per PitchBook) and product marketing pushed the company toward Hong Kong taxis, F&B, and retail. The NA SMB iPad POS niche is now dominated by Square, Clover, Shopify POS, and Lightspeed Retail. A NA rep is unlikely to encounter Bindo organically. No evidence of a Tencent acquisition was found.

## Recommendation
DEFER

**Reasoning:** Low NA prospect density, unverified API host, and orders pull disabled in config make this poor ROI versus the dozens of higher-volume retail POS already in the playbook. Revisit only if a specific HK/APAC merchant pipeline opens.

## Sources consulted
- https://bindolabs.com/
- https://apidoc.bindo.co/
- https://pitchbook.com/profiles/company/63545-05
- https://www.paxglobal.com.hk/en/latest-news/pax-and-bindo-labs-bring-contactless-payments-to-hong-kong-taxis-with-the-a930/
- `src/services/pos_connectors/registry.py` (key `bindo-pos`)
- Live API docs accessed: No (public portal reachable; configured `api.bfriendo.com` host not validated)
