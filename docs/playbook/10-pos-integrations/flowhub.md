# Flowhub

> Status: **WAVE 2 PARTNER-PENDING** — partner intake
> Category: cannabis (US dispensary #3 — strong in CO/MI/MA/OK)
> Auth: Bearer token

## What you tell the merchant

"Flowhub is our #3 US cannabis priority — partner intake in flight. Strong Colorado, Michigan, Massachusetts, and Oklahoma presence. Expected live within 30–60 days post-approval."

## How the merchant connects (when live)

1. Flowhub admin → **Settings → API → Generate API key**
2. Paste into Meridian's **Settings → POS Connections → Connect Flowhub**
3. We pull from `https://api.flowhub.co/v1`

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Inventory | daily | full history |
| Employees | daily | full history |
| Members (customers) | daily | PII-protected |

Endpoint reference: `https://api.flowhub.co/v1`

## What features they get (when live)

Cannabis suite:

- Money Left on Table
- Product velocity + inventory intelligence
- Customer (member) LTV
- Revenue forecasting
- Day-of-week / time-of-day patterns
- Employee performance

## What features they DON'T get

- Order creation — analytics-only
- Some compliance modules are state-specific in Flowhub; we surface revenue patterns, not regulatory compliance itself

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Multi-location data crosses streams | Flowhub multi-location setup varies | Connect each location separately or use the multi-location endpoint (TBD per partner agreement) |

## Sales angle

**Opener (CO/MI/MA/OK):** "You're on Flowhub — perfect timing. We're in the Flowhub partner pipeline and you can be in the first cohort. [State]'s cannabis market is brutal on margin; our agents tell you which products and time windows actually make money."

**Why Flowhub:**
- Strong regional presence (especially CO and MI)
- Mid-market dispensaries — natural Premium tier candidates (CA$685 / $599)

## What blocks live status today

- Flowhub partner intake — application filed
- Cannabis compliance posture (shared with all cannabis integrations)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (flowhub config) + docs/playbook/_status/phase-2-decisions.md (Cannabis #4)_
