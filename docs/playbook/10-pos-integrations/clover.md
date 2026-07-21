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

## How direct kitchen injection works (built, pending live verification)

Phone orders can now land in a Clover merchant's kitchen the way a normal ticket does — no staff re-keying. Three API calls, in order:

1. **Order created** via the Clover API (`POST /v3/merchants/{mId}/orders`, state `open`) — it appears in the merchant's Orders app.
2. **Line items added** — one per unit, with per-item special instructions, so the ticket reads like a staff-entered order.
3. **Print event fired** (`POST /v3/merchants/{mId}/print_event` with the order id) — this is the step that actually makes the ticket print. An API-created Clover order **never prints on its own**; the print event routes it to the merchant's order printer (or the device's onboard printer when no order printer is set).

Print failure is deliberately non-fatal: if the merchant has no printer configured or no device online, the order still exists on the register and support can see `kitchen_fired` / `kitchen_fire_status` on the order record. Ops kill-switch: `CLOVER_KITCHEN_FIRE_ENABLED=0` skips the print step without touching order creation.

**Two human prerequisites before this goes live for a merchant:**

1. Grant **ORDERS and INVENTORY write** permissions on the Meridian Clover app in the Clover developer dashboard (app-level setting).
2. The merchant **re-OAuths via the 1-click connect link** so their token picks up the new write scopes.

Note: Clover App Market approval gates *marketplace distribution* only — it does **not** gate these API writes for merchants we onboard directly through our own OAuth link.

**The live prove-out:** connect a real Clover merchant, hit the **"send test order"** button in setup, and watch their printer. The button pushes a clearly-marked $-minimal test ticket through the exact live pipeline, then reads the order back from Clover (exists + open + line items) to confirm end-to-end. Until a real merchant's printer has fired, treat this leg as built-but-unproven.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Long-lived merchants silently 401** | **Token-refresh bug** — old code comment claimed Clover tokens never expire; they do. Pending fix. | One-click reconnect from portal (manual workaround until fix ships) — see `40-troubleshooting/pos-connection-failures.md` |
| Backfill stalls around 50% | 429 throttling — Clover allows 12 req/sec sustained / 16 burst; apps sharing a token share the budget | We auto-throttle and resume; share the standard rate limiter across workers, not per-task. Large merchants may take 12+ hours |
| Webhook returns 200 but no DB write | Missing entity-type stamp during parse (payload only carries `{type, objectId, ts}` — handlers re-fetch) | Engineering fix — stamp entity from subscription verification code |
| Missing customer data | Merchant doesn't capture customer info at checkout | Expected — customer LTV agent falls back to anonymous bucketing |
| **Injected order shows in the Orders app but never prints a kitchen ticket** | Merchant has **no default order printer** — Clover 400s our `print_event` with "The default printing device is missing" (verified live 2026-07-21; explicit device/printer targeting doesn't bypass it). Dispatch reports `kitchen_print_reason=no_default_printer`; the order still lands on the register. | Merchant-side, one-time: on the Clover register → **Setup → Printers → set the kitchen/order printer as default**. Make this an onboarding checklist step for every order-injection merchant. |

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

_Last updated: 2026-07-16 (direct kitchen injection: built, pending live verification)_
_Sourced from: src/services/pos_connectors/registry.py (clover config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #2, production issue #1) + docs/playbook/_status/pos/clover.md (Phase 1)_
