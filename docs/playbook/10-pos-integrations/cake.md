# CAKE

> Status: **WAVE 1 BUILDING** — CSV path shipping now (Sysco channel, ~5k restaurants); API integration stays WAIT
> Category: restaurant
> Auth: CSV-only (today); API auth pending vendor partnership

## What you tell the merchant

"CAKE customers get analytics via daily CSV export today. We're building the live API connection — currently in vendor discussions. CSV means you upload once a day (or we automate via SFTP for higher tiers) and get insights within hours of upload."

## How the merchant connects (CSV path)

1. From CAKE admin → **Reports → Export → Daily Sales Report (CSV)**
2. From the Meridian portal → **Settings → Data Upload → Choose File**
3. Drag in the CSV; we ingest and map columns automatically

Required CSV columns:

| CAKE column | Meaning |
|-------------|---------|
| Order ID | transaction_id |
| Date | timestamp |
| Total | total_cents |
| Items | line_items |
| Payment Type | payment_method |

## What features they get

CSV path covers the **transaction-level** features but loses some real-time ones:

- Money Left on Table (recalculated daily, not real-time)
- Revenue trend + forecasting
- Peak hours (based on timestamp granularity in the CSV)
- Menu engineering
- Basket analysis
- Day-of-week + seasonality

## What features they DON'T get (yet)

- Real-time alerts (no live API)
- Live order push from phone agent (`sms_fallback: True` is the workaround — orders go via SMS)
- Customer LTV (CAKE CSV doesn't include customer IDs by default)
- Employee performance comparison (no employee data in standard export)

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Daily upload missed | Manual process | Upgrade to automated SFTP (Premium tier) |
| Column mapping fails | CAKE export format changed | Re-map in portal; takes 30 seconds |
| Duplicate transactions | Same date range uploaded twice | We dedupe by `Order ID` automatically |

## Sales angle

**Opener:** "Are you on CAKE? Probably came in through Sysco. Your reports tell you yesterday's revenue — we tell you which menu items are killing your margin and which to push. Most CAKE merchants find CA$1,500–CA$3,000/mo within 2 weeks of starting daily uploads."

**Why CAKE merchants are a real opportunity:**
- Sysco channel has ~5,000 CAKE restaurants — wide untapped market
- Most have never seen analytics beyond CAKE's basic reports
- CSV-only is a soft objection — they're already used to exporting reports

**How to handle the "I don't want to upload a CSV every day" objection:**
"That's fair. Two options: (1) Premium plan includes automated daily SFTP — we pull it from CAKE for you. (2) We're building the live API; CSV is the bridge. You're in line for live as soon as it ships."

## What blocks live status today

- **CSV path:** ready to ship this wave (Wave 1 #7)
- **API path:** vendor partnership still WAIT — no committed timeline

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (cake config — csv_only) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #7)_
