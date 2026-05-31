# SpotOn

> Status: **WAVE 2 PARTNER-PENDING (slow)** — public reports show 26+ days just to receive the partner form. **File on first qualified prospect, not speculatively.**
> Category: restaurant
> Auth: Bearer (when live)

## What you tell the merchant

**Be honest about the timeline:** "SpotOn integration is partner-gated — their partner program has a slow intake (we've seen 30+ days just to get the application form). We file the moment we have a qualified prospect, which you'd be. Realistic timeline is 60–90 days. CSV path works in the meantime if you want to start seeing insights now."

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect SpotOn**
2. OAuth flow to SpotOn
3. We pull from `https://api.spoton.com/v1`

Typical time to connect (projected): **3 minutes**.

## What data we pull (when live)

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Menu items | daily | full history |
| Employees | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.spoton.com/v1`

## What features they get (when live)

Restaurant suite:

- Money Left on Table
- Menu engineering
- Revenue forecasting
- Customer LTV
- Employee performance
- Order creation supported (`supports_orders: True`)

## Sales angle

**Opener:** "Are you on SpotOn? Honest answer: their partner program is slow. We file the partner app when we have a real prospect — which you are. While that's processing (30–90 days), we can run analytics on a CSV export so you're not waiting. Then we cut over to live API once approved."

**When to push hard:** SpotOn merchants who are CA$685+ Premium-tier candidates with cameras justify the partner-app effort. Single-location small accounts on SpotOn → consider a CSV-only path or pass.

**Why we don't file SpotOn speculatively:** the partner application is slow and merchant-tied; filing without a real account in hand wastes the cycle.

## What blocks live status today

- SpotOn partner program intake — bottleneck is on their side (26+ day documented wait for the form itself)
- Engineering ready to ship once approved

## CSV bridge

If a SpotOn merchant wants to start now:
1. SpotOn admin → **Reports → Sales Export (CSV)**
2. Meridian portal → **Settings → Data Upload**
3. Daily uploads = daily insights; cut over to live when partner approval lands

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (spoton config) + docs/playbook/_status/phase-2-decisions.md (Wave 2 holding list — file on first qualified prospect)_
