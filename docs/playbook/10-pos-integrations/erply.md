# Erply

> Status: **WAVE 2 PARTNER-PENDING** — file on prospect signal
> Category: retail (international retail POS)
> Auth: Session key (header-based)

## What you tell the merchant

"Erply support is partner-gated — we file the application when we have qualified Erply prospects. The auth model is session-key based, so the integration is straightforward once approved. Realistic 30–60 days post-filing."

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect Erply**
2. Erply admin generates an API session credential
3. Paste into Meridian; we pull from `https://{account_code}.erply.com/api`

Typical time to connect (projected): **3 minutes**.

## What data we pull (when live)

| Data | Frequency | Backfill |
|------|-----------|----------|
| Sales documents | hourly poll | 18 months |
| Products | daily | full history |
| Employees | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://{account_code}.erply.com/api` (query-string driven: `?request=getSalesDocuments`, etc.)

## What features they get (when live)

Retail suite:

- Money Left on Table
- Product velocity + inventory intelligence
- Customer LTV
- Revenue forecasting
- Basket analysis
- Multi-location rollups (Erply is multi-store friendly)

## Sales angle

**Opener:** "Are you on Erply? Strong multi-store retail POS. We file the partner app on prospect signal — you'd be the trigger. While we're getting approved, CSV path works for getting started."

**Best fit:** international multi-store retailers, specialty retail with 2+ locations.

## What blocks live status today

- Erply partner application — filed on qualified prospect signal only

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (erply config) + docs/playbook/_status/phase-2-decisions.md (Wave 2 holding list)_
