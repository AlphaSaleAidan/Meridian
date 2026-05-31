# IndicaOnline

**Registry key:** `indica-online` — `src/services/pos_connectors/registry.py` (lines 1167-1181)

## Status
**OUTDATED CONFIG** — registry says `auth_type: csv_only`, but IndicaOnline ships an Open API (v2.0.0) covering Customer, Delivery Address, Product, Inventory, Order, Office, Location, Staff, File. API exists but unverified (`apidocs.indicaonline.com` 403s — credentials gated).

## What it is
LA-based cannabis dispensary POS (retail, delivery, ecom menu, METRC) for CA single- and small-multi operators.

## Vertical & market
- **Vertical:** Cannabis dispensary (retail + delivery)
- **NA presence:** Small-to-Medium — mid-tier behind Dutchie / Cova / Treez; peer to Meadow / Blaze
- **Typical merchant:** Single-location CA dispensary or delivery operator
- **Geo:** US (CA-heavy); marketing toward Canada and intl

## How to spot it
- iPad with IndicaOnline app at counter; admin URLs on `indicaonline.com`
- Mentions "IndicaOnline" or "IndicaOnline AI" (MCP analytics, May 2026)
- Springbig / Weedmaps / Leafly wired in

## Auth method
**Unverified — likely API key issued by support.** Credentials via `support@indicaonline.com` / (888) 420-4207. Header name/format not public. Do not assume CSV-only.

## Data we can pull (registry vs. real API)
| Type | Registry | Real API |
|------|----------|----------|
| Orders | CSV only | Order API (also accepts inbound push) |
| Catalog | — | Product API |
| Customers | — | Customer API (patient PII) |
| Inventory | — | Inventory API |
| Employees | — | Staff API |
| Locations | — | Location / Office APIs |
| Delivery | — | Delivery Address API |

`supports_orders: False` in registry is wrong — inbound order push is documented.

## Partner / access
- Required (soft): `/partnership/` form, type "Integration"
- Credentials: `support@indicaonline.com` / (888) 420-4207
- Approval: not published — plan 2-4 weeks
- Cost / rev share: not publicly documented

## Sandbox / rate limits / webhooks
None publicly documented. Plan poll-only until partner intake confirms.

## Connect flow (merchant)
1. Meridian files `/partnership/` intake + emails support for credentials
2. Dispensary enables Open API (admin path unconfirmed)
3. Merchant pastes API key into Meridian
4. Meridian tests a real endpoint before unlocking dashboard

## Effort to LIVE
**M-L (2-6 weeks)** — rebuild registry from CSV stub to REST config, validate endpoints, build cannabis connect UI.

## What blocks LIVE
- Registry CSV stub contradicts live product — needs real `base_url`, `auth_type`, `auth_header_name`, endpoints
- Docs portal gated — no spec validation without partner intake
- No customer-facing cannabis connect UI; no PII / METRC review

## Common failure modes
- **Rep pitches "CSV upload only"** → registry mislabel → wastes partnership lever
- **401 everywhere** → header guessed → confirm literal with support
- **Empty results** → per-location scoping → confirm Office / Location on the key

## Strategic notes
Mid-tier CA cannabis — peer to Meadow / Blaze. May 2026 IndicaOnline AI launch (MCP over the Open API) signals API investment but doesn't change merchant count. Standalone, doesn't justify cannabis lift. As a fast-follow after Dutchie / Cova / Treez, pairs with Meadow to cover CA boutique / delivery long tail.

## Recommendation
**WAIT if cannabis greenlit; DEFER if pursuing only top-3 (Dutchie / Cova / Treez).**

**Reasoning:** Real Open API exists, so upside is higher than CSV stub implies — but cost is M-L and merchant count doesn't justify it ahead of top three. Fix the registry mislabel either way.

## Sources consulted
- https://indicaonline.com/open-api/
- https://indicaonline.com/integrations/open-api/
- https://indicaonline.com/integrations/
- https://indicaonline.com/partnership/
- https://apidocs.indicaonline.com/docs (403 — gated)
- https://releasenotes.indicaonline.com/release/KY4qS-open-api-200
- May 2026 PR Newswire — IndicaOnline AI MCP layer
- `registry.py` lines 1167-1181
- Live API docs accessed: No (gated)
