# Heartland Retail

> Status: **WAVE 1.5 BUILDING — fastest win on the board**
> Category: retail (multi-vertical — apparel, specialty, gift, home goods)
> Auth: Bearer token (self-serve from dev portal — NO partner gate)

## What you tell the merchant

"Heartland Retail is one of the few Heartland products with a self-serve API — no partner program, no waiting. You generate an API token in Heartland's dev portal, paste it into Meridian, and we start backfilling. First insights inside 24 hours of connect."

## How the merchant connects (when live)

1. **dev.retail.heartland.us** → sign in with Heartland Retail owner credentials → **Create API token**
2. Paste the token into Meridian's **Settings → POS Connections → Connect Heartland Retail**
3. We hit `/stores` to verify and start the backfill
4. Multi-store merchants paste one token per store

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Sales | hourly poll | 18 months |
| Items (catalog) | daily | full history |
| Customers | daily | full history |
| Users (employees) | daily | full history |
| Stores (locations) | daily | full history |

Endpoint reference: `https://api.springboardretail.com/api/v1` (Springboard Retail is the underlying product — Heartland Retail is the rebrand)

## What features they get (when live)

Multi-vertical retail suite:

- Money Left on Table (cart abandons, basket size misses, lost regulars)
- Product velocity + inventory intelligence (reorder timing per SKU)
- Customer LTV + churn (Heartland Retail has clean customer IDs)
- Pricing power per category
- Employee performance (per-cashier revenue, average ticket, attach rate)
- Day-of-week / time-of-day patterns
- Multi-store rollups (when merchant has tokens for each store)

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Heartland Restaurant data — that's a separate connector (see [heartland-restaurant.md](./heartland-restaurant.md))
- Heartland Portico / payment-only merchants — Portico is a payments gateway, not a POS; no analytics surface

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 after working for months | Bearer token revoked when Heartland account downgraded | Merchant regenerates token in dev portal — one-click reconnect preserves history |
| Only one store's data showing | Multi-store merchant only pasted one token | Each store needs its own token; add each in Meridian settings |
| Catalog rows missing | Item flagged inactive in Heartland | Inactive items don't appear in `/items`; verify in Heartland admin |
| Merchant confused which Heartland they have | Heartland sells 4+ distinct products | If their dashboard URL is `*.springboardretail.com` or `*.retail.heartland.us` — it's Heartland Retail. Other URLs = different product. |

## Sales angle

**Opener:** "You're on Heartland Retail — which is good news for you, because it's the one Heartland product with a real API. We pull your sales, your inventory turn, your top customers, and tell you exactly where you're leaving money. Most Heartland merchants get told 'no API' — that's true for Restaurant and Portico, not for you."

**Why Heartland Retail is the wedge:**
- Fastest connector to build on the entire add list (small effort, self-serve auth)
- Specialty retail merchants (apparel, gift, home goods) are an underserved analytics market — most analytics tools target restaurants
- Self-serve token means no partner gate, no waiting — we can promise a real timeline
- The compound `heartland` registry entry tried to cover Restaurant + Retail + Portico in one config and failed; Heartland Retail (Springboard rebrand) is the clean split

**Competitive notes:** If a prospect says "I'm on Heartland" — qualify which one. Restaurant is partner-gated (separate playbook). Portico is payments-only. Retail is the only one we can connect to fast.

## What blocks live status today

- Connector implementation (config landed, OAuth UI build in progress)
- First Heartland Retail merchant for beta validation

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (heartland-retail config) + docs/playbook/_status/phase-2-decisions.md (Wave 1.5 adds, "fastest win" framing) + docs/playbook/_status/pos-expansion-candidates.md (heartland-retail high-priority entry)_
