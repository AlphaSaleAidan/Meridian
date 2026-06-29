# Dutchie

> Status: **WAVE 2 PARTNER-PENDING** — Dutchie Certified Partner Program (launched Aug 2025)
> Category: cannabis (US dispensary #1)
> Auth: Bearer token (per-retailer)

## What you tell the merchant

"Dutchie is our #1 US cannabis priority. We're in the Dutchie Certified Partner Program — application live. Once approved (usually 30–60 days from approval), connection is fast: retailer-specific API token, immediate backfill. I can put you in the first cohort."

## How the merchant connects (when live)

1. Dutchie admin → **Settings → Integrations → Generate API token** (per-retailer)
2. Paste token + retailer ID into Meridian's **Settings → POS Connections → Connect Dutchie**
3. We pull from `https://plus.dutchie.com/api/v1/retailers/{retailer_id}/...`

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll | 18 months |
| Products | daily | full history |
| Employees | daily | full history |
| Customers | daily | PII-protected per state rules |

Endpoint reference: `https://plus.dutchie.com/api/v1/retailers/{retailer_id}/`

## What features they get (when live)

Cannabis suite, full coverage:

- Money Left on Table
- Product Velocity (cannabis SKU turn is the #1 lever)
- Inventory Intelligence (batch-aware)
- Customer LTV / patient retention
- Revenue trend + forecasting
- Promo ROI
- Day-of-week / time-of-day (cannabis is heavily 4:20 + weekend skewed)
- Order creation supported (`supports_orders: True`) — phone agent can push orders

## What features they DON'T get

- Compliance reporting itself — Dutchie + state regulators own that. We surface margin and demand patterns on top.

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Token rejected | Token scoped to wrong retailer ID | Regenerate with correct retailer scope |
| Missing products | Dutchie inventory module disabled at the merchant | Falls back to order-line items |

## Sales angle

**Opener:** "You're on Dutchie — biggest US cannabis POS, biggest opportunity for our analytics. We're in their Certified Partner Program; you can be in the first cohort live. The cannabis margin question is always 'which SKU, what price, what time' — that's exactly what our agents answer."

**Why Dutchie matters:**
- US dispensary market leader
- Multi-state operators (MSOs) → multi-location add-on candidates (commission at custom price)
- Cannabis owners are sophisticated buyers — they value real analytics

**Cannabis-specific compliance you must mention:**
- US federal Schedule I → separate banking/insurance posture
- PII per state regulations (some states have HIPAA-adjacent rules)
- No Google/Facebook/LinkedIn ads — outreach is direct/event/WOM only

## What blocks live status today

- Dutchie Certified Partner Program approval — application filed; vendor timeline varies
- US cannabis compliance review on our side (separate from Cova which is Canada-only)

---

_Last updated: 2026-06-29_
_Sourced from: src/services/pos_connectors/registry.py (dutchie-pos config) + docs/playbook/_status/phase-2-decisions.md (Cannabis #2, Wave 2 partner table)_
