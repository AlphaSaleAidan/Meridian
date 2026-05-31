# Heartland Restaurant

> Status: **WAVE 1.5 BUILDING — partner program required**
> Category: restaurant (Genius-branded cloud restaurant SKU; ~35k venues including Dinerware)
> Auth: X-Api-Key header (partner program required)

## What you tell the merchant

"Heartland Restaurant is a partner-program POS — we've filed our partner application this week. Once Heartland issues us an API key, you paste it and your location ID into Meridian and we backfill. We're targeting ~30–60 days for live status depending on Heartland's partner review."

## How the merchant connects (when live)

1. Meridian partner approval → Heartland issues per-merchant API key
2. Merchant gets the **location_id** from their Heartland Restaurant admin
3. Merchant pastes the **API key** + **location_id** into Meridian's **Settings → POS Connections → Connect Heartland Restaurant**
4. We hit `/locations` to verify and start the backfill

Typical time to connect (projected): **5 minutes** post-partner-approval.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll | 18 months |
| Menu items (catalog) | daily | full history |
| Customers | daily | full history |
| Employees | daily | full history |
| Locations | daily | full history |

Endpoint reference: `https://api.heartland.us/restaurant/v1`

## What features they get (when live)

Restaurant-tuned suite:

- Money Left on Table (void patterns, comps, untaken upsells)
- Menu engineering (item velocity, margin per dish)
- Peak hours (cover-count by time slot)
- Employee performance (per-server revenue, average check, void rate)
- Discount/promo ROI
- Revenue trend + forecasting

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only, no phone-agent push-back
- Heartland Retail data — that's a separate connector (see [heartland-retail.md](./heartland-retail.md))
- Heartland Portico / payment-only merchants — Portico is a payments gateway, not a POS

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Can't get an API key | Partner program approval pending | Wait — partner cycle is the gate; no merchant-side workaround |
| Only one location showing | Multi-location merchant pasted one location_id | Each location needs its own location_id paired with the partner API key |
| Endpoint surface differs from docs | Possible compound endpoint shapes across Genius / Dinerware / Heartland Restaurant branches | Connector layer normalizes; engineering owns the per-branch quirks |
| 7shifts already on the same Heartland account | 7shifts integration coexists — no conflict, we both consume read-only | No fix needed; reassure merchant |

## Sales angle

**Opener:** "You're on Heartland Restaurant — that's ~35k venues, and 7shifts and a handful of others integrate with it directly. We're in the same partner program; once approved, we pull your orders, your menu engineering, your server performance into one view that tells you exactly where margin is leaking."

**Why Heartland Restaurant is the wedge:**
- ~35k US venue footprint — meaningful TAM
- Partner-program POSes have less analytics competition than Square/Toast (higher gate = fewer entrants)
- 7shifts integration precedent means Heartland's partner program is responsive — not a black hole
- Distinct from the compound `heartland` registry entry — Wave 1.5 cleanup splits this out as its own connector

**Competitive notes:** Different from Heartland Retail (self-serve, fast) and Heartland Portico (payments-only, no analytics surface). Qualify which Heartland the merchant is on before promising a timeline. If they're on Dinerware specifically — same Heartland Restaurant partner program covers it.

## What blocks live status today

- Heartland partner program application (kickoff this week)
- Partner approval gates everything — no merchant-side path
- Per-merchant location_id provisioning UX
- Compound endpoint surface — engineering may discover Genius vs Dinerware vs Heartland Restaurant shape differences during build

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (heartland-restaurant config) + docs/playbook/_status/phase-2-decisions.md (Wave 1.5 adds, ~35k venue framing) + docs/playbook/_status/pos-expansion-candidates.md (heartland-restaurant high-priority entry)_
