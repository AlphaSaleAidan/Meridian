# Boulevard

> Status: **WAVE 1.5 BUILDING — salon vertical wedge**
> Category: salon (modern salon/spa POS — appointment-led)
> Auth: OAuth 2.0 client credentials

## What you tell the merchant

"Boulevard is our first salon connector. Salons are a vertical we've been trained on but never connected to before — Boulevard is the modern, tech-forward salon POS, so it's where we're starting. You'll create a developer app in Boulevard's portal, paste the client ID and secret into Meridian, and we start backfilling. First insights inside 24 hours of connect."

## How the merchant connects (when live)

1. **developers.joinblvd.com** → sign in with Boulevard owner credentials → **Create app**
2. Copy the **client_id** and **client_secret** Boulevard issues
3. Paste both into Meridian's **Settings → POS Connections → Connect Boulevard**
4. We hit `/locations` to verify and start the backfill

Typical time to connect (projected): **4 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Appointments (sales) | hourly poll | 18 months |
| Services (catalog) | daily | full history |
| Clients (customers) | daily | full history (PII-protected) |
| Staff (employees) | daily | full history |

Endpoint reference: `https://dashboard.boulevard.io/api/2020-01` (GraphQL Admin API — connector layer handles REST→GraphQL shaping)

## What features they get (when live)

Salon-tuned suite:

- Money Left on Table (rebook gaps, no-shows, service add-on misses)
- Customer LTV + churn (salon retention is the margin lever)
- Service mix / pricing power per stylist
- Peak hours + chair utilization
- Employee performance (per-stylist revenue, average ticket, rebook rate)
- Discount/promo ROI

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only, no phone-agent push-back to Boulevard
- Inventory intelligence is limited — Boulevard's product retail module is optional and varies by salon

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| GraphQL response shape doesn't match | REST-style fields above are the documented adapter — actual surface is GraphQL | Connector layer translates; engineering owns the query shape |
| Auth rejected | Client credentials not approved for production scope | Re-request scopes in dev portal |
| Rate-limit on backfill | Boulevard caps bulk historical pulls | Backfill paces automatically; longer than Square but still <6h for most salons |
| Missing client PII | Salon client privacy rules vary by region | We honor Boulevard's PII flags; some fields may be redacted |

## Sales angle

**Opener:** "You're on Boulevard, which means you picked a salon POS that actually has data worth pulling. Most salon POSes don't. We're the first analytics layer for Boulevard — your rebook gaps, your add-on misses, your stylist-by-stylist margin — none of that is visible in the Boulevard dashboard the way we surface it."

**Why Boulevard is the salon wedge:**
- Modern API surface (GraphQL) — most salon POSes don't have one at all
- Boulevard merchants self-select for tech-forward operators — easier rep conversations
- Salon vertical is in our training (lesson 4.3 "Salons & Spas") but had zero integrations until this wave — first-mover advantage

**Competitive notes:** Mindbody is the wellness anchor we're building alongside this. If a salon is on Mindbody instead, route to that playbook. Boulevard is the wedge for salons that explicitly chose a modern POS over Mindbody.

## What blocks live status today

- GraphQL connector layer build (REST adapter shape is documented; full GraphQL query surface in progress)
- Salon PII handling review (region-specific client data rules)
- First Boulevard merchant for beta validation

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (boulevard config) + docs/playbook/_status/phase-2-decisions.md (Wave 1.5 adds) + docs/playbook/_status/pos-expansion-candidates.md (salon vertical gap)_
