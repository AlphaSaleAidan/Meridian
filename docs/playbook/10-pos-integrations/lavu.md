# Lavu

> Status: **WAVE 1 BUILDING** — registry being rewritten to `reqserv` POST-table shape
> Category: restaurant (iPad-based POS, often used by independent restaurants + bars)
> Auth: API key (X-Api-Key header)

## What you tell the merchant

"Lavu support is shipping this month. We connect with an API key you generate from Lavu's control panel. Backfill takes a few hours, first insights inside 24 hours of connect."

## How the merchant connects (when live)

1. Merchant logs into `admin.lavu.com/cp/` → **Settings → Printer/Technical → API**
2. They copy `dataname`, `token`, and `key` (3 fields — not a single API key) into Meridian's **Settings → POS Connections → Connect Lavu**
3. We test against `admin.poslavu.com/cp/reqserv` and start the backfill

Typical time to connect (projected): **3 minutes**.

**No partner program required** for read access — any active Lavu merchant can pull their own credentials. The formal "Integration Partner" listing on lavu.com/integrations/ is a separate marketing/co-sell motion (contact Lavu sales), not required to ship.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll | 18 months |
| Menu items | daily | full history |
| Employees | daily | full history |
| (Customers — limited) | daily | varies |

Endpoint reference: `https://api.lavu.com/v1` (rewrite in progress to `reqserv` POST-table shape — engineering call)

## What features they get (when live)

Restaurant-focused suite:

- Money Left on Table
- Menu engineering
- Peak hours
- Revenue forecasting
- Discount/promo ROI
- Employee performance
- Order creation supported (`supports_orders: True`) — phone agent can push back orders

## What features they DON'T get

- Customer LTV is limited — Lavu's customer module is optional and not universally enabled
- No camera-side reservation data (Lavu doesn't have reservations natively)

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| 404 on `/orders` or `/menus/items` | Wrong base URL — real endpoint is `admin.poslavu.com/cp/reqserv` with `table=orders` in the POST body, not REST-style paths | Engineering rewriting registry to the POST-table shape |
| 401/403 | Stale `token` — merchant rotated keys in Control Panel | Prompt re-paste from the API tab |
| Empty `data` array | Querying old `admin.poslavu.com` host after Lavu's URL migration | Confirm host with merchant; Lavu has flagged URL changes |
| Missing orders | Order saved offline on iPad, not synced | Lavu-side sync issue — outside our control |

## Sales angle

**Opener:** "Are you on Lavu? You've got iPad-level data most POSes don't expose — table turn times, server performance, void patterns. Our agents pull all of that and tell you exactly where you're leaking margin."

**Best fit:** independent restaurants, bars/pubs, small chains (2–5 locations) that picked Lavu specifically for the iPad form factor. Strongest in pizzerias, bars/breweries, food trucks, and small full-service/QSR.

**Why this is the wedge:** Lavu sits squarely in Meridian's ICP — independent pizzeria/bar/QSR operators on tight margins. Self-service credentials (no partner gate, no TouchBistro-style moat to wait on) make this one of the cheapest integrations on the board *once engineering rewrites the connector*. Lead with the **Freedom Plan crowd** ($9.99/mo with Lavu Pay processing — margin-sensitive, no-fee operators) — they feel the value of analytics fastest.

**Operator tells:** iPads on stands or handheld (no proprietary terminal hardware), "we use Lavu," "Lavu Pay," mentions of Freedom Plan / no processing fees, or add-ons like MenuDrive (online ordering) or Sourcery (invoicing).

**Watch out:** Don't pitch order-push until verified against the real `reqserv` table API — `supports_orders: True` in registry is unverified. Don't repeat the "owned by Roller Holdings" claim — Phase 1 couldn't verify it (Lavu Inc., Albuquerque NM, founded 2010).

## What blocks live status today

- **Registry `base_url`, `auth_type`, and endpoint paths do not match the actual Lavu API.** The published shape is `POST admin.poslavu.com/cp/reqserv` with `dataname`/`token`/`key` in the body and `table=<name>` as the query — not REST + `X-Api-Key`.
- **`GenericRESTConnector` likely can't handle Lavu's POST-body-credential + `table=name` pattern** — needs a small Lavu-specific adapter.
- **No customer-facing 3-field paste UI** (dataname / token / key).
- **`supports_orders: True` is unverified** — should default to False until confirmed against the real table API.
- Estimated effort to LIVE: **1–2 weeks** (registry rewrite + adapter + connect UI).

## Reference docs

- Lavu integrations marketing page: https://lavu.com/integrations/
- Open API blog post: https://lavu.com/customization-king-pos-systems-open-apis/
- Public API doc (HTML): http://admin.poslavu.com/cp/areas/api_doc.html
- Reference client (community): https://github.com/willglynn/poslavu
- Nerdwallet review: https://www.nerdwallet.com/business/software/reviews/lavu-pos
- Merchant Maverick review: https://www.merchantmaverick.com/reviews/pos-lavu-review/

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (lavu config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #8, ownership-claim caveat) + docs/playbook/_status/pos/lavu.md (Phase 1)_
