# Lavu

**Registry key:** `lavu` — see `src/services/pos_connectors/registry.py`

## Status
OUTDATED CONFIG — registry points at an undocumented `api.lavu.com/v1` + `X-Api-Key` shape; the public Lavu API is actually `admin.poslavu.com/cp/reqserv` with POST `dataname`/`token`/`key`. Self-service credentials, no partner gate, but the connector won't authenticate until rewritten.

## What it is
iPad-based cloud restaurant POS founded 2010 in Albuquerque, NM; strongest in pizzerias, bars, breweries, food trucks, and small full-service / QSR independents.

## Vertical & market
- **Primary vertical:** restaurant (pizzeria, bar/brewery, QSR, food truck, cafe, full-service)
- **Estimated NA market presence:** Medium (independents); behind Toast and Square for Restaurants but established
- **Typical merchant profile:** 1–5 location independent operator on iPads; price-sensitive (Freedom Plan $9.99/mo with required Lavu Pay processing, Core ~$59/mo annual)
- **Geographic concentration:** US-dominant, some international

## How to spot the merchant uses it
- iPads on stands or handheld, no proprietary terminal hardware
- Server/manager login screen branded "Lavu"
- Back-office URL: `admin.lavu.com/cp/` (legacy `admin.poslavu.com/cp/`)
- Conversational tells: "we use Lavu," "Lavu Pay," mentions of Freedom Plan / no processing fees, or Lavu's add-ons (MenuDrive online ordering, Sourcery invoicing)

## Auth method
API key (POST body) — credentials (`dataname`, `token`, `key`) are issued automatically inside the merchant Control Panel; not OAuth, not header-based, not partner-gated. Registry's `X-Api-Key` header on `api.lavu.com/v1` does not match the documented Lavu endpoint.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Likely ✓ once rewritten | `orders`, `order_contents`, `order_payments` tables via `reqserv` | Registry's `/orders` will not resolve |
| Catalog / items | Likely ✓ once rewritten | `menu_items`, `menu_categories`, `menu_groups` tables | Registry's `/menus/items` will not resolve |
| Customers | Unconfirmed | — | Not in current registry; not in the table list scraped from public docs |
| Employees | Likely ✓ once rewritten | `employees` (per registry) — confirm exact table name | |
| Inventory | Likely ✓ | `ingredients`, `ingredient_usage` | Lavu has full ingredient-level inventory |
| Refunds | Unconfirmed | Probably surfaced inside `order_payments` | Validate during rewrite |

`supports_orders: True` in registry — UNVERIFIED. Order push via the `reqserv` table API is not documented in the public surface; treat as read-only until confirmed.

## Partner program / access requirements
- **Partner program required:** No for read access — any active Lavu merchant can pull their own credentials. Formal "Integration Partner" listing on `lavu.com/integrations/` is a separate marketing/co-sell motion (contact Lavu sales).
- **Sign-up URL:** Merchant pulls credentials at `admin.lavu.com/cp/` → Settings → Printer/Technical → API
- **Approval timeline:** Self-service (credential paste flow); partner listing is a separate, slower BD conversation
- **Cost / revenue share:** No documented developer fee for using the merchant's own API credentials

## Sandbox / test environment
- **Available:** UNCERTAIN — no public sandbox documented
- **URL:** N/A publicly
- **Notes:** Lavu's parent company / ownership and any partner sandbox program are not confirmed in public sources

## Rate limits
Unknown — not publicly documented.

## Webhook / sync model
Poll-only based on public docs. No webhook surface confirmed.

## Connect flow (what the merchant does)
1. Merchant logs into `admin.lavu.com/cp/`
2. Settings → Printer/Technical → API tab
3. Copies `dataname`, `token`, `key` into Meridian's connect screen
4. Meridian backfills historical orders + daily poll against `admin.poslavu.com/cp/reqserv`

## Estimated effort to go LIVE (config → production-ready)
M (1–2 weeks) — primarily a rewrite of the `lavu` registry entry to the `reqserv` POST-table shape plus a custom adapter (it doesn't fit the generic REST connector cleanly), then a key-paste UI.

## What blocks LIVE status today
- Registry `base_url`, `auth_type`, and endpoint paths do not match the actual Lavu API surface
- `GenericRESTConnector` likely cannot handle Lavu's POST-body-credential + `table=name` query pattern — needs a small Lavu-specific adapter
- No customer-facing key-paste UI
- Order-push capability (`supports_orders: True`) is unverified and should default to False until confirmed

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 404 on `/orders` or `/menus/items` → **Likely cause:** wrong base URL; the real endpoint is `admin.poslavu.com/cp/reqserv` with `table=orders` in the POST body → **Fix:** rewrite registry entry, build Lavu adapter
- **Symptom:** 401/403 → **Likely cause:** stale `token` (merchant rotated keys in Control Panel) → **Fix:** prompt re-paste from API tab
- **Symptom:** empty `data` array → **Likely cause:** querying old `admin.poslavu.com` host after Lavu's URL migration → **Fix:** confirm host with merchant; docs flagged a URL change

## Strategic notes
Lavu sits squarely in Meridian's ICP — independent pizzeria/bar/QSR operators who are exactly the segment overpaying for analytics. Self-service credentials make this one of the cheapest integrations on the board *if engineering rewrites the connector*; there is no TouchBistro-style partner moat to wait on. Lead with the Freedom Plan crowd (margin-sensitive, no-fee operators) — they feel the value of analytics fastest. Do not pitch order-push until that capability is verified against the actual table API. Note: the brief's claim that Lavu is owned by "Roller Holdings" could not be verified in public sources (Lavu Inc., Albuquerque NM, founded 2010; last documented acquisition was Sourcery in 2019, by Lavu) — treat ownership framing as unconfirmed.

## Recommendation
BUILD NOW (after registry fix).

**Reasoning:** Self-service auth and a high-fit ICP make Lavu a fast win versus partner-gated peers, but the current registry config will not authenticate against the real API and must be rewritten before any connect flow ships.

## Sources consulted
- https://lavu.com/integrations/
- https://lavu.com/customization-king-pos-systems-open-apis/
- https://lavu.com/about-lavu/
- https://lavu.com/2025-best-restaurant-pos/
- https://www.nerdwallet.com/business/software/reviews/lavu-pos
- https://www.merchantmaverick.com/reviews/pos-lavu-review/
- http://admin.poslavu.com/cp/areas/api_doc.html
- https://github.com/willglynn/poslavu
- https://www.crunchbase.com/organization/lavu
- Live API docs accessed: Partial (public `api_doc.html` page; full per-table reference is behind merchant login)
