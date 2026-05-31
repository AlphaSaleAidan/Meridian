# Aldelo POS

**Registry key:** `aldelo` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN — registry shape is plausible but `base_url` (`https://api.aldelo.com/v1`) is **not the public API host**. Live docs at `doc.aldelo.io` are Postman-hosted; auth scheme in registry (`X-API-Key` header) is consistent with Aldelo's Developer Dashboard key model but unverified against a live call.

## What it is
Long-established small-restaurant POS, founded 1999. Two lines: **Aldelo Pro** (legacy Windows on-prem) and **Aldelo Express** (cloud iPad). Only Express has a public REST API.

## Vertical & market
- **Primary vertical:** restaurant (independent FSR, QSR, pizza, cafes, bars)
- **NA presence:** Medium — decades-old base of single-location independents; historical strength in Asian-American operators
- **Typical merchant:** 1-location owner-operator, $300k–$1.5M revenue
- **Geo:** US (HQ Pleasanton, CA)

## How to spot the merchant uses it
- Windows cash terminal with on-prem PC tower (Aldelo Pro tell)
- iPad terminal with Aldelo Express branding on order screen / receipts
- EVO-branded PIN pad (EVO is the preferred Express payments partner)
- Tell: "we've had Aldelo forever"

## Auth method
**API key in `X-API-Key` header** per registry. Consistent with Aldelo's Developer Dashboard key model; not verified against a live response.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | configured | `/transactions` | `supports_orders: False` — totals only |
| Catalog / items | configured | `/menus` | |
| Customers | not configured | — | |
| Employees | configured | `/employees` | |
| Inventory | not configured | — | |
| Refunds | not configured | — | |

Test endpoint `/restaurants`, envelope key `data`. None validated against a live call.

## Partner program / access requirements
- **Partner program required:** Yes — Aldelo Developer Partners, gated by Developer Dashboard enrollment
- **Sign-up URL:** `aldelo.com/developers.html` (404 at time of writing); live docs at `doc.aldelo.io`
- **Approval timeline:** Unpublished. "Free for qualified developers" implies a review step
- **Cost / revenue share:** Not disclosed

## Sandbox / test environment
- **Available:** Unverified — Developer Dashboard generates "development keys" per marketing, but no public sandbox URL confirmed
- **URL:** Unknown

## Rate limits
Not publicly documented.

## Webhook / sync model
Unknown — assume poll-only until confirmed.

## Connect flow
1. Merchant provides Aldelo Express account email (Pro merchants cannot connect)
2. We use Developer Dashboard key plus merchant authorization (flow unverified)
3. Pull sales summaries via `/transactions`

Aldelo Pro: CSV/SMS fallback only.

## Estimated effort to go LIVE
**L (1+ months)** — Dashboard enrollment, validate actual base URL, confirm auth live, build merchant-auth handshake.

## What blocks LIVE today
- Registry `base_url` returns 403 from Microsoft IIS — not the docs surface
- No Developer Dashboard account on file
- Aldelo Pro has no cloud API — bifurcates the strategy
- Merchant-authorization flow undocumented externally

## Common failure modes
- **Symptom:** "I use Aldelo" but no cloud login → **Cause:** Aldelo Pro, not Express → **Fix:** CSV/SMS fallback
- **Symptom:** `api.aldelo.com/v1` returns 403 → **Cause:** wrong host in registry → **Fix:** confirm base URL via Developer Dashboard first

## Strategic notes
Aldelo's base skews to single-location independents, **below Meridian's SLA threshold**. The Pro/Express split means a successful API build only reaches a fraction of "Aldelo" merchants. EVO's preferred-payments relationship is a possible future channel lever, not a near-term asset.

## Recommendation
**DEFER**

**Reasoning:** Small independents under the SLA threshold, plus the Pro/Express split and an unverified registry config, mean integration cost outweighs near-term revenue. Re-evaluate if an EVO channel relationship materializes or SLA economics shift.

## Sources consulted
- https://www.aldelo.com/api.html
- https://doc.aldelo.io/ (Postman-hosted, reachable)
- https://www.aldelo.express/developerapi.html
- https://www.evopayments.us/evo-is-now-a-preferred-partner-of-aldelos-cloud-pos-and-payment-solution/
- https://apitracker.io/a/aldelo (base endpoint and auth fields blank)
- Live API docs accessed: Partial — `doc.aldelo.io` reachable; `api.aldelo.com` returns 403 (IIS), suggesting registry base URL is wrong
