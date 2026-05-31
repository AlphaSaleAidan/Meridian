# Meadow

> Status: **WAVE 1 BUILDING** — registry config exists; live this wave
> Category: cannabis (California boutique / delivery niche)
> Auth: API key (X-Api-Key header)

## What you tell the merchant

"Meadow support is shipping this wave. You'll generate an API key from your Meadow dashboard, paste it into Meridian, and we'll backfill 18 months of orders. Delivery-specific metrics included."

## How the merchant connects

1. Meadow admin → **Settings → API → Create key**
2. Paste into Meridian's **Settings → POS Connections → Connect Meadow**
3. We pull from `https://api.getmeadow.com/api/v2`

Typical time to connect: **2–3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll | 18 months |
| Products | daily | full history |
| Patients (customers) | daily | PII-protected |

Endpoint reference: `https://api.getmeadow.com/api/v2`

## What features they get

Cannabis + delivery-tuned:

- Money Left on Table
- Product velocity
- Patient LTV (Meadow's patient data is well-structured for retention analysis)
- Delivery zone performance (where Meadow exposes geo data)
- Revenue forecasting
- Day-of-week / time-of-day patterns

## What features they DON'T get

- Employee performance — Meadow doesn't expose employee data at the order level by default
- Order creation — analytics-only

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Missing delivery data | Merchant uses Meadow for retail only, not delivery | Expected; falls back to retail-only analytics |

## Sales angle

**Opener (California boutiques):** "You're on Meadow — usually means California boutique or delivery. Both of those are margin-sensitive plays. We tell you which products and which neighborhoods make money vs. just generate orders."

**Best fit:** California boutique dispensaries, delivery-first operators.

## What blocks live status today

- Final QA on backfill performance for high-volume delivery accounts

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (meadow config) + docs/playbook/_status/phase-2-decisions.md (Cannabis #5)_
