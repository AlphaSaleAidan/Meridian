# TouchBistro

**Registry key:** `touchbistro` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP

## What it is
iPad-based restaurant POS built for independent full-service restaurants and small chains; Toronto-founded, strong in Canada and a top-3 reseller of choice for TD Merchant Solutions.

## Vertical & market
- **Primary vertical:** restaurant (full-service, casual, cafes, bars)
- **Estimated NA market presence:** Medium overall, Large in Canada
- **Typical merchant profile:** independent FSR, 1–5 locations, iPad terminals
- **Geographic concentration:** ~45% Canada / ~48% US per public customer breakdowns — disproportionately important for the Meridian Canada portal

## How to spot the merchant uses it
- iPad terminals on swivel stands at host stand / server stations (no proprietary hardware)
- Server login screen branded "TouchBistro"
- Receipt footer often reads "Powered by TouchBistro" and merchant may use TouchBistro Online Ordering, Reservations (formerly TableUp), or Gift Cards add-ons
- Conversational tells: "we run on iPads," "our POS is TouchBistro," payments through Chase, Worldpay, Moneris, Square, or Barclaycard

## Auth method
API key (header) — issued only after a signed partner agreement. No public OAuth, no self-service developer portal.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ✓ (partner) | `/restaurants/{restaurant_id}/orders` | Config present; unvalidated against live partner docs |
| Catalog / items | ✓ (partner) | `/restaurants/{restaurant_id}/menu-items` | |
| Customers | ✗ | — | Not in current registry config |
| Employees | ✓ (partner) | `/restaurants/{restaurant_id}/staff` | |
| Inventory | ✗ | — | Usually via WISK/MarketMan integrations |
| Refunds | Unknown | — | Likely surfaced inside orders payload — needs partner doc confirmation |

`supports_orders: False` — read-only analytics, no order push.

## Partner program / access requirements
- **Partner program required:** Yes
- **Sign-up URL:** No public form. Contact `integratedpartners@touchbistro.com` (historically John Florinis)
- **Approval timeline:** Enterprise sales cycle — typically 4–8+ weeks, commercial terms required
- **Cost / revenue share:** Unknown / negotiated per partner; API keys are individually monitored

## Sandbox / test environment
- **Available:** UNCERTAIN — not publicly documented
- **URL:** N/A publicly
- **Notes:** Sandbox access negotiated with partner contact

## Rate limits
Unknown — not publicly documented.

## Webhook / sync model
Poll-only based on registry config. Webhook availability under partner agreement is UNCERTAIN.

## Connect flow (what the merchant does)
1. Rep collects merchant intent and `restaurant_id` from the merchant's TouchBistro Cloud account
2. Meridian (as approved partner) provisions an API key tied to that restaurant
3. Merchant confirms data-sharing authorization with TouchBistro (partner-mediated)
4. Meridian pulls historical orders + ongoing daily sync via `cloud.touchbistro.com/api/v1`

## Estimated effort to go LIVE (config → production-ready)
XL — gated by partner agreement, not engineering.

## What blocks LIVE status today
- No executed integration partner agreement with TouchBistro
- Endpoint paths in registry are unvalidated against current TouchBistro partner docs
- No customer-facing connect UI (key-paste flow at minimum, once keys can be issued)
- Sandbox + rate-limit behavior unknown until partner onboarding

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401/403 on `/restaurants/{id}/...` → **Likely cause:** API key not scoped to that restaurant_id → **Fix:** request scoped key from TouchBistro partner contact
- **Symptom:** 404 on documented endpoints → **Likely cause:** registry config drift vs current API → **Fix:** validate paths against partner docs before launch

## Strategic notes
TouchBistro is one of the highest-priority Canadian POS targets for Meridian: Toronto HQ, deep TD Bank distribution, and a Canadian customer base that mirrors Meridian's Canada portal ICP almost exactly. They deliberately gatekeep the API to protect competitive migration, so progress is a relationship game — not a documentation race. Lead with the analytics-only, read-only, no-order-push framing; that posture historically clears their partner review faster than full bidirectional asks. Existing integrations (7shifts, WISK, MarginEdge, Deliverect) prove third parties do get approved.

## Recommendation
WAIT — begin partner outreach now, build later.

**Reasoning:** Meridian Canada portal cannot ignore TouchBistro, but eng effort is wasted until a signed partner agreement and validated API key exist. Email `integratedpartners@touchbistro.com` this week; defer UI/connector hardening until access is granted.

## Sources consulted
- https://www.touchbistro.com/features/integrations/
- https://help.touchbistro.com/s/topic/0TO4T000000kDzKWAU/third-party-integrations
- https://apitracker.io/a/touchbistro
- https://reformingretail.com/index.php/2019/01/23/why-do-some-cloud-pos-companies-still-lack-apis/
- https://enlyft.com/tech/products/touchbistro
- https://www.businesswire.com/news/home/20260127249555/en/Restaurants-Post-Strong-Margins-in-Uneven-Recovery-TouchBistros-2026-Canadian-State-of-Restaurants-Report
- Live API docs accessed: No (partner-gated)
