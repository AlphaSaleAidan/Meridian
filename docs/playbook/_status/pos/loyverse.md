# Loyverse

**Registry key:** `loyverse` — see `src/services/pos_connectors/registry.py`

## Status
READY (config valid, recommend DEFER unless targeting larger Loyverse merchants — see Strategic notes)

## What it is
Loyverse is a free iOS/Android POS app aimed at ultra-small SMBs — single-operator cafes, food trucks, kiosks, small retail shops — run on the merchant's own phone/tablet with optional add-on hardware.

## Vertical & market
- **Primary vertical:** multi-vertical (mix of small-format food service and retail)
- **Estimated NA market presence:** Small-to-Medium (heavier in EMEA, LATAM, APAC than US)
- **Typical merchant profile:** Single-operator or 1–2 employee shops — coffee carts, food trucks, market stalls, small boutiques
- **Geographic concentration:** Global, with heavy international skew; US presence is the long tail of micro-SMBs

## How to spot the merchant uses it
- POS runs on a generic iPad or Android tablet (no branded hardware)
- App icon: orange/red shopping-bag-and-arrow "Loyverse POS" or "Loyverse Dashboard"
- Receipt footer typically reads "Powered by Loyverse"
- Merchant logs in at `loyverse.com` and references "Loyverse Back Office" or "Loyverse Dashboard"
- Conversational tells: "the free POS app," "I run it off my iPad," "Loyverse loyalty"

## Auth method
Bearer token via Loyverse's developer program. Apps are registered at `https://developer.loyverse.com/apps`, and merchants connect by approving the app from their Loyverse account. The registry config uses `auth_type: bearer` against `https://api.loyverse.com/v1.0`. OAuth-style consent flow specifics (authorize/token URLs, scope names) were not verifiable in this pass — Loyverse's API reference is JavaScript-rendered and requires a logged-in fetch.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `GET /v1.0/receipts` | Cursor pagination, 250/page, `after`/`before` date filters |
| Catalog / items | Yes | `GET /v1.0/items` | |
| Customers | Yes | `GET /v1.0/customers` | |
| Employees | Yes | `GET /v1.0/employees` | |
| Inventory | Not configured | — | Loyverse exposes inventory; not in registry today |
| Refunds | Embedded in `/receipts` | `GET /v1.0/receipts` | Refunds typically returned as negative-receipt records |
| Order creation | No | — | `supports_orders: False`; phone agent cannot push orders |

## Partner program / access requirements
- **Partner program required:** No formal partner gate — Loyverse runs an open developer program
- **Sign-up URL:** https://developer.loyverse.com/apps
- **Approval timeline:** Self-service
- **Cost / revenue share:** Free to register (no published rev share)

## Sandbox / test environment
- **Available:** Not verified in this pass; Loyverse historically expects developers to test against a real (free) merchant account
- **URL:** N/A — production-only against `https://api.loyverse.com/v1.0` per registry
- **Notes:** Sign up a Loyverse merchant account for QA seed data

## Rate limits
Not verified live in this pass. Implement defensive client-side throttling and honor `Retry-After` on HTTP 429.

## Webhook / sync model
Poll-only as wired today (cursor + `after`/`before` date window). Loyverse does support webhooks per their developer program, but they are not in the current registry config.

## Connect flow (what the merchant does)
1. In Meridian: **Settings → Integrations → Connect Loyverse**
2. Merchant is redirected to Loyverse, signs into their Loyverse account
3. Merchant reviews and approves the Meridian app's access scopes
4. Redirected back to Meridian; backfill kicks off using `/receipts` with `after`/`before` cursoring
5. First dashboards usable as soon as initial receipt page lands (small merchants finish fast)

## Estimated effort to go LIVE (config → production-ready)
S (1–3 days) — bearer auth, cursor pagination, and standard endpoints; the work is mostly wiring the developer-portal app handshake into Meridian's connect UI.

## What blocks LIVE status today
- No customer-facing connect UI for Loyverse in Meridian
- OAuth/consent flow specifics (authorize URL, scope names, token lifetime) not yet validated against live Loyverse docs
- ICP/pricing concern (see Strategic notes) — engineering effort is cheap, but commercial fit is the real blocker

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Receipts stop importing after page N" → **Likely cause:** Cursor pagination not persisted between sync runs → **Fix:** Confirm `cursor` is being passed forward; reset window via `after`/`before`.
- **Symptom:** "401 Unauthorized" → **Likely cause:** Merchant revoked app access from Loyverse Back Office → **Fix:** Prompt re-connect; tokens are not auto-recoverable.
- **Symptom:** "Missing refund detail" → **Likely cause:** Refunds embedded as negative receipts, not modeled separately → **Fix:** Aggregate negative-total receipts in the normalizer.

## Strategic notes
Loyverse's user base skews to the smallest end of the SMB market — single-operator cafes, food trucks, market stalls — often running monthly revenue well below the threshold where Meridian's **$343/mo** subscription pencils out for the merchant. Self-service OAuth means engineering cost is low, but rep economics are poor unless we specifically target the Loyverse merchants on the larger side (multi-location, higher AOV, or those already paying for Loyverse's Employee/Advanced Inventory add-ons — a signal they have budget).

## Recommendation
DEFER — keep the config warm, but do not prioritize a customer-facing connect UI until we have a qualified Loyverse pipeline of larger merchants. If a rep finds a Loyverse merchant doing real volume (multi-location, paid Loyverse add-ons), flag for fast-track build (S effort).

**Reasoning:** Integration is technically cheap (READY config, no partner gate), but the typical Loyverse merchant cannot justify $343/mo. Build on signal, not speculation.

## Sources consulted
- https://developer.loyverse.com/apps
- https://developer.loyverse.com/docs/
- `src/services/pos_connectors/registry.py` (key: `loyverse`)
- Live API docs accessed: Partial (developer portal landing only; full reference is JS-rendered and behind sign-in)
