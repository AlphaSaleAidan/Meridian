# Agilysys (InfoGenesis POS)

**Registry key:** `agilysys` — see `src/services/pos_connectors/registry.py` (line 925). Config: `base_url: https://api.agilysys.com/v1`, `auth_type: header`, `auth_header_name: X-Api-Key`. Neither the host nor the API key header is verifiable against any public Agilysys developer documentation — both should be treated as placeholders until validated with an Agilysys integrations contact.

## Status
NEEDS PARTNERSHIP — also UNCERTAIN (config endpoints not validated against live API; no public dev portal).

## What it is
Agilysys InfoGenesis POS is an enterprise hospitality point-of-sale used by hotels, resorts, casinos, country clubs, cruise lines, stadiums, and managed foodservice (higher ed, healthcare, airports). Part of a wider Agilysys stack (PMS, Pay, IG OnDemand, IG KDS).

## Vertical & market
- **Primary vertical:** hospitality F&B (hotels, casinos, resorts, clubs)
- **Estimated NA market presence:** Strong in enterprise hospitality; effectively zero in independent SMB restaurants
- **Typical merchant profile:** multi-outlet hotel/resort F&B operator, casino floor, private club, large-venue concessionaire
- **Geographic concentration:** Global (NA-headquartered, strong international hospitality footprint)

## How to spot the merchant uses it
- "InfoGenesis" branding on terminals or back-office screens
- Customer is a hotel/resort/casino/club rather than a standalone restaurant
- Conversational tell: "we run InfoGenesis at the property" / "IG OnDemand for poolside" / Agilysys Pay on receipts
- Often paired with Agilysys PMS or LMS in the same property

## Auth method
Per registry: API key in `X-Api-Key` header. Per Agilysys public materials: "Open Integration Framework" with REST APIs, but no public auth spec. Real integrations are gated behind direct partnership; assume credentials are issued per-property after sign-off.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | YES (config) | `/transactions` | Not validated against live API |
| Catalog / items | YES (config) | `/items` | Not validated |
| Properties (test) | YES (config) | `/properties` | Not validated |
| Customers | NO | — | Not in registry |
| Employees | NO | — | Not in registry |
| Inventory | NO | — | Separate Agilysys module |
| Refunds | UNKNOWN | — | Not in registry |
| Order creation | NO | — | `supports_orders: False` |

## Partner program / access requirements
- **Partner program required:** Yes — Agilysys Solution Partners program
- **Sign-up URL:** https://www.agilysys.com/en/solution-partners/ (contact form / "Connect with a Hospitality Expert" — no self-serve developer signup). Phone: 877-369-6208.
- **Approval timeline:** Enterprise sales cycle — weeks to months; no published timeline
- **Cost / revenue share:** Not publicly disclosed

## Sandbox / test environment
- **Available:** Not publicly documented
- **URL:** N/A (gated behind partner intake)
- **Notes:** Expect credentials and any sandbox to be issued per-engagement after partnership conversation

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only per current registry config. Agilysys markets an "Open Integration Framework" but webhook support is not publicly specified.

## Connect flow (what the merchant does)
Not applicable until partnership exists. Post-approval, the property's IT lead would coordinate with Agilysys to issue an API key scoped to the property, which would then be entered into Meridian by the merchant admin.

## Estimated effort to go LIVE
XL — custom partnership required (Solution Partner intake), config validation against real docs, plus a customer-facing credential capture UI.

## What blocks LIVE status today
- No Agilysys Solution Partner relationship
- Registry config (`base_url`, header name, endpoint paths) is unverified against live Agilysys API documentation
- No customer-facing API-key capture UI
- No sandbox credentials
- Wrong ICP for current Meridian rep motion

## Common failure modes
- **Symptom:** Connection test fails immediately → **Likely cause:** `api.agilysys.com/v1` is a placeholder; real host issued per integration → **Fix:** confirm actual host with Agilysys partner contact
- **Symptom:** 401/403 with valid-looking key → **Likely cause:** auth header name wrong (`X-Api-Key` unverified) → **Fix:** request auth spec from Agilysys integrations team

## Strategic notes
Agilysys lives in enterprise hospitality — hotels, casinos, resorts, clubs — and competes directly with Oracle MICROS/Simphony at that tier. It is completely off-ICP for Meridian's SMB analytics motion. Reps will only see Agilysys when prospecting a hotel F&B director or casino ops lead, where the buying committee, sales cycle, and integration bar all match the MICROS playbook. Treat any inbound Agilysys mention as a qualification signal that the prospect is enterprise, not SMB.

## Recommendation
DEFER.

**Reasoning:** Off-ICP enterprise hospitality with a gated partner program and unverified registry config. Revisit only with a signed enterprise opportunity at a hotel, resort, casino, or club worth the partnership intake.

## Sources consulted
- https://www.agilysys.com/en/solution-partners/
- https://www.agilysys.com/en/ecosystem/food-and-beverage/infogenesis-pos/
- https://www.agilysys.com/en/products/ig-ondemand/
- `src/services/pos_connectors/registry.py` (line 925)
- Live API docs accessed: No (no public Agilysys developer portal located)
