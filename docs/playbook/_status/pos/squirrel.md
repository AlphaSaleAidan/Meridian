# Squirrel Systems (Squirrel Cloud POS / Squirrel 11)

**Registry key:** `squirrel` — see `src/services/pos_connectors/registry.py` (line 913). Config: `base_url: https://api.squirrelsystems.com/v1`, `auth_type: header`, `auth_header_name: X-Api-Key`, `test_endpoint: /properties`, `transactions_endpoint: /checks`, `catalog_endpoint: /menu-items`, `employees_endpoint: /employees`, `supports_orders: False`. The host and auth header are not verifiable against any public Squirrel developer documentation — treat both as placeholders until validated with a Squirrel integrations contact.

## Status
NEEDS PARTNERSHIP — also UNCERTAIN (no public developer portal located; registry endpoints unvalidated).

## What it is
Squirrel Systems is a Vancouver, BC–based hospitality POS vendor offering Squirrel Cloud POS and Squirrel 11, plus Squirrel-branded terminal hardware, for restaurants, multi-unit chains, hotels, resorts, and casinos.

## Vertical & market
- **Primary vertical:** restaurant + hospitality F&B (with hotel/resort/casino F&B as a notable segment)
- **Estimated NA market presence:** Medium in Canadian hospitality; long-established but smaller than Toast/Lightspeed/TouchBistro by unit count
- **Typical merchant profile:** independent full-service restaurant, multi-unit Canadian chain, or hotel/resort F&B outlet
- **Geographic concentration:** Canada-strong (HQ Burnaby, BC), also sold into US hospitality

## How to spot the merchant uses it
- "Squirrel" branding on terminals, KDS screens, or back-office login
- Hotel or resort F&B operator in Canada referencing "Squirrel" alongside their PMS
- Conversational tell: "we run Squirrel," "Squirrel Cloud," or "Squirrel 11"
- Featured public references include Browns, Tribeca, and Logan's

## Auth method
Per registry: API key in `X-Api-Key` header. Per Squirrel public materials: no published auth spec. Real integrations appear to be gated behind direct partnership; assume credentials are issued per-property after sign-off.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / checks | YES (config) | `/checks` | Not validated against live API |
| Catalog / menu items | YES (config) | `/menu-items` | Not validated |
| Properties (test) | YES (config) | `/properties` | Not validated |
| Employees | YES (config) | `/employees` | Not validated |
| Customers | NO | — | Not in registry |
| Inventory | NO | — | Not in registry |
| Refunds | UNKNOWN | — | Not in registry |
| Order creation | NO | — | `supports_orders: False` |

## Partner program / access requirements
- **Partner program required:** Yes — Squirrel operates a partner/reseller portal at `partner.squirrelsystems.com` (login-gated)
- **Sign-up URL:** No public self-serve developer signup located; initial contact via sales 1.866.686.6887 or the contact form on `squirrelsystems.com`
- **Approval timeline:** Unknown — assume enterprise/hospitality sales cycle (weeks)
- **Cost / revenue share:** Not publicly disclosed

## Sandbox / test environment
- **Available:** Not publicly documented
- **URL:** N/A
- **Notes:** Expect credentials and any sandbox to be issued per engagement after partnership conversation

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only per current registry config. Webhook support is not publicly specified.

## Connect flow (what the merchant does)
Not applicable until partnership exists. Post-approval, the property's IT lead would coordinate with Squirrel to issue an API key scoped to the property, which would then be entered into Meridian by the merchant admin.

## Estimated effort to go LIVE
XL — partnership intake plus config validation against real Squirrel API documentation, plus a customer-facing credential capture UI.

## What blocks LIVE status today
- No Squirrel Systems partnership relationship
- Registry config (`base_url`, header name, endpoint paths) is unverified against live Squirrel API documentation
- No customer-facing API-key capture UI
- No sandbox credentials
- No public developer portal located

## Common failure modes
- **Symptom:** Connection test fails immediately → **Likely cause:** `api.squirrelsystems.com/v1` is a placeholder; real host issued per integration → **Fix:** confirm actual host with Squirrel integrations contact
- **Symptom:** 401/403 with valid-looking key → **Likely cause:** auth header name (`X-Api-Key`) unverified → **Fix:** request auth spec from Squirrel partner team

## Strategic notes
Important for the Meridian Canada portal: Squirrel is Canadian-headquartered (Burnaby, BC) and has real presence in Canadian full-service restaurants and hotel/resort F&B. Any Canada-side rep prospecting independent restaurants or hotel F&B directors in BC, AB, and ON should expect to encounter Squirrel. It sits between SMB cloud POS (Lightspeed, TouchBistro) and enterprise hospitality (Agilysys, MICROS) — a real partnership conversation is likely required, but the buyer profile is less remote than Agilysys/MICROS.

## Recommendation
WAIT.

**Reasoning:** Strategically relevant for Meridian Canada given the BC HQ and hospitality footprint, but no public API/developer portal and unverified registry config mean we should open a partnership conversation before investing build effort. Trigger build work as soon as a Canadian hospitality opportunity warrants the partner intake.

## Sources consulted
- https://www.squirrelsystems.com/
- https://www.squirrelsystems.com/contact/
- `src/services/pos_connectors/registry.py` (line 913)
- Live API docs accessed: No (no public Squirrel developer portal located)
