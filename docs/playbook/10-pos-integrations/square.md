# Square

> Status: **LIVE**
> Category: multi-vertical (restaurant / retail / cafe / smoke shop / salon)
> Auth: OAuth (bearer)

## What you tell the merchant

"Square connection takes about 90 seconds. You'll click one button, log into your Square account, approve Meridian access, and we'll start importing 18 months of transaction history immediately. First insights land within 24 hours."

## How the merchant connects

1. From the Meridian portal, **Settings → POS Connections → Connect Square**
2. They click through to Square's OAuth screen and log in
3. They approve the requested scopes (orders, catalog, team members, customers)
4. Square redirects them back; we begin the historical backfill
5. They see a progress bar on Settings → POS Connections

Typical time to connect: **2 minutes**. Backfill: **2–6 hours** for 18 months depending on transaction volume.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders / transactions | real-time (webhooks) + 5-min poll | 18 months |
| Catalog items | hourly | full history |
| Team members | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://connect.squareup.com/v2`

## What features they get

Almost everything. Square's data is the richest of any POS we connect to:

- Money Left on Table (full path — strong upstream data)
- Revenue trend + forecasting
- Peak hours (15-min granularity)
- Customer LTV + churn (Square has customer IDs)
- Basket analysis
- Product velocity + inventory intelligence
- Employee performance
- Pricing power
- Discount/promo ROI
- Day-of-week + seasonality
- Cash flow

See `30-features/_data-requirements-matrix.md` for the full feature × data map.

## What features they DON'T get

- **Camera intelligence + cross-reference agents** require Premium plan + a supported camera. Not Square-specific.
- **Multi-location rollups** require Command plan.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| OAuth screen shows "App not found" | Wrong environment (sandbox vs prod) | Use the production connect link from portal only |
| Backfill stuck at < 100% after 24h | Large catalog, rate limits | See `40-troubleshooting/backfill-stuck.md` |
| Token expired (after months) | Square refresh token rotation | One-click reconnect from portal — preserves history |

## Sales angle

**Opener:** "I work with Square merchants who are leaving CA$2,800/mo on the table they don't see. Got 60 seconds?"

**Why Square is your best target:** highest data quality, fastest backfill, fewest objections about "will this break my POS." It won't — we're read-only by default.

**Vertical-specific Square openers:**
- Cafes: "Square gives you a register. We tell you which 15-minute window is your real peak so you schedule the second barista at the right time."
- Smoke shops: "Square's reports show you sales. We show you shrinkage and which SKUs are dead inventory."
- Salons: "Your Square customer list is gold — we flag regulars who haven't rebooked before they switch."

## What blocks live status today

Nothing — it's live. Open work is UX hardening (the connect flow has 2 extra clicks we want to remove).

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (square config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #1) + src/integrations/registry.py_
