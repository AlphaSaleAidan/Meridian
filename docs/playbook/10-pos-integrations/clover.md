# Clover

> Status: **LIVE** (with one known bug — see below)
> Category: multi-vertical (heavy in smoke shops, small retail, casual restaurants)
> Auth: OAuth (bearer, per-merchant)

## What you tell the merchant

"Clover connection takes about 2 minutes. We connect via Clover's app marketplace OAuth, pull your last 18 months of orders, and have first insights in 24 hours."

## How the merchant connects

1. From the Meridian portal, **Settings → POS Connections → Connect Clover**
2. They're redirected to Clover's authorization screen, log in with their merchant credentials
3. They approve scopes (orders, items, employees, customers)
4. We get the merchant ID + access token, begin backfill

Typical time to connect: **2–3 minutes**.

**Partner program:** Meridian's Clover App Market listing (https://www.clover.com/developers) is **pending approval** — read-only OAuth sync works today, but write access (order injection) stays gated until the review lands. See [Clover — read-only today](clover-read-only.md) for the exact merchant-expectation language; never tell a merchant we're already approved.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll (webhook upgrade in roadmap) | 18 months |
| Items / catalog | hourly | full history |
| Employees | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.clover.com/v3/merchants/{merchant_id}`

## What features they get

Nearly the full POS-analytics suite. Clover's data is solid; the gap vs Square is webhook latency (we're hourly until webhooks ship).

- Money Left on Table
- Revenue trend + forecasting
- Peak hours
- Customer LTV (where customer IDs exist)
- Basket analysis
- Product velocity + inventory intelligence
- Employee performance
- Discount/promo ROI
- Anomaly detection (huge for smoke shops — shrinkage signal)

## What features they DON'T get

- Real-time alerts within seconds of a transaction — currently hourly batch. Webhooks shipping in the roadmap.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Long-lived merchants silently 401** | **Token-refresh bug** — old code comment claimed Clover tokens never expire; they do. Pending fix. | One-click reconnect from portal (manual workaround until fix ships) — see `40-troubleshooting/pos-connection-failures.md` |
| Backfill stalls around 50% | 429 throttling — Clover allows 12 req/sec sustained / 16 burst; apps sharing a token share the budget | We auto-throttle and resume; share the standard rate limiter across workers, not per-task. Large merchants may take 12+ hours |
| Webhook returns 200 but no DB write | Missing entity-type stamp during parse (payload only carries `{type, objectId, ts}` — handlers re-fetch) | Engineering fix — stamp entity from subscription verification code |
| Missing customer data | Merchant doesn't capture customer info at checkout | Expected — customer LTV agent falls back to anonymous bucketing |

## Sales angle

**Opener:** "Are you on Clover? Most Clover smoke shop / retail owners are losing 6–8% to shrinkage they can't see — we catch it in the transaction data."

**Why Clover is high-conversion in your pipeline:**
- Dominant in smoke shops + small retail
- Owners are price-sensitive but close fast on the shrinkage angle
- Self-serve OAuth — they can connect during the demo

**Why this is the wedge:** Clover is the largest US cloud POS by volume (~$133B+ annualized), owned by Fiserv and sold through banks/ISOs. That bank/ISO channel reaches merchants Meridian couldn't direct. Pitch: "we speak Clover natively" vs. CSV-only competitors. Operator tell: "we got it from our bank" / "Fiserv set us up."

**Avoid:**
- Don't pitch Clover merchants on real-time alerts (we're hourly today)
- Don't promise webhook-driven features until that ships

## What blocks live status today

- **Token refresh not implemented** in `src/clover/oauth.py` — published apps now receive expiring tokens, so long-lived connections silently 401. Tracked as a separate PR. Severity high but doesn't break new merchants; bites at the multi-month mark. Workaround: reconnect.
- **No `list_refunds()` wrapper** in `client.py` — refunds endpoint exists (`/refunds`, 90-day window) but isn't surfaced.
- **Webhook dispatch needs `_entity_type` stamping** during parse from subscription metadata.

## Reference docs

- Clover developer portal: https://www.clover.com/developers
- API reference: https://docs.clover.com/dev/reference/paygetrefunds-3
- Test token generation: https://docs.clover.com/dev/docs/generate-a-test-api-token
- FAQs: https://docs.clover.com/dev/docs/faqs
- Sandbox host: `sandbox.dev.clover.com` (OAuth) + `apisandbox.dev.clover.com` (REST)

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (clover config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #2, production issue #1) + docs/playbook/_status/pos/clover.md (Phase 1)_
