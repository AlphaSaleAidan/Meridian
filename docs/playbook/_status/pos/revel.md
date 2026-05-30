# Revel Systems

**Registry key:** `revel` — see `src/services/pos_connectors/registry.py`

## Status
OUTDATED CONFIG — legacy `API-AUTHENTICATION` header still works, but current Developer Portal documents Bearer-token (OAuth client_credentials) as the supported path. Shift4 acquired Revel in 2025 and plans to fold it into SkyTab POS, so roadmap is unstable.

## What it is
iPad-based cloud POS for restaurants (QSR, full-service, pizza, bars) and mid-size specialty retail; multi-location/franchise-friendly.

## Vertical & market
- **Primary vertical:** restaurant (primary), specialty retail (secondary)
- **NA presence:** Medium (~18,000+ locations at acquisition)
- **Typical merchant:** mid-size multi-unit restaurants, franchise groups
- **Geo:** US-dominant, some international

## How to spot it
- iPad terminals on Heckler/Ergonomic mounts
- Login URL `https://{merchant-subdomain}.revelup.com/`
- Receipts: "Powered by Revel" (some post-Shift4 shifting to SkyTab)
- Staff say "I'll check Revel" / "the back office"

## Auth method
- **Legacy (registry uses this):** API key + secret joined by colon, sent as `API-AUTHENTICATION` header. Still functional.
- **Current (Developer Portal):** OAuth 2.0 `client_credentials` → Bearer token, 24h expiry, one token across all merchants for that Partner.

Per-merchant subdomain `https://{domain}.revelup.com/resources` is authoritative — merchant must supply their subdomain.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders | yes | `/Order/` | `offset`/`limit`, page 200 |
| Catalog | yes | `/Product/` | |
| Customers | yes | `/Customer/` | |
| Employees | yes | `/Employee/` | |
| Inventory | partial | not mapped | Separate endpoints exist |
| Refunds | partial | `/Order/` | Nested in order payload |

## Partner program / access
- **Required:** Yes — credentials only to approved Partners
- **Sign-up:** https://developer.revelsystems.com/
- **Timeline:** Not publicly stated; treat as multi-week enterprise process
- **Cost / rev share:** Not publicly disclosed

## Sandbox
Available, provisioned per-Partner on approval (same per-subdomain pattern). No public self-serve sandbox.

## Rate limits
Not publicly documented on open portal. Use exponential backoff on 429.

## Webhook / sync model
Hybrid — Developer Portal documents Webhooks; current registry is poll-only via `/Order/`.

## Connect flow (merchant-facing)
1. Merchant logs into `https://{their-subdomain}.revelup.com/`
2. Gives Meridian their subdomain (for `base_url` substitution)
3. Meridian uses Partner-issued credentials — merchant does not self-generate keys under the new platform

## Effort to go LIVE
XL — Partner approval gate + auth refactor (legacy header → Bearer/OAuth) + Shift4 consolidation risk.

## What blocks LIVE today
- No Partner account / no `client_id` / `client_secret`
- Registry uses legacy `API-AUTHENTICATION`; should migrate to Bearer
- No customer-facing connect UI (subdomain + credential capture)
- Shift4 roadmap risk: Revel may be deprecated as merchants migrate to SkyTab

## Recommendation
DEFER — skip Partner approval and auth refactor. Prioritize SkyTab; treat Revel as CSV-export fallback if a prospect insists.

**Reasoning:** Shift4 consolidation makes Revel a sunset target; effort better spent where the base is migrating.

## Common failure modes
- **401 on `/Establishment/`** → wrong subdomain or key:secret not colon-joined → confirm subdomain; verify header is `key:secret`
- **404 on all endpoints** → subdomain typo or white-label host → ask merchant for their Management Console URL verbatim

## Strategic notes
Shift4 ($250M acquisition, closed 2025) said it will fold the best of Revel into SkyTab and deprecate legacy acquired-product revenue. Revel sells into a shrinking base. Flip side: these mid-market restaurants will re-platform in 12–24 months — landing them on Meridian now positions us to follow them to SkyTab.

## Sources
- developer.revelsystems.com/revelsystems/docs/api-platform-authentication
- developer.revelsystems.com/revelsystems/docs/how-to-make-an-api-call
- developer.revelsystems.com/revelsystems/docs/webhooks
- paymentsdive.com/news/shift4-point-of-sale-revel-pos-merger-acquisition-payment/715958/
- investors.shift4.com/news-events/press-releases/detail/221/
- Live API docs accessed: No (Developer Portal 403'd unauthenticated; used indexed snippets)
