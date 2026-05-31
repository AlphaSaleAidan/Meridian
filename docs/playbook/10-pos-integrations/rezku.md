# Rezku

> Status: **WAVE 2** — registry is currently `csv_only`; partner app filed on prospect signal
> Category: restaurant
> Auth: CSV today; live API pending partner discussion

## What you tell the merchant

"Rezku works via CSV today — you export daily, upload, get insights within 24 hours. We file the partner application for live API access when we have qualified Rezku prospects in the pipeline. If you're interested in being one of the first, let me know."

## How the merchant connects (CSV)

1. Rezku admin → **Reports → Sales Report → Export CSV**
2. Meridian portal → **Settings → Data Upload → Choose File**

Required CSV columns:

| Rezku column | Meaning |
|--------------|---------|
| Order # | transaction_id |
| Date | timestamp |
| Total | total_cents |
| Item Name | line_items |
| Payment Type | payment_method |

`sms_fallback: True` — phone agent orders can route via SMS for Rezku merchants.

## What features they get

CSV path: transaction-level features — Money Left on Table, revenue trend, peak hours, basket analysis, menu engineering, day-of-week patterns.

## What features they DON'T get (yet)

- Real-time alerts
- Customer LTV (no customer IDs in standard export)
- Employee performance

## Sales angle

**Opener:** "Are you on Rezku? CSV path works today — you'll see margin gaps within 24 hours of first upload. Live API is partner-gated and we file on prospect signal. Either way, you're not blocked."

## What blocks live status today

- Live API path requires Rezku partner program — filed on qualified prospect signal only (per Phase 2 decision: not speculatively)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (rezku config — csv_only) + docs/playbook/_status/phase-2-decisions.md (Wave 2 holding list)_
