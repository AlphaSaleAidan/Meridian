# Lightspeed Restaurant (K-Series)

> Status: **WAVE 1 BUILDING** + partner application filed this week
> Category: restaurant (full-service, hospitality, multi-location)
> Auth: OAuth (bearer)

## What you tell the merchant

"Lightspeed Restaurant support is in active build — partner application filed this week with Lightspeed's K-Series team. Expected live within 30–45 days. I can put you on the priority list and we can preview your data via CSV in the meantime."

**Do not promise a specific date** — vendor approval is variable.

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect Lightspeed Restaurant**
2. OAuth redirect to Lightspeed → business owner approves
3. We pull from `https://api.lightspeedrestaurant.com/v1`

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Items | daily | full history |
| Employees | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.lightspeedrestaurant.com/v1`

## What features they get (when live)

Restaurant suite + hospitality extras:

- Money Left on Table
- Menu engineering matrix
- Revenue forecasting (with reservation overlay where Lightspeed reservations are on)
- Peak hours
- Customer LTV
- Employee performance
- Multi-location rollups (Command tier)
- Order creation supported (`supports_orders: True`)

## What features they DON'T get

- Lightspeed-specific table management telemetry (table turn time) requires module add-on the merchant may not have

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Wrong region | Lightspeed has US/EU/AU instances | Confirm region during onboarding |
| Token rejected post-renewal | OAuth refresh edge case | One-click reconnect |

## Sales angle

**Opener:** "Are you on Lightspeed Restaurant? Hospitality-grade data we can do a lot with — table turn analysis, server-level revenue, menu engineering. Once we're live (this month), most operators find CA$3K+/mo in repeatable wins."

**Best fit:** full-service restaurants, hotels with F&B, multi-location restaurant groups (Command tier — CA$1,370/mo, $959 commission).

## What blocks live status today

- Lightspeed K-Series partner application filed this week — waiting on approval
- Registry config exists; engineering completing the OAuth flow alongside partner approval

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (lightspeed-restaurant config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #10, Wave 2 partner table)_
