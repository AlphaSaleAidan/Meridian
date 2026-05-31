# Petpooja

**Registry key:** `petpooja` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP / UNCERTAIN — config shaped (`X-Api-Key`; `/orders`, `/menu`, `/restaurants`; `supports_orders: True`) but `base_url` `https://api.petpooja.com/v2` not validated against published docs, and access is partner-gated.

## What it is
India-HQ all-in-one restaurant suite (POS, billing, inventory, aggregator integrations, captain app) from Prayosha Food Services Pvt. Ltd. (Ahmedabad).

## Vertical & market
- **Primary vertical:** restaurant (QSR, casual dining, cafes, cloud kitchens)
- **Estimated NA market presence:** Small — marketing names Canada with UAE/MENA/SA; India is the stronghold
- **Typical merchant profile:** Indian SMB restaurant, often multi-outlet, heavy Swiggy/Zomato dependency; 150k+ businesses claimed
- **Geographic concentration:** International — dominant India (200+ cities); some UAE/MENA/SA, limited Canada

## How to spot the merchant uses it
- Petpooja-branded biller terminal or tablet running Merchant App
- Captain app on phones for table-side ordering
- Swiggy/Zomato/Dunzo/Magicpin run from one dashboard
- Tells: "Petpooja billing/captain," `merchant.petpooja.com` admin URL

## Auth method
API key in `X-Api-Key` header. Keys + `restaurantid`s are partner-issued — not self-serve.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Cfg | `/orders` | Unverified |
| Catalog / items | Cfg | `/menu` | Unverified |
| Customers | ✗ | — | — |
| Employees | ✗ | — | — |
| Inventory | ✗ | — | — |
| Refunds | ✗ | — | — |

`supports_orders: True`, `order_create_endpoint: /orders`, `order_id_field: orderid` — UNVERIFIED.

## Partner program / access requirements
- **Partner program required:** Yes — Integration Partner Program
- **Sign-up URL:** `https://www.petpooja.com/poss/restaurant-integrations`
- **Approval timeline:** UNCERTAIN — no published SLA
- **Cost / revenue share:** Unknown publicly

## Sandbox / test environment
- **Available:** UNCERTAIN — public Apiary doc has mock + proxy hosts; prod base is a placeholder, implying partner-issued URLs
- **URL:** N/A publicly
- **Notes:** `pos-systems.ts` has `sandboxAvailable: false`

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only; `webhooksSupported: false` in frontend.

## Connect flow (what the merchant does)
1. Merchant (or Meridian) requests integration via the Partner Program
2. Petpooja issues API key + `restaurantid`(s)
3. Merchant pastes credentials into Meridian connect screen
4. Meridian sends `X-Api-Key` to `base_url` for `/restaurants`, `/menu`, `/orders`

## Estimated effort to go LIVE
L (1+ months) — partner approval, endpoint verification, connect UI.

## What blocks LIVE status today
- No partnership; API key issuance is gated
- `base_url` not confirmed against current partner docs
- No customer-facing connect UI; no NA merchant in pipeline
- Sandbox unverified; payload shapes guesswork until a partner spec lands

## Common failure modes
- 401/403 on `/restaurants` → no partner key or wrong host → confirm onboarding and partner URL
- empty `/menu` → missing `restaurantid` scoping → confirm ID with Petpooja
- order create OK in mock, fails in prod → mock vs partner-prod divergence → re-pull partner spec

## Strategic notes
Credibly one of India's largest restaurant POS footprints by merchant count, but materially off Meridian's NA ICP. The Canada marketing mention isn't backed by merchant density a rep can source from.

## Recommendation
DEFER.

**Reasoning:** Off-ICP, and the API path needs a gated partner relationship with no deal driving it. Revisit only if a qualified multi-outlet Petpooja merchant (likely a Canadian Indian-cuisine group) lands in pipeline.

## Sources consulted
- https://www.petpooja.com/ ("150k+ Businesses")
- https://www.petpooja.com/poss/restaurant-integrations (Partner Program)
- https://onlineorderingapisv210.docs.apiary.io/ (mock + placeholder prod)
- Internal: `src/services/pos_connectors/registry.py`; `frontend/src/data/pos-systems.ts`
- Live API docs accessed: Partial (marketing + Apiary header; prod not verifiable without key)
