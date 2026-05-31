# Posist (Restroworks)

**Registry key:** `posist` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP / UNCERTAIN — registry has a plausible base URL and `X-Api-Key` config, but the company rebranded to Restroworks and the live `api.posist.com/x/v1` host and paths are unvalidated against current docs.

## What it is
India-founded cloud restaurant management platform (POS, KOT, inventory, CRM, analytics) for full-service, QSR, cloud kitchens, and chains; rebranded from "Posist" to "Restroworks."

## Vertical & market
- **Primary vertical:** restaurant (full-service, QSR, cloud kitchen, multi-unit chain)
- **Estimated NA market presence:** Small — no documented NA chain footprint in Meridian's ICP
- **Typical merchant profile:** multi-unit restaurant or chain operator in India, GCC/Middle East, or SE Asia
- **Geographic concentration:** International — India-dominant, expanding Middle East (UAE/Saudi); minimal NA

## How to spot the merchant uses it
- "Posist" or "Restroworks" branding on tablet/terminal login screens
- Owner/operator with India or GCC roots; chain operating in India or Middle East
- Conversational tells: "Posist," "Restroworks," "KOT printer," India/GCC chain terminology

## Auth method
API key in `X-Api-Key` header (per registry). Per-merchant provisioning model not verified against current Restroworks partner program.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Configured | `/tabs` | Endpoint UNVERIFIED against live docs |
| Catalog / items | Configured | `/menuitems` | Endpoint UNVERIFIED |
| Customers | ✗ | — | Not configured |
| Employees | Configured | `/users` | Endpoint UNVERIFIED |
| Inventory | ✗ | — | Not configured |
| Refunds | ✗ | — | Not configured |

`supports_orders: False` in registry — read-only by current config; no order-create path wired.

## Partner program / access requirements
- **Partner program required:** Likely yes — UNCERTAIN under Restroworks branding
- **Sign-up URL:** Unknown — no NA-facing developer portal surfaced
- **Approval timeline:** UNCERTAIN
- **Cost / revenue share:** Unknown

## Sandbox / test environment
- **Available:** UNCERTAIN — no public sandbox confirmed

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only per current config.

## Connect flow (what the merchant does)
1. Merchant requests API key from Restroworks account team (process unverified)
2. Merchant pastes key into Meridian connect screen
3. Meridian sends `X-Api-Key` against `/restaurant` to test, then polls `/tabs`, `/menuitems`, `/users`

No customer-facing connect UI exists.

## Estimated effort to go LIVE
L (1+ months) — partner outreach, post-rebrand API validation, customer-facing UI, NA-qualified pilot merchant.

## What blocks LIVE status today
- Rebrand to Restroworks — current host and paths unvalidated against post-rebrand docs
- No partner relationship with Restroworks
- No customer-facing connect UI; no NA pilot merchant

## Common failure modes
- **Symptom:** `/restaurant` 404 or DNS failure → **Likely cause:** legacy host moved under Restroworks → **Fix:** confirm current base URL with Restroworks partner team
- **Symptom:** 401 on `X-Api-Key` → **Likely cause:** key format or header name changed post-rebrand → **Fix:** verify against current docs

## Strategic notes
Posist/Restroworks is a real, sizeable platform in its home markets (India, expanding Middle East) but absent from Meridian's NA ICP. The rebrand adds uncertainty — the registry predates Restroworks and may point at stale infrastructure. Not worth spec work until a qualified India or GCC chain lands in pipeline.

## Recommendation
DEFER.

**Reasoning:** Off-ICP for Meridian's NA motion, no partner relationship, and the post-rebrand API surface is unverified — no engineering or partnership investment until a qualified international deal forces it.

## Sources consulted
- `src/services/pos_connectors/registry.py` (`posist` key)
- Live API docs accessed: No
