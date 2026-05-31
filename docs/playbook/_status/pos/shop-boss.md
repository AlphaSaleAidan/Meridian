# Shop-Boss

**Registry key:** `shop-boss` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP / UNCERTAIN — registry config exists with `X-Api-Key` header auth, but partner access path and live API docs are not first-party verified.

## What it is
Cloud-based auto repair shop management software (work orders, customers, services) used by independent auto repair shops as their system of record.

## Vertical & market
- **Primary vertical:** automotive — independent auto repair shops
- **NA market presence:** Small vs category leaders (Tekmetric, Shopmonkey, Shop-Ware); established long-tail player
- **Typical merchant:** independent repair shop on a Shop Boss subscription
- **Geography:** US (per shopboss.net)

## How to spot the merchant uses it
- Service writer working out of `app.shopboss.net`
- Conversational tells: "we run on Shop Boss"
- (Hardware / receipt cues not first-party verified.)

## Auth method
API key via `X-Api-Key` header (per `registry.py`). Merchant generates the key inside Shop Boss and supplies it with an Account ID. No OAuth, no webhooks.

## Data we can pull (per current config)
- **Configured:** work orders (`/work-orders`, read-only — `supports_orders: False`), services (`/services`), customers (`/customers`)
- **Not configured:** employees, inventory (frontend claims inventory; registry has no endpoint), refunds (unknown if exposed)
- **Test endpoint:** `/shops`. **Base URL:** `https://app.shopboss.net/api/v1`.

## Partner program / access
- **Partner program required:** Unknown — no public portal located
- **Sign-up URL / timeline / rev share:** Unknown

## Sandbox
Frontend metadata says yes; not first-party verified. No URL in registry.

## Rate limits
Unknown — not documented in any first-party source we have.

## Webhook / sync model
Poll-only. No webhook support in current config.

## Connect flow (what the merchant does)
1. Log in to Shop Boss
2. Settings → API → generate API key
3. Copy Account ID from Settings
4. Paste both into Meridian (UI not yet built)

## Estimated effort to go LIVE
L (1+ months) — gated on first-party API doc access, partner contact, and validation of every configured endpoint; Meridian also has no auto-shop dashboards.

## What blocks LIVE status today
- **No verified API docs.** Endpoint paths in `registry.py` were scaffolded without confirmed first-party docs.
- **Partner access path unknown.** No located developer portal or self-service key flow.
- **No connect UI** in Meridian.
- **Off-ICP vertical.** No auto-repair dashboards or automotive buyer motion.

## Common failure modes
- **401 on every call** → wrong header or unprovisioned key → confirm `X-Api-Key` spelling; re-issue key.
- **Auth works, endpoints 404** → unverified paths → validate `/work-orders`, `/services`, `/customers` against live responses before promising data.
- **No real-time updates** → no webhooks → expected; poll on a schedule.

## Strategic notes
Auto repair is outside Meridian's core ICP (F&B + retail SMBs on Square/Clover/Toast). Shop Boss is also smaller than Tekmetric, Shopmonkey, and Shop-Ware, with less verifiable API surface than any of them. Reps should not prospect auto shops; if an inbound merchant on Shop Boss appears, log the lead and flag for product — do not promise a timeline or sandbox demo.

## Recommendation
DEFER (off-ICP).

**Reasoning:** Off-ICP automotive vertical, unverified API config, no confirmed partner path, and a smaller install base than the auto-shop leaders we already defer on. Revisit only if Meridian commits to an automotive expansion.

## Sources consulted
- `src/services/pos_connectors/registry.py` (entry `shop-boss`, lines 531–542)
- `frontend/src/data/pos-systems.ts` (entry `shop-boss`, lines 2255–2308)
- https://www.shopboss.net (vendor site, surface-level only)
- Live first-party API docs accessed: No
