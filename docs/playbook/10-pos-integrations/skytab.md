# SkyTab (Shift4)

> Status: **WAVE 1 BUILDING** + Shift4 partner application filed this week
> Category: restaurant (Shift4's restaurant POS — major Revel migration tailwind)
> Auth: OAuth (bearer)

## What you tell the merchant

"SkyTab support is in active build — Shift4 partner application filed this week. Expected live within 30–45 days. If you migrated from Revel recently, you're a priority — there are ~18,000 of you moving to SkyTab right now and we're building specifically for that wave."

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect SkyTab**
2. Shift4 OAuth flow
3. We pull from `https://api.shift4.com/v1/merchants/{merchant_id}/...`

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Items | daily | full history |
| Employees | daily | full history |

Endpoint reference: `https://api.shift4.com/v1`

## What features they get (when live)

Restaurant suite:

- Money Left on Table
- Menu engineering
- Revenue forecasting
- Peak hours
- Employee performance
- Discount/promo ROI

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Customer LTV — SkyTab customer data is not exposed in their current API surface

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Merchant ID wrong | SkyTab merchant ID differs from Shift4 payment merchant ID | Use the SkyTab admin → Settings to get the right one |
| Old Harbortouch credentials | Merchant migrated from Harbortouch but kept old creds | They need new SkyTab creds from Shift4 |

## Sales angle

**Opener for Revel-migrating merchants:** "I know you just moved to SkyTab from Revel. That migration is brutal and you've probably lost your analytics in the process. We rebuild it on SkyTab data — same insights, better than what Revel ever gave you."

**Opener for net-new SkyTab:** "Are you on SkyTab? Shift4's restaurant POS — we're partner-pending right now and you can be in the first cohort of live merchants. CA$2,800/mo in money-left-on-table is the average we find in week 1."

**Why this matters:** the Revel → SkyTab migration is a forced event for ~18,000 restaurants. Most are looking for replacements for their old analytics stack. Time-bounded opportunity.

## What blocks live status today

- Shift4 partner application filed this week — waiting on approval
- Engineering completing OAuth flow in parallel

## Routing note

**If a merchant says "we're on Harbortouch":** that brand is sunset. Shift4 is migrating everyone to SkyTab. Pitch them as SkyTab merchants and tee up the migration conversation.

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (skytab config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #11, Harbortouch deprecation, Wave 2 partner table)_
