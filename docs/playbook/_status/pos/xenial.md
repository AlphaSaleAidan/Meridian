# Xenial (Genius by Global Payments)

**Registry key:** `xenial` — `src/services/pos_connectors/registry.py` line 902. Config: `base_url: https://api.xenial.com/v1`, `auth_type: header`, `auth_header_name: X-Api-Key`.

## Status
NEEDS PARTNERSHIP — base URL and X-Api-Key shape are plausible but no public dev portal exists to validate endpoints or obtain credentials.

## What it is
Enterprise QSR / fast-casual / stadium-concessions POS arm of Global Payments (rebranding as "Genius by Global Payments"). Hardware + cloud SaaS with global multi-unit rollout services.

## Vertical & market
- **Vertical:** restaurant (enterprise QSR / fast-casual / stadium / theme park)
- **NA presence:** Large in enterprise; negligible in SMB
- **Typical merchant:** 50+ unit corporate or franchisee group of a global brand (Burger King, Popeyes, Carl's Jr., Tim Hortons franchisees, Dutch Bros, Panda Express, Taco Bell)

## How to spot it
- Xenial-branded terminals; "Xenial Cloud" / "Xenial Encounter" on login
- Drive-thru menu boards with Xenial branding
- Operator mentions "Genius by Global Payments," "Xenial Cloud Portal," "XPLR" (Partner Relay)
- Franchisee says "corporate runs the POS" — common at BK / Popeyes / Tim Hortons

## Auth method
API key in `X-Api-Key` header per registry. Not confirmed against live docs — `apitracker.io/a/xenial` lists no public auth spec, no free dev account, no published docs. Credentials are provisioned via Global Payments enterprise onboarding.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | YES (configured) | `/transactions` | Unvalidated |
| Catalog / items | YES (configured) | `/menu-items` | Unvalidated |
| Customers / employees / inventory | NO | — | Not in registry |
| Refunds | UNKNOWN | — | Not validated |
| Order creation | NO | — | `supports_orders: False` |

## Partner program / access
- **Required:** Yes — Global Payments / Xenial enterprise partnership; no self-serve dev signup found
- **Intake:** `contact@xenial.com` / `https://www.xenial.com/` (sales-led)
- **Timeline:** Enterprise cycle — weeks to months, gated by named brand opportunity
- **Cost / rev share:** Unknown — not published

## Sandbox
Unknown — no public URL; presumed gated behind partnership.

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only via REST. Xenial markets "Partner Relay (XPLR)" for data integration; webhooks not configured.

## Connect flow
N/A until partnership exists. Even with credentials, the franchisee usually cannot authorize alone — corporate IT controls Xenial Cloud Portal for the brand.

## Estimated effort to go LIVE
XL — Global Payments commercial agreement + endpoint validation + credential UI + brand-level (not store-level) approval.

## What blocks LIVE
- No Global Payments / Xenial partnership
- No verified live API docs — `/sites`, `/transactions`, `/menu-items` unvalidated
- No sandbox credentials, no credential intake UI
- Franchisee cannot self-authorize — corporate brand IT is the gatekeeper

## Common failure modes
- **DNS / 404 on `api.xenial.com/v1`:** placeholder URL, not live gateway → confirm gateway with Xenial partner contact
- **401 with valid-looking key:** key not provisioned for requested brand/site scope → request scope expansion via brand's Xenial admin

## Strategic notes
Off-ICP for Meridian's SMB rep motion. Deployments are corporate-controlled at global brands — a single franchisee cannot trigger integration; the deal must come through the brand. Global Payments owns the commercial relationship and gates partner access.

## Recommendation
DEFER.

**Reasoning:** Enterprise-only ICP, no self-serve dev portal, brand-gated access. Revisit only with a named brand sponsor (corporate LOI) or Global Payments channel deal.

## Sources consulted
- https://www.xenial.com/
- https://www.xenial.com/products/pos-software/
- https://apitracker.io/a/xenial
- https://hospitalitytech.com/xenial-cloud-point-sale-revolutionizes-entire-ordering-fulfillment-and-management-process
- Live API docs accessed: No (no public developer portal located)
