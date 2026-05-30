# iiko

**Registry key:** `iiko` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN (off-ICP) — config points at the real iikoCloud (iikoTransport) host, but it's the Russia-region endpoint and there is no documented merchant population in Meridian's NA ICP.

## What it is
Russian-founded restaurant suite (iikoRMS, iikoFront POS, iikoOffice back-office, iikoCloud/iikoTransport public API) for full-service, QSR, dark kitchens, bars, cafes. Founded 2005; iiko Middle East operates out of Dubai.

## Vertical & market
- **Primary vertical:** restaurant (full-service, QSR, bar, cafe, dark kitchen, delivery-heavy chains)
- **Estimated NA market presence:** Small — no meaningful US/Canada footprint surfaced in public sources
- **Typical merchant profile:** multi-unit operator in Russia/CIS, MENA (UAE/Saudi loudest), or growing LatAm; iiko claims 30,000+ F&B businesses globally
- **Geographic concentration:** International — dominant Russia/CIS, strong MENA, expanding LatAm; minimal NA

## How to spot the merchant uses it
- Cyrillic-language back office or terminals; "iiko" branding on tablet login
- Back-office on iiko-hosted subdomains (`*.iiko.it`, `iikoweb`); cloud API on `api-*.iiko.services`
- Russian-speaking ownership or restaurant group with Russian/CIS or MENA roots
- Conversational tells: "iikoFront," "iikoOffice," "iikoCloud," "iikoTransport," "iikoDelivery"

## Auth method
Bearer token via POST `/access_token` using an `apiLogin` key the merchant generates inside iikoWeb. Per-merchant API license required; tokens short-lived.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Partial | `/deliveries/by_delivery_date_and_status` | Delivery API only — dine-in/table orders live elsewhere |
| Catalog / items | ✓ | `/nomenclature` | Full menu dump per organization |
| Customers | ✗ | — | Separate loyalty API, not configured |
| Employees | ✗ | — | Not configured |
| Inventory | ✗ | — | Deep inventory exists; separate adapter |
| Refunds | ✗ | — | Not configured |

`supports_orders: True` with `/deliveries/create` — UNVERIFIED end-to-end.

## Partner program / access requirements
- **Partner program required:** Effectively yes — API access gated by iiko-issued license tied to the merchant's installation
- **Sign-up URL:** No clean NA-facing developer portal; docs live at iiko.help and community Postman/GitHub mirrors
- **Approval timeline:** UNCERTAIN — merchant requests license through their iiko reseller
- **Cost / revenue share:** Unknown publicly; handled by reseller

## Sandbox / test environment
- **Available:** UNCERTAIN — iikoDelivery described as trial-testable by third parties; no NA sandbox confirmed
- **URL:** N/A publicly
- **Notes:** Community Postman collections (avatariya, salesduck) are the accessible reference

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only on cloud. iikoFront on-prem has plugin/event hooks via the iikoFront SDK, not the cloud REST surface.

## Connect flow (what the merchant does)
1. Merchant (or reseller) enables API access on the iikoCloud license
2. Merchant generates `apiLogin` inside iikoWeb
3. Merchant pastes `apiLogin` into Meridian connect screen
4. Meridian POSTs `/access_token`, caches bearer, polls `/organizations` → `/nomenclature` → `/deliveries/*`

## Estimated effort to go LIVE
L (1+ months) — needs regional endpoint routing, license-acquisition path, partner relationship, and dine-in coverage beyond delivery.

## What blocks LIVE status today
- `base_url` is `api-ru.iiko.services` (Russia region); international tenants typically route to non-RU regional hosts — NA-originated connects will likely fail or hit compliance issues
- No customer-facing connect UI; order-pull only covers `/deliveries/*`
- No partner relationship; sanctions exposure not legally reviewed

## Common failure modes
- **Symptom:** `/access_token` 401 → **Cause:** no API license, or `apiLogin` from wrong region → **Fix:** route through correct regional host; confirm license with reseller
- **Symptom:** empty `/organizations` → **Cause:** token issued for different tenant/region → **Fix:** confirm region, re-issue token
- **Symptom:** missing dine-in orders → **Cause:** only `/deliveries/*` configured → **Fix:** extend connector

## Strategic notes
iiko is genuinely large globally — dominant in Russia/CIS, real MENA presence, growing LatAm — but materially absent from Meridian's NA ICP. The `api-ru.iiko.services` host is the Russia-region endpoint; any US-based integration with Russia-resident infrastructure triggers OFAC review (post-2022 US/UK/EU sanctions extended to IT/cloud/enterprise-software services to Russia). Even for non-RU iiko tenants, an NA-based ISV needs counsel sign-off on in-scope regional endpoints. Not worth spec work — only revisit if a qualified MENA or LatAm restaurant group with non-RU tenancy lands in pipeline.

## Recommendation
DEFER.

**Reasoning:** Off-ICP for Meridian's NA motion and carries unresolved Russia-sanctions exposure on the configured endpoint; no engineering investment until a qualified non-RU international deal forces it.

## Sources consulted
- https://iiko.github.io/front.api.doc/ + https://github.com/iiko/front.api.doc + https://github.com/iiko/front.api.sdk
- iikoCloud community refs: https://www.postman.com/avatariya/iiko-cloud-api/overview ; https://github.com/salesduck/iiko-cloud-api ; https://github.com/kebrick/pyiikocloudapi ; https://packagist.org/packages/codeofsolomon/laravel-iiko-cloud-api
- Company: https://tracxn.com/d/companies/iiko/__lWMv5pqAD6ABkMhNImqqrmfBDN8Ez5R_mB3Et6M3z7M
- Sanctions: https://www.clearytradewatch.com/2024/10/u-s-uk-and-eu-sanctions-alignment-u-s-it-and-software-sector-service-bans-and-export-controls-take-effect-as-russia-sanctions-continue-to-expand/ ; https://www.fenwick.com/insights/publications/u-s-imposes-sweeping-new-sanctions-and-export-controls-on-russia-and-belarus
- Live API docs accessed: Partial (iikoFront GitHub Pages reachable; iikoCloud auth endpoint reachable but requires credentials)
