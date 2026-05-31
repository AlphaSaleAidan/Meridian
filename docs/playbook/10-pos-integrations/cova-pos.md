# Cova

> Status: **WAVE 1 BUILDING** + partner intake this week — **Canada cannabis #1 wedge**
> Category: cannabis (dispensary)
> Auth: Header-based auth (Authorization header)

## What you tell the merchant

"Cova is our #1 Canadian cannabis integration — partner intake filed this week, building now. You'll connect with API credentials from your Cova admin. Expected live within 30–45 days. We've designed the cannabis workflow with PII handling and provincial compliance baked in."

## How the merchant connects (when live)

1. Cova admin → **Settings → API → Create credential**
2. Paste credential into Meridian's **Settings → POS Connections → Connect Cova**
3. We test against `/companies` endpoint and start backfill

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Sales invoices | hourly poll | 18 months |
| Catalog products | daily | full history |
| Employees | daily | full history |
| Customers (patients) | daily | full history (PII-protected) |

Endpoint reference: `https://api.covasoftware.com/v1`

## What features they get (when live)

Cannabis-tuned suite:

- Money Left on Table
- Product Velocity (especially valuable — fast inventory turn in cannabis)
- Inventory Intelligence (reorder timing, batch tracking)
- Customer LTV (patient retention is the cannabis margin lever)
- Revenue trend + forecasting
- Promo/discount ROI
- Day-of-week / time-of-day patterns (cannabis traffic is heavily time-skewed)

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Cross-border or US compliance — Cova is Canada-focused

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Auth rejected | Wrong scope on Cova credential | Cova partner intake clarifies scopes during approval |
| Missing batch IDs | Cova batch tracking module not on | Falls back to SKU-level (still useful) |

## Sales angle

**Opener (Canada):** "You're on Cova in Canada — you're our #1 priority cannabis integration. Provincial regulators want clean data; your patients want consistent product availability. We give you both, plus the margin insights nobody else surfaces."

**Why Cova is the wedge:**
- Dominant in Canadian dispensaries
- Cannabis margins are tight → analytics ROI is obvious
- Provincial compliance overhead is real — we've built around it

**Cannabis-specific compliance you must mention:**
- Separate banking + insurance posture (federal Schedule I in US contexts)
- PII handling per provincial rules
- Marketing channels: direct, event, WOM only (Google/Facebook/LinkedIn restrict cannabis ads)

## What blocks live status today

- Cova partner intake filed this week — waiting on approval
- Cannabis vertical compliance review (separate banking/insurance, PII storage) — coordinating with ops

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (cova-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #12, Cannabis vertical greenlit, Wave 2 partner table)_
