# CSV-Only Systems — One-Place Reference

When a merchant uses a POS in this list, the answer is **CSV upload only** (the vendor has no usable API for analytics partners). It still works — daily uploads give you daily insights — but it's not real-time and some features (customer LTV, employee performance) may be limited depending on what's in the export.

## How CSV upload works (universal flow)

1. Merchant exports a sales report from their POS as CSV
2. Meridian portal → **Settings → Data Upload → Choose File**
3. We auto-detect or map columns, ingest, dedupe by transaction ID
4. Insights refresh within hours of upload (vs hourly poll for live API)

Premium tier supports automated SFTP pulls so the merchant doesn't have to upload manually each day.

## What CSV path covers vs misses

| Feature | CSV path | Live API |
|---------|---------|----------|
| Money Left on Table | Yes (daily refresh) | Yes (real-time) |
| Revenue trend + forecasting | Yes | Yes |
| Peak hours | Yes (if timestamps are granular) | Yes |
| Basket analysis | Yes (if line items present) | Yes |
| Product velocity | Yes (if SKUs present) | Yes |
| Customer LTV | **Only if customer IDs in export** | Yes |
| Employee performance | **Only if employee field in export** | Yes |
| Real-time alerts | No (daily batch) | Yes |
| Phone agent order push | SMS fallback only | Native order create |

## CSV-only systems by category

### Restaurant on-prem (vendor has no API at all)

| POS | Notes | Phase 2 status |
|-----|-------|----------------|
| Aldelo | On-prem, no cloud sync | Stripped "Roller Holdings" ownership claim — unverified |
| Digital Dining | Legacy on-prem | Active CSV path |
| Focus POS | On-prem, used in QSR | Active CSV path |
| Future POS | On-prem | Active CSV path |
| NorthStar | Vendor unverified | Active CSV path; flag if merchant asks for vendor history |
| PixelPoint | Heartland-owned legacy | Active CSV path |
| Rezku | Partner pipeline pending — currently CSV | See [rezku.md](./rezku.md) |
| CAKE | CSV path is current Wave 1 ship; API still WAIT | See [cake.md](./cake.md) |
| talech | Token-auth REST rewrite in flight; currently CSV in registry | See [talech.md](./talech.md) |

### Retail / Pharmacy (no API)

| POS | Notes |
|-----|-------|
| Cashier Live | Active CSV path |
| Rain POS | Stripped "Roller Holdings" ownership claim — unverified |
| Retail Edge | Active CSV path |
| accu-pos | Active CSV path |

### Automotive (entire vertical has no API)

If a merchant uses any of these, the answer is "CSV only" — there is no automotive POS in our registry with a working API today.

| POS | Notes |
|-----|-------|
| Mitchell1 | Shop management |
| ALLDATA Manage | Shop management |
| NAPA TRACS | Auto parts + service |
| TireMaster | Tire shops |
| R.O. Writer | Repair order |
| Protractor | Stripped "acquired into Solera" claim — unverified |
| Bolt On | Service writer |
| AutoVitals | Service writer / inspection |
| AutoFluent | Repair management |
| Omnique | Repair management |

**Sales note for automotive:** the vertical is consistent enough that you can group all automotive prospects under one CSV onboarding flow. Auto repair shops + tire shops have similar margin questions (parts vs labor, technician productivity, slow-mover inventory).

### Cannabis CSV-only

| POS | Notes |
|-----|-------|
| BioTrack | State regulatory layer — see [biotrack.md](./biotrack.md) |
| Indica Online | California boutique — see [indica-online.md](./indica-online.md) |
| Leaf Logix | **Deprecated** — acquired by Dutchie 2021. Keep CSV for legacy tenants only; recommend Dutchie migration. |
| POS Nation | **Registry mis-tag** — currently labeled cannabis, actually multi-vertical retail. Fix in flight. |

### Multi-vertical CSV-only

| POS | Notes |
|-----|-------|
| Harbortouch | **Sunset** — Shift4 rebranded to SkyTab. Route to [skytab.md](./skytab.md). |

## Required columns (universal CSV schema)

Meridian's CSV importer needs at minimum:

| Column | Type | Required | Why |
|--------|------|----------|-----|
| transaction_id | string | Yes | Dedup key |
| timestamp | ISO datetime | Yes | All time-based agents need this |
| total_cents | integer | Yes | Revenue calculations |
| line_items | string/array | Yes | Basket analysis, menu engineering |
| payment_method | string | No | Payment optimizer agent |
| customer_id | string | No | Unlocks customer LTV/churn |
| employee_id | string | No | Unlocks employee performance |

Per-POS column mappings (the actual export column names) live in `src/services/pos_connectors/registry.py` under each `csv_columns` block.

## Sales script for CSV-only POS

**Opener:** "You're on [POS]. They don't expose an analytics API, so we work via CSV — you export daily, upload to Meridian, and we run all the insights on top. Same agents, daily refresh instead of real-time. Most merchants on [POS] find CA$1,500+/mo in margin gaps within the first 2 weeks."

**If they push back on CSV:** "Two options to make it easier: Premium plan includes automated SFTP pulls — we grab the export from your system, you don't upload anything. Or we set you up to email the CSV to a Meridian inbox; takes 30 seconds a day."

## What NOT to promise CSV merchants

- Real-time alerts (we're daily)
- Phone agent that pushes orders into their POS (we can SMS-fallback where `sms_fallback: True` in registry — Cake, Talech, Rezku, Harbortouch — but it's text-based, not POS-native)
- Customer LTV unless the export contains customer IDs (most automotive and CAKE exports don't)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (28 csv_only entries) + docs/playbook/_status/phase-2-decisions.md (Can't-Connect list, Deprecate list)_
