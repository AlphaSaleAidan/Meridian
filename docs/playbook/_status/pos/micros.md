# Oracle MICROS (and Simphony)

**Registry keys:** `micros` and `simphony` — see `src/services/pos_connectors/registry.py` (lines 191 and 875). Oracle owns both; the configs share the same `base_url` (`https://api.oracle.com/food-and-beverage/v1`) and `token_url` (`https://login.oracle.com/oauth/token`). Note: registry config currently lists `auth_type: oauth_client_credentials`, but live Oracle docs describe OAuth 2.0 **Authorization Code + PKCE** for Simphony Transaction Services Gen2 — config is likely outdated.

## Status
NEEDS PARTNERSHIP — also OUTDATED CONFIG (wrong auth flow per current Oracle docs).

## What it is
Oracle's enterprise restaurant POS — MICROS (legacy on-prem heritage) and Simphony (cloud-first successor), used by hotels, casinos, stadiums, theme parks, and large multi-unit chains.

## Vertical & market
- **Primary vertical:** restaurant / hospitality / gaming
- **Estimated NA market presence:** Dominant in enterprise; negligible in SMB
- **Typical merchant profile:** hotel F&B operator, casino, 50+ unit chain, stadium concessionaire
- **Geographic concentration:** Global (strong international footprint)

## How to spot the merchant uses it
- Beige/black Oracle-branded terminals (Workstation 6 / 625 / Express Station)
- Login URL contains `oracleindustry.com` or `simphony` subdomain
- Receipt footer may show "MICROS" or property/enterprise name
- Conversational tell: "we're on Simphony" / "MICROS at the property level" / talk of "Enterprise Management Console"

## Auth method
OAuth 2.0 **Authorization Code + PKCE** via `{HOST}/oidc-provider/v1/oauth2/token` (per Simphony Gen2 docs). Requires `orgname` (organization short name) during signin. ID token valid 14 days, refresh token 28 days. Registry's `oauth_client_credentials` setting needs correction.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | YES | `/organizations/{org_id}/transactions` (micros), `/checks` (simphony) | Requires API account scoped to enterprise/property |
| Catalog / items | YES | `/organizations/{org_id}/menu-items` | |
| Employees | YES | `/organizations/{org_id}/employees` | |
| Customers | NO | — | Not in current config |
| Inventory | NO | — | Separate Oracle module |
| Refunds | UNKNOWN | — | Not validated against live API |
| Order creation | NO | — | `supports_orders: False` in registry |

## Partner program / access requirements
- **Partner program required:** Yes — Oracle PartnerNetwork (OPN) enrollment + Simphony Integrations Program inquiry
- **Sign-up URL:** https://www.oracle.com/food-beverage/restaurant-pos-systems/pos-integrations/partners/ and https://partner.oracle.com
- **Approval timeline:** Enterprise sales cycle — weeks to months (OPN approval, then ISV team validation testing, then Marketplace listing)
- **Cost / revenue share:** Free Simphony Lab during development; OPN tier fees may apply; Marketplace listing is the gate

## Sandbox / test environment
- **Available:** Yes — "Simphony Lab" provided free to approved ISV partners
- **URL:** Provisioned post-approval, not public
- **Notes:** No self-serve sandbox; gated behind OPN enrollment

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only via REST per current registry config. Oracle does offer event streams in newer Gen2 APIs but not configured here.

## Connect flow (what the merchant does)
Not applicable until partnership exists. Post-approval, merchant admin would: (1) log in to Reporting and Analytics, (2) add a Simphony Transaction Services Gen2 API account, (3) choose Client Scope (BOTH/LOCAL/CLOUD) and Authorization Scope, (4) share generated Client ID with Meridian, (5) complete OAuth signin with `orgname`.

## Estimated effort to go LIVE
XL — custom partnership required (OPN enrollment + ISV validation + Marketplace listing) plus connector rewrite (auth flow correction, PKCE, refresh-token rotation).

## What blocks LIVE status today
- No Oracle PartnerNetwork enrollment
- No Simphony Integrations Program acceptance
- Registry config uses wrong auth flow (`oauth_client_credentials` vs. PKCE)
- No customer-facing OAuth UI
- No Simphony Lab credentials for validation

## Common failure modes
- **Symptom:** 401 on token endpoint → **Likely cause:** wrong grant type (client_credentials vs. authorization_code) → **Fix:** rebuild connector for PKCE flow
- **Symptom:** 404 on `/organizations/{org_id}/...` → **Likely cause:** `org_id` vs. `orgname` mismatch → **Fix:** confirm tenant short name during signin

## Strategic notes
MICROS/Simphony is enterprise-only and a poor fit for Meridian's SMB rep motion. Sales cycles are 3–9 months, decisions involve corporate IT + procurement, and incumbents (Agilysys, Olo, Spoonity) already own the integration shelf. Pursue only if Meridian has a named hotel/casino/chain opportunity worth the OPN investment.

## Recommendation
DEFER.

**Reasoning:** Wrong ICP for current motion — enterprise sales cycle and partnership gating make ROI negative until Meridian has a concrete enterprise pipeline. Revisit only with a signed LOI from a multi-unit prospect.

## Sources consulted
- https://docs.oracle.com/en/industries/food-beverage/simphony/omsstsg2api/authenticate.html
- https://docs.oracle.com/cd/F32325_01/doc.192/f36951.pdf
- https://www.oracle.com/food-beverage/restaurant-pos-systems/pos-integrations/partners/
- https://www.oracle.com/partners/en/products/industries/simphony/integrate/index.html
- https://www.oracle.com/food-beverage/restaurant-pos-systems/pos-integrations/next-gen-api-for-restaurant-pos/
- Live API docs accessed: Yes
