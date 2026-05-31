# BioTrack

> Status: **CSV-ONLY** — state regulatory layer, complementary (not competing) with retail POSes
> Category: cannabis (state-level compliance/track-and-trace)
> Auth: CSV-only (no public API for analytics partners)

## What you tell the merchant

"BioTrack is your state's track-and-trace layer — we don't compete with it. We sit on top: you export your BioTrack-compatible sales CSV (METRC tags, license numbers included), upload it to Meridian, and we layer margin and demand analytics on top."

## How the merchant connects

1. BioTrack (or compliant state system) → **Reports → Sales Export (CSV)**
2. Meridian portal → **Settings → Data Upload → Choose File**

Required CSV columns:

| BioTrack column | Meaning |
|-----------------|---------|
| Transaction ID | transaction_id |
| Date | timestamp |
| Total | total_cents |
| Product Name | line_items |
| METRC Tag | compliance tracking ID |
| License Number | compliance_id |

## What features they get

CSV-path cannabis suite:

- Money Left on Table (daily, not real-time)
- Product velocity (METRC tag-aware — we can track batch performance)
- Revenue trend + forecasting
- Day-of-week / time-of-day patterns
- Compliance-friendly: METRC tags preserved in our data layer

## What features they DON'T get

- Real-time alerts (CSV upload cadence is daily)
- Customer LTV (BioTrack exports don't include customer IDs by default)
- Employee performance (not in standard export)

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Wrong export format | Each state's BioTrack instance varies | Use the "raw sales" export, not the regulatory submission |
| Missing METRC tags | Merchant didn't pull the tag-included variant | Re-export with tags |

## Sales angle

**Opener:** "BioTrack handles your compliance — that's not us. We sit on top. Upload your daily BioTrack sales CSV and we'll tell you which strains are quietly killing your margin and which to push. METRC tags stay in your data; we don't touch your compliance posture."

**Why this works:** BioTrack merchants are often regulator-conscious. Lead with "we don't replace compliance, we add margin intelligence on top." Removes the biggest objection.

## What's NOT happening

- We are NOT pursuing direct BioTrack API integration — they don't offer one for analytics partners. CSV is the path, by design.

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (biotrack config — csv_only) + docs/playbook/_status/phase-2-decisions.md (Cannabis #7 — regulatory layer, complementary not competing)_
