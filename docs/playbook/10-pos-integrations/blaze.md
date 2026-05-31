# Blaze

> Status: **WAVE 1 BUILDING** — registry config exists; live this wave
> Category: cannabis (California mid-tier)
> Auth: Header-based (Authorization header)

## What you tell the merchant

"Blaze support ships this wave. You'll generate API credentials from your Blaze partner panel, paste into Meridian, and we'll backfill. Most Blaze merchants see meaningful insights inside the first 48 hours."

## How the merchant connects

1. Blaze admin → **Settings → Partner API → Generate credentials**
2. Paste into Meridian's **Settings → POS Connections → Connect Blaze**
3. We pull from `https://api.blaze.me/api/v1/partner/...`

Typical time to connect: **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Products | daily | full history |
| Members | daily | PII-protected |

Endpoint reference: `https://api.blaze.me/api/v1/partner`

## What features they get

Cannabis suite:

- Money Left on Table
- Product velocity + inventory intelligence
- Member (customer) LTV
- Revenue forecasting
- Promo ROI
- Day-of-week / time-of-day patterns

## What features they DON'T get

- Order creation — analytics-only
- Budtender-level performance (Blaze doesn't expose this at the partner API level)

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Auth header format wrong | Blaze uses non-standard `Authorization` value format | Partner docs spec it; engineering handles |

## Sales angle

**Opener:** "You're on Blaze — solid California mid-tier coverage. We pull your transactions and tell you the 3–5 SKUs that are quietly killing your margin every month. Most Blaze merchants find CA$2K+/mo in product mix fixes."

**Best fit:** California mid-tier dispensaries (single + small multi-location).

## What blocks live status today

- Final QA on backfill performance

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (blaze-pos config) + docs/playbook/_status/phase-2-decisions.md (Cannabis #6)_
