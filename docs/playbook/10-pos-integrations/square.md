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
4. Square redirects them back; we begin the historical backfill (locations → team → catalog → 18 mo orders → inventory)
5. They see a progress bar on Settings → POS Connections

Typical time to connect: **2 minutes**. Backfill: **2–6 hours** for 18 months depending on transaction volume. First dashboards usable within minutes (orders phase is the long pole).

**No Square partner approval needed** — self-serve OAuth, any merchant can connect immediately. Partner app registered at https://developer.squareup.com/apps.

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

- **Camera intelligence + cross-reference agents** require the camera intelligence add-on + a supported camera. Not Square-specific.
- **Multi-location rollups** require the multi-location add-on.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Sync stuck at orders phase | Large merchant hitting rate limits on `SearchOrders` (we throttle to ~4 req/sec on batch) | Confirm 429s in logs; backfill resumes month-by-month automatically. ETA 1–30 min for 18 months — no action needed |
| Square disconnected unexpectedly | Merchant revoked from Square Dashboard, or refresh token unused >30 days | `oauth.authorization.revoked` webhook auto-marks disconnected; merchant must re-run connect flow |
| Card brand / last-4 missing on transactions | `payment.created` webhook hadn't fired yet at order import | Wait for payment webhook; values backfill on `_enrich_payment` |
| 401 Unauthorized after a few weeks | Access token expired and auto-refresh cron failed | Check `refresh_token()` logs; manual refresh via OAuthManager or one-click reconnect |

### Edge cases we expect but haven't seen yet
- OAuth screen shows "App not found" — usually wrong environment (sandbox vs prod). Use the production connect link from portal only.
- Backfill stuck at <100% after 24h — see `40-troubleshooting/backfill-stuck.md`.

## Sales angle

**Opener:** "I work with Square merchants who are leaving CA$2,800/mo on the table they don't see. Got 60 seconds?"

**Why Square is your best target:** highest data quality, fastest backfill, fewest objections about "will this break my POS." It won't — we're read-only by default.

**Why this is the wedge:** Square is dominant for sub-$5M-revenue SMBs in the US — single-location and 2–10 location independents (coffee shops, salons, boutiques, food trucks). It's our highest-volume integration target: easy self-serve OAuth, no partner gate, and the merchant base maps perfectly to Meridian's SMB ICP. Lead with Square in demos. If a merchant uses Square Appointments or Square for Restaurants, same OAuth covers both.

**Vertical-specific Square openers:**
- Cafes: "Square gives you a register. We tell you which 15-minute window is your real peak so you schedule the second barista at the right time."
- Smoke shops: "Square's reports show you sales. We show you shrinkage and which SKUs are dead inventory."
- Salons: "Your Square customer list is gold — we flag regulars who haven't rebooked before they switch."

## What blocks live status today

Nothing — OAuth, sync engine, webhooks, and token refresh are all in production (`src/square/`). Open work is UX hardening (the connect flow has 2 extra clicks we want to remove).

## Reference docs

- Square OAuth overview: https://developer.squareup.com/docs/oauth-api/overview
- Authorization URL setup: https://developer.squareup.com/docs/oauth-api/create-urls-for-square-authorization
- Webhooks overview: https://developer.squareup.com/docs/webhooks/overview
- Developer dashboard / app registration: https://developer.squareup.com/apps

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (square config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #1) + docs/playbook/_status/pos/square.md (Phase 1)_
