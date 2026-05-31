# talech

> Status: **WAVE 1 BUILDING** — token-auth REST rewrite (registry currently says `csv_only`; live API path coming this wave)
> Category: multi-vertical (originally Elavon's POS; common in small restaurant + retail)
> Auth: Token-based REST (rewrite shipping; no Elavon partner gate required)

## What you tell the merchant

"talech support is shipping this month — we'll connect via API with a token you generate from your talech admin. Until then, CSV upload works for getting started. Either way, first insights inside 24 hours."

## How the merchant connects (CSV path — works today)

1. talech admin → **Reports → Sales Report → Export CSV**
2. Meridian portal → **Settings → Data Upload → Choose File**

Required columns:

| talech column | Meaning |
|---------------|---------|
| Receipt # | transaction_id |
| Date | timestamp |
| Total | total_cents |
| Item | line_items |
| Payment Method | payment_method |

## How the merchant connects (API — when live)

1. talech admin → **Settings → API Access** (path TBD pending rewrite)
2. Generate token; paste into Meridian
3. We pull transactions on hourly poll

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | CSV today / hourly poll (API live) | 18 months |
| Catalog | daily (API live) | full history |
| Employees | daily (API live) | varies |

## What features they get

CSV path (today): transaction-level — Money Left on Table, peak hours, revenue forecasting, basket analysis, day-of-week patterns.

API path (when live): adds product velocity, employee performance, customer LTV (where customer data exists), real-time alerts.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| CSV column names don't match | talech export format varies by account age | Use the column mapping screen in Meridian |
| API auth rejected | Old Elavon partner gate still referenced | Engineering rewriting to direct token-auth — no Elavon gate |
| Missing items in CSV | Voided/refunded transactions filtered out | Expected; we recompute from remaining data |

## Sales angle

**Opener:** "Are you on talech? You probably came in through Elavon. Most talech merchants run on CSV exports — we ingest that today and live API is shipping this month. Either way, you'll see what your reports aren't telling you within 24 hours."

**Why talech merchants close:**
- Many feel "stuck" on talech with no analytics layer — open to anything that adds value
- CSV path means you don't need to wait for engineering
- Multi-vertical means broad appeal (restaurant + retail mix)

## What blocks live status today

- Token-auth REST rewrite (current registry entry is `csv_only`; engineering implementing the live API path this wave)
- No vendor blocker — talech doesn't require Elavon partner gate per Phase 2 finding

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (talech config — csv_only currently) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #9 — Elavon gate not required)_
