# Epos Now

> Status: **WAVE 2 PARTNER-PENDING** — file on prospect signal
> Category: multi-vertical (UK-origin POS, growing in North America)
> Auth: Bearer

## What you tell the merchant

"Epos Now support is partner-gated — we file the partner application when we have qualified Epos Now prospects (you'd be one). Realistic timeline is 30–60 days post-filing. CSV bridge is available if you want to start seeing insights now."

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect Epos Now**
2. OAuth flow to Epos Now
3. We pull from `https://api.eposnowhq.com/api/v4`

Typical time to connect (projected): **3 minutes**.

## What data we pull (when live)

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Products | daily | full history |
| Staff | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.eposnowhq.com/api/v4`

## What features they get (when live)

Multi-vertical suite:

- Money Left on Table
- Product velocity + inventory intelligence
- Customer LTV
- Revenue forecasting
- Employee performance

## Sales angle

**Opener:** "Are you on Epos Now? We file the partner application on prospect signal — you'd be the trigger. Realistic 30–60 days post-filing. CSV works in the meantime so you're not waiting on us."

**Best fit:** small UK-origin merchants now operating in North America, multi-vertical retail or hospitality.

## What blocks live status today

- Epos Now partner application — filed on qualified prospect signal only

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (epos-now config) + docs/playbook/_status/phase-2-decisions.md (Wave 2 holding list)_
