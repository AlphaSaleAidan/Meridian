# Indica Online

> Status: **CSV-ONLY** — California boutique long-tail
> Category: cannabis (California boutique)
> Auth: CSV-only

## What you tell the merchant

"Indica Online doesn't expose an analytics API today, so we work via CSV. You export your daily sales report from Indica, upload to Meridian, and we layer the AI agents on top. Daily refresh, not real-time, but you'll see meaningful insights within 24 hours of your first upload."

## How the merchant connects

1. Indica Online admin → **Reports → Sales Export (CSV)**
2. Meridian portal → **Settings → Data Upload → Choose File**

Required CSV columns:

| Indica column | Meaning |
|---------------|---------|
| Order # | transaction_id |
| Date | timestamp |
| Total | total_cents |
| Product | line_items |
| Track ID | metrc_tag |
| License | compliance_id |

## What features they get

CSV-path cannabis suite:

- Money Left on Table (daily)
- Product velocity
- Revenue trend + forecasting
- Day-of-week / time-of-day patterns
- METRC tags preserved

## What features they DON'T get

- Real-time alerts
- Customer LTV (not in standard export)
- Employee performance

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Export format change | Indica Online has updated their export schema over time | Use the column mapper in Meridian portal — 30 seconds |

## Sales angle

**Opener:** "You're on Indica Online — typically California boutique. CSV path works fine for getting started; you'll see your margin gaps and demand patterns within 24 hours of the first upload. Most boutique dispensaries find CA$1,500+/mo in product mix tweaks alone."

**Best fit:** California boutique dispensaries with limited tech bandwidth.

## What's NOT happening

- We are NOT pursuing direct Indica Online API integration as priority — boutique long-tail. CSV stays the path.

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (indica-online config — csv_only) + docs/playbook/_status/phase-2-decisions.md (Cannabis #8)_
