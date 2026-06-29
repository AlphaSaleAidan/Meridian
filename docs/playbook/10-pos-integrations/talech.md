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

1. Log in at `app.talech.com` → click name (top right) → **Account Settings**
2. Click **Generate New Token** → enter developer name = "Meridian" + the Meridian-monitored inbox as developer email
3. Click **Generate API Token** — talech emails the token to that inbox
4. Meridian ingests the token automatically from the email; merchant does nothing further

Token is revocable from the same screen. **No partner program required** — the merchant owns their data and authorizes Meridian directly. Self-serve, takes minutes.

[**talech's own plan tiers**] API access is tier-gated within talech. Merchants on talech Mobile (free) or talech Starter ($29/mo) won't see the "Generate New Token" option — they need talech Standard ($69/mo) or talech Premium ($99/mo). (These are talech's own plans, not Meridian plans.)

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
| Merchant on talech Mobile/Starter can't find "Generate New Token" | API access is talech-tier-gated | Merchant needs to upgrade their talech plan to talech Standard ($69) or talech Premium ($99) |
| 403 on `api-eu.talech.com` for a US merchant | Wrong region host | Route US to `api.talech.com`, EU/UK/IE to `api-eu.talech.com` |
| Token works then suddenly 401 | Merchant clicked **Revoke** in Account Settings | Re-issue from the same screen |
| CSV column names don't match | talech export format varies by account age | Use the column mapping screen in Meridian |
| Missing items in CSV | Voided/refunded transactions filtered out | Expected; we recompute from remaining data |

## Sales angle

**Opener:** "Are you on talech? You probably came in through Elavon. Most talech merchants run on CSV exports — we ingest that today and live API is shipping this month. Either way, you'll see what your reports aren't telling you within 24 hours."

**Why talech merchants close:**
- Many feel "stuck" on talech with no analytics layer — open to anything that adds value
- CSV path means you don't need to wait for engineering
- Multi-vertical means broad appeal (restaurant + retail mix)

**Why this is the wedge:** talech sits inside the U.S. Bank / Elavon distribution machine — every talech merchant is also an Elavon processing customer. Winning the talech integration doubles as a wedge into the much larger Elavon merchant book (8,000+ merchants and $2.3B annual processing volume at time of the 2019 U.S. Bancorp acquisition). The self-serve merchant token is the unlock: we don't need bank-grade partner approval to start, which makes talech materially easier than Heartland or Clover-on-Fiserv.

**Operator tells:** iPad on a stand running the talech app (often paired with an Elavon-branded card reader), login at `app.talech.com`, "we use talech" or "the iPad POS from our bank / Elavon."

## What blocks live status today

- **Registry is `csv_only`** with no `base_url`, endpoints, or auth — needs rewrite to token-auth REST
- **API host (`api.talech.com` vs `api-eu.talech.com`), exact resource paths, pagination, and date params not openly published** — we need a live merchant token to introspect the OpenAPI/Swagger spec
- **No webhook channel** — pure poll model has to be designed
- **Email-delivered token onboarding** needs a Meridian-side inbox handler (token arrives via email, not via UI)
- Estimated effort to LIVE: **1–2 weeks** once we have one pilot merchant token
- No vendor blocker — talech doesn't require Elavon partner gate

## Reference docs

- Developer access help article: https://help.talech.com/hc/en-us/articles/115004761986-How-do-I-give-Developers-access-to-my-talech-account-
- API access request article: https://help.talech.com/hc/en-us/articles/218019803-Requesting-API-Access
- talech API merchants PDF: http://ppsusa.com/wp-content/uploads/2020/04/Talech-API-for-Merchants.pdf
- Elavon talech product page: https://www.elavon.com/solutions/accept-payments-in-person/point-of-sale-software-solutions/talech-retail.html
- Merchant Maverick review (tiers + pricing): https://www.merchantmaverick.com/reviews/talech-review/

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (talech config — csv_only currently) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #9 — Elavon gate not required) + docs/playbook/_status/pos/talech.md (Phase 1)_
