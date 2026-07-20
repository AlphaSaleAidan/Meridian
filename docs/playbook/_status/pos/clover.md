# Clover

**Registry key:** `clover` — see `src/services/pos_connectors/registry.py`

## Status
LIVE

## What it is
Android POS for SMBs, owned by Fiserv — largest US cloud POS by volume.

## Vertical & market
- **Primary vertical:** multi-vertical; strongest restaurant + retail
- **NA presence:** Dominant (~$133B+ annualized)
- **Typical merchant:** single/few-location SMB sold via Fiserv/bank/ISO
- **Geo:** US-led; also CA / UK / EU / LATAM

## How to spot the merchant uses it
- White-and-green Clover **Station / Mini / Flex / Mobile / Go** on the counter
- Receipts + customer-app pings reference Clover
- Merchant logs in at `clover.com`, uses the Clover App Market
- Tell: "we got it from our bank" / "Fiserv set us up"

## Auth method
OAuth 2.0 auth-code (`auth_type: "bearer"`). Published apps now receive **expiring** tokens; `oauth.py` lacks refresh (see blockers).

## Data we can pull (per current config)
All paths under `/v3/merchants/{mId}/`.

| Type | Avail | Path |
|---|---|---|
| Orders | yes | `/orders` (`expand=lineItems,payments`; ms `clientCreatedTime` filter) |
| Catalog | yes | `/items` (`expand=categories,modifierGroups,tags`) |
| Categories | yes | `/categories` |
| Customers | yes | `/customers` |
| Employees | yes | `/employees` |
| Inventory | yes | `/item_stocks` |
| Payments | yes | `/payments` (`createdTime` filter) |
| Refunds | partial | `/refunds` (90-day window; not wired) |

Arrays wrap in `"elements"`; pagination is **offset + limit** (`page_size: 100`) — not Square-style cursor.

## Partner program / access requirements
- **Required:** Yes — https://www.clover.com/developers; publish via Clover App Market
- **Timeline:** Sandbox immediately; first App Market review ~1–2 weeks
- **Cost:** Free dev account; paid apps rev-share

### Dashboard app permissions (as of 2026-07-20)
App "Meridian Ai Business Support" (`YK86AE2YAHSP2` = `CLOVER_APP_ID`), still **DRAFT** — no App Market release submitted, 0 merchant installs.

| Category | Read | Write |
|---|---|---|
| Orders | ✓ | ✓ (added 2026-07-20) |
| Customers | ✓ | ✓ (added 2026-07-20) |
| Inventory | ✓ | — |
| Merchant | ✓ | — |
| Payments | ✓ | — |
| Employees | — | — |

Write scopes only reach tokens issued AFTER this change (new/re-authorizations). ⚠️ Employees Read is unchecked on the dashboard, yet `client.py` calls `/employees` and this doc claims daily employee pulls — verify `list_employees()` against a token from this app, or request Employees Read.

## Sandbox / test environment
- **Available:** Yes — `sandbox.dev.clover.com` (OAuth) + `apisandbox.dev.clover.com` (REST). Prod: `clover.com` / `api.clover.com`.
- **Notes:** Test tokens have extra rate-limit restrictions in prod — never reuse live.

## Rate limits
Tighter than Square. `rate_limiter.py` enforces **12 req/sec sustained, 16 burst per token** (token bucket). Clover documents `429 Too Many Requests` but no per-endpoint SLA — 16/sec is our safe internal bound. Apps sharing a token share the budget; client backs off on 429/5xx.

## Webhook / sync model
Hybrid. Real-time webhooks (`ORDER`/`ITEM`/`INVENTORY` CRUD + `APP DELETE`) signed **HMAC-SHA256**. Payloads carry only `{type, objectId, ts}` — handlers re-fetch. 15-min incremental poll + 18-month backfill in monthly chunks.

## Connect flow (what the merchant does)
1. Meridian Settings → **Connect POS** → **Clover**
2. Clover **Authorize** screen — approve Meridian
3. Clover redirects to `redirect_uri` with `code` + `merchant_id`
4. Backend exchanges at `/oauth/token`; backfill starts

## Estimated effort to go LIVE
LIVE — pipeline shipped under `src/clover/`.

## What blocks LIVE status today
- Token refresh not implemented — tokens now expire; long-lived connections will silently 401
- No `list_refunds()` wrapper in `client.py`
- Webhook dispatch needs `_entity_type` stamped during parse from subscription metadata

## Common failure modes (for troubleshooting playbook)
- **Backfill stalls ~50%** → 429 throttling → share `standard_limiter` across workers, not per-task
- **401 after weeks** → token expired or app uninstalled → `oauth.verify_token`; if dead, reconnect via `APP DELETE` path
- **Webhook 200, no DB write** → missing `_entity_type` → stamp entity from subscription verification code

## Strategic notes
Highest-leverage SMB integration — Fiserv's bank/ISO channel reaches merchants we couldn't direct. Pitch: "we speak Clover natively" vs. CSV-only competitors.

## Recommendation
BUILD NOW (built — protect and harden)

**Reasoning:** LIVE; unlocks the largest US SMB POS base. Remaining work small vs. deal flow.

## Sources consulted
- `docs.clover.com`: `/dev/reference/paygetrefunds-3`, `/dev/reference/createcharge`, `/dev/docs/generate-a-test-api-token`, `/dev/docs/faqs`, `/dev/changelog`
- `en.wikipedia.org/wiki/Clover_Network`
- Live API docs accessed: Yes (via Context7; WebFetch returned 403)
