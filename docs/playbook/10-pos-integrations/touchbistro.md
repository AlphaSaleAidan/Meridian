# TouchBistro

> Status: **WAVE 2 PARTNER-PENDING** — partner application filed (`integratedpartners@touchbistro.com`)
> Category: restaurant (iPad-first; strong in Canada)
> Auth: Header-based (Authorization header)

## What you tell the merchant

"TouchBistro support is in the partner pipeline — we've reached out to their integrated partners team. We're framing as analytics-only / read-only, which keeps the partner conversation light. Expected live within 30–60 days post-approval. I can put you in the priority cohort."

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect TouchBistro**
2. They authorize via TouchBistro partner credential flow
3. We pull from `https://cloud.touchbistro.com/api/v1/restaurants/{restaurant_id}/...`

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll | 18 months |
| Menu items | daily | full history |
| Staff | daily | full history |

Endpoint reference: `https://cloud.touchbistro.com/api/v1`

## What features they get (when live)

Restaurant suite:

- Money Left on Table
- Menu engineering matrix
- Peak hours
- Revenue forecasting
- Server-level performance
- Customer LTV (where TouchBistro customer data is captured)

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only (which is by design for the partner framing)

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Restaurant ID wrong | TouchBistro multi-location IDs differ from billing IDs | Confirm with TouchBistro admin |

## Sales angle

**Opener (Canada):** "You're on TouchBistro — really strong choice for Canadian independents. We're partner-pending with them right now. Once live, you get menu engineering and server-level performance most TouchBistro reports don't expose. CA$2,800+/mo in margin gaps is typical for full-service restaurants."

**Why TouchBistro is a Canada wedge:** strong Canadian independent restaurant share. Pair with Cova (cannabis) and Toast (US-focused) for a full Canadian story.

## What blocks live status today

- TouchBistro integrated partners application — filed at `integratedpartners@touchbistro.com`
- Engineering ready to ship once approved

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (touchbistro config) + docs/playbook/_status/phase-2-decisions.md (Wave 2 partner table)_
