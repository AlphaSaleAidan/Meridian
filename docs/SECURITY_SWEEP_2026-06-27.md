# Remediation status (autonomous sprint, 2026-06-27)

The findings below were produced by a read-only sweep. Several were FIXED + deployed
to production the same day:

| Finding | Status |
|---|---|
| Toast webhook: no HMAC verification | **FIXED** — `Toast-Signature` HMAC-SHA256 verified (PR #176, live). Note: `TOAST_WEBHOOK_SECRET` is unset in prod (Toast not live), so it fails closed (503). |
| Vision camera PATCH/DELETE/heartbeat unauthenticated (H1) | **FIXED** — PATCH/DELETE require `org_id` + camera-belongs-to-org check; heartbeat → device-token (PR #176, live; DELETE 200→422 verified). |
| Payouts ledger readable by any logged-in user | **FIXED** — locked to `require_admin_auth` (machine/admin only) (PR #176, live). |
| `require_service_auth` authenticates without authorizing (C1, cross-tenant BOLA on phone_dashboard/schedule/website/intelligence/stripe_connect) | **PARTIAL** — foundation shipped (`require_service_auth` returns a principal; `require_admin_auth` + `enforce_service_member` added). Per-route membership enforcement is NOT yet applied to the remaining endpoints because it affects rep-vs-merchant access and needs a deliberate rollout. **Highest remaining priority.** |
| Vapi webhook fail-open when secret unset (M2) | Verified `VAPI_SERVER_SECRET` IS set in prod → fails closed (401 verified). Recommend keeping it set. |

---

# Meridian Security Sweep — FastAPI Backend + React

Scope: `/root/meridian-sprint` @ `origin/main` (HEAD `918193da`). READ-ONLY review.
Focus: `src/api/` (routes, auth, middleware). Verified against source; no runtime testing.

Auth primitives (`src/api/auth.py`):
- `require_admin` — `X-Admin-Key == MERIDIAN_ADMIN_KEY` (fail-closed if unset → 503).
- `require_jwt` — valid Supabase session (authentication only, NO org binding).
- `require_admin_jwt` — JWT + email in hardcoded `ADMIN_EMAILS`.
- `require_org_access` (router-level dep) — enforces JWT + org membership **only when an `org_id`/`merchant_id` is present in query, path, OR body**. If none is present it is a **silent no-op that returns None and requires NO auth at all**.
- `require_org_member(user, org_id)` — explicit in-handler membership check.
- `require_service_auth` — accepts `X-Admin-Key`, `MERIDIAN_SERVICE_TOKEN`, **OR any valid Supabase user session**. No org binding.

---

## CRITICAL

### C1. `require_service_auth` authenticates but does not authorize → cross-tenant BOLA across the whole "service" surface
`src/api/auth.py:256-273`. The fallback `user = await _verify_supabase_token(token); if user: return` means **any logged-in Supabase user (any merchant who ever signed up) passes `require_service_auth`**. Every endpoint that takes a `merchant_id`/`org_id` in the path/body under this guard performs NO membership check, so any authenticated user can read/write any other tenant's data by supplying a different id.

Confirmed exposed (non-exhaustive):
- `src/api/routes/payouts.py:28-104` — `GET /api/payouts/summary|reps|balances|history|reps/{rep_id}/commissions` returns the **entire sales-rep commission/payout ledger for ALL reps** to any authenticated user. No id even needed.
- `src/api/routes/phone_dashboard.py:402-451` — `GET /api/phone-dashboard/calls/{merchant_id}|orders/{merchant_id}|stats/{merchant_id}` exposes another tenant's **call logs, phone orders (customer names, phone numbers, delivery addresses)**. `POST /config` (`:79`) lets you overwrite another merchant's phone agent config; `provision-number` (`:714`).
- `src/api/routes/schedule.py` — all 13 routes (`staff`, `shifts`, `publish`, `projected-revenue`, …) read/write any merchant's staff & schedule by `merchant_id`.
- `src/api/routes/website.py` — `config`, `save`, `publish`, `analytics/{merchant_id}`, `orders/{merchant_id}`, `DELETE /{merchant_id}` for any merchant.
- `src/api/routes/intelligence.py:55-145` — `health/financial/benchmarks/{org_id}` financial ratios for any org.
- `src/api/routes/stripe_connect.py:58-121` — `onboard`/`status` for any `merchant_id`.
- Also: `pos.py` select/status, `inference.py` (whole router), `email.py /send`, `portal.py /generate`, `us.py /create-customer`, `onboarding.py create-account/provision-customer`.

Impact: full multi-tenant data breach (customer PII, financials) + cross-tenant writes, gated only by "have a valid account + know/guess the target id". Many ids (merchant_id) flow through the frontend and are enumerable.
Fix: `require_service_auth` must NOT accept arbitrary user sessions for tenant-scoped endpoints. Either (a) restrict it to `MERIDIAN_SERVICE_TOKEN`/admin-key only, or (b) keep user acceptance but additionally call `require_org_member(user, merchant_id)` in every handler. Payouts/financial endpoints should be `require_admin_jwt`.

---

## HIGH

### H1. Vision camera mutation endpoints are fully unauthenticated (router guard is a no-op)
`src/api/routes/vision.py` — router declares `dependencies=[Depends(require_org_access)]` (`:27`), but these routes carry **no `org_id` in path/query/body**, so the guard returns None and enforces nothing:
- `PATCH /api/vision/cameras/{camera_id}` (`:162`) — `CameraUpdateRequest` has no `org_id`. Anyone (no auth) can flip `compliance_mode` and **enable privacy-invasive features on any camera** — `demographics`, `vip` (face matching), `live_view`, `depth` — which all default OFF (`:46-49`).
- `DELETE /api/vision/cameras/{camera_id}` (`:199`) — unauth delete of any camera by id.
- `POST /api/vision/cameras/{camera_id}/heartbeat` (`:212`) — unauth status spoofing.

All operate filtering by `id` only, no org scoping. camera_id is a UUID (some obscurity) but there is zero authn/authz. Privacy/regulatory blast radius (turning on facial recognition on a stranger's camera).
Fix: require `org_id` (query) on these routes so `require_org_access` engages, plus confirm the camera belongs to that org (the pattern already used correctly in `request_live_view` `:241-259`).

### H2. Telephony (Twilio) webhooks: raw card capture (PAN + CVV) with no signature verification
`src/api/routes/phone.py`. No `X-Twilio-Signature` validation exists anywhere in the file (grep: none). All Twilio webhooks are open to the internet:
- `POST /twilio/voice` (`:790`), `/gather` (`:925`), `/status` (`:1163`), `/payment-webhook` (`:1404`), and the pay flow `/pay/start|number|expiry|cvv|zip` (`:1513-1597`).
- The pay flow captures **raw PAN** (`cap.pan = digits`, `:1553`), **expiry** (`:1571`), and **CVV** (`cap.cvv = digits`, `:1591`) from DTMF into an in-memory capture object (`card_on_phone`).

Two problems: (1) capturing/holding raw PAN+CVV in app memory pulls the backend into PCI-DSS scope, and storing CVV (even transiently in a mutable object) violates PCI requirements — Twilio `<Pay>` / a tokenizing gateway should handle this; (2) with no Twilio signature check, anyone can drive these endpoints (spoof orders, probe/POST into the card-capture state machine by guessing a `CallSid`).
Fix: verify `X-Twilio-Signature` (Twilio `RequestValidator`) on every telephony webhook; move card entry to Twilio `<Pay>`/Stripe so raw PAN/CVV never reach the app; never persist CVV.

---

## MEDIUM

### M1. Toast webhook accepts events without HMAC verification (known gap, confirmed)
`src/api/routes/webhooks.py:342-384`. It fails closed if `TOAST_WEBHOOK_SECRET` is unset (`:359-362`, returns 503) but, when set, it logs `"Toast webhook accepted WITHOUT signature verification"` (`:366`) and processes the payload. An attacker who knows a `restaurantGuid` can forge `order.created`/`restaurant.disconnected` events → trigger POS syncs or **force-disconnect a merchant's Toast connection** (`_process_toast_webhook` `:387-416`, calls `_disconnect_merchant`). (Square `:148-220` and Clover `:266-308` correctly verify and fail-closed.)
Fix: implement the Toast HMAC check (TODO at `:364`) and reject on mismatch.

### M2. Vapi webhook is fail-open when `VAPI_SERVER_SECRET` is unset
`src/api/routes/vapi_webhook.py:250-259`. The `x-vapi-secret` check only runs `if VAPI_SERVER_SECRET:`. If the env var is not set in prod, the **order-placing webhook is open to the internet** — `submit_order` runs the real pipeline (POS order create + Stripe pay-link SMS to an attacker-supplied caller number). Cannot confirm the prod env value from here; flag to verify it is set. (Contrast Square/Clover/Stripe which fail-closed.)
Fix: fail closed — require the secret to be configured in production and reject if absent.

### M3. Spaces sub-routes unauthenticated (router `require_org_access` no-op)
`src/api/routes/spaces.py` (router dep at `:25`). Routes lacking `org_id`/`merchant_id`:
- `GET /api/spaces/{space_id}/model` (`:253`) — unauth read of any space's 3D model file. Path built from user input `Path("data/spaces")/space_id` (`:257`); traversal impact is limited because only `model.{splat,ply,spz}` is served, but the cross-tenant read is real.
- `PATCH /api/spaces/{space_id}/status` (`:325`) — unauth status change, filters by `id` only.
- `POST /api/spaces/{space_id}/zones` (`:343`) — `ZonesRequest` has no org field → unauth zone writes to any space by id.
Fix: scope these by org and engage the guard (require `org_id`, verify the space belongs to it).

### M4. Credits: IDOR reads + unauthenticated starter-grant
`src/api/routes/credits.py`:
- `GET /balance/{merchant_id}` (`:82`) and `GET /ledger/{merchant_id}` (`:96`) use `require_jwt` only — no `require_org_member` — so any authenticated user reads any merchant's credit balance/ledger. (`/purchase` and `/deduct` correctly call `require_org_member`/admin.)
- `POST /starter-grant/{merchant_id}` (`:167`) has **no auth dependency** — unauthenticated; idempotent so impact is limited to creating starter-grant ledger entries for arbitrary merchant_ids / pre-empting grants, but it is an unauthenticated credit-issuing write.
Fix: add `require_org_member` to balance/ledger; require auth on starter-grant.

### M5. `content /scrape/website` unauthenticated outbound fetch
`src/api/routes/content.py:615`. No auth dependency (other content routes use `require_jwt`+`require_org_member`). SSRF is well-handled — `is_private_url` pre-check + manual redirect loop re-checking each hop (`:626-650`) — so this is not an SSRF hole, but it is an unauthenticated endpoint that fetches attacker-chosen public URLs (scraping proxy / minor amplification; theoretical DNS-rebind TOCTOU between `is_private_url` and the httpx fetch).
Fix: add `require_jwt`/org-member; rate-limit (it is not in the middleware `RATE_LIMITS` map).

### M6. Rate limiting is in-memory per-worker and per-process
`src/api/middleware/rate_limiter.py` (module-level `_buckets` dict) and `src/api/auth.py:314-379`. With multiple Uvicorn/Gunicorn workers the effective limit is `limit × worker_count`, and it resets on restart/redeploy. Client IP is taken from the **last** `X-Forwarded-For` hop (`:54-56`, `auth.py:358-363`) — correct only if exactly one trusted proxy is in front; an extra hop lets clients influence the key. Adequate as a coarse guard, not as abuse prevention for signup/credential endpoints.
Fix: back rate limits with a shared store (Redis) for multi-worker correctness; pin the trusted-proxy hop count.

---

## LOW / INFORMATIONAL

- **L1. CSP allows `unsafe-inline` and `unsafe-eval` for scripts** — `src/api/middleware/security_headers.py:16`. Weakens XSS defense. Otherwise headers are strong (HSTS preload, X-Frame DENY, nosniff, frame-ancestors none, Permissions-Policy `payment=()`).
- **L2. `POST /api/stripe/create-checkout` unauthenticated** — `src/api/routes/stripe_checkout.py:100`. Allows `custom_price_cents` (`:114`); price can only be set downward for the attacker's own payment, so abuse is limited to spurious Stripe session creation. Consider auth + rate limit. Webhook (`:253`) verifies signature, fail-closed (good).
- **L3. OAuth open-redirect class bug is FIXED** — `src/api/routes/_oauth_return.py:29-40` rejects `//host` and `scheme://`, allowlists on-site prefixes; `FRONTEND_URL` is env-controlled, state is HMAC-signed (`oauth.py:64-111`). `OAUTH_STATE_SECRET` raises `RuntimeError` in prod if unset (`oauth.py:36`); the `test-only` default is non-prod only. Dev ephemeral random secret invalidates in-flight states on restart (availability only). `pay_redirect.py /p/{code}` redirects to a DB-stored Stripe URL with a strict code format check (`:54`) — not user-controlled at redirect time.
- **L4. No hardcoded secrets found** in tracked `src/` (scanned for sk_live/whsec_/re_/AKIA/xoxb/etc.). All keys read from env. Good.
- **L5. No raw SQL** — all DB access goes through a PostgREST-style abstraction; filter *values* are interpolated as `f"eq.{value}"` but passed as httpx-encoded query params, so operator/param injection is not achievable. Low risk; values reaching guarded routes are already membership-validated.
- **L6. `compliance.py` GET `/api/compliance/pending/{user_id}` (`:146`)** unauthenticated read of a user's pending acceptances (low sensitivity). `/api/privacy/request` and `/api/privacy/unsubscribe` are intentionally public (DSAR/opt-out), rate-limited via middleware.
- **L7. CORS** (`app.py:185-215`) is locked to a known allowlist with `allow_credentials=True` (no wildcard) — good. `viktor.space` preview origin is allowlisted (intentional, not the old redirect bug). `FRONTEND_ORIGIN` env appends one extra origin — operationally fine as long as it is set to a trusted value.

---

## Auth-coverage inventory (router-level + notable routes)

| Router | Guard | Notes |
|---|---|---|
| admin, training, garry, garry_patches | `require_admin` (router) | OK |
| inference | `require_service_auth` (router) | see C1 — any user session passes |
| inventory_docs, archives, vision, spaces, dashboard, analytics, cpa, predictive | `require_org_access` (router) | OK **only** where route has org_id/merchant_id; no-op otherwise → H1, M3 |
| billing | mixed: `require_jwt` (checkout/status), `require_service_auth` (invoice/cancel/payment), `require_admin` (renewals/trials); webhook sig-verified | OK |
| credits | mixed | M4 (balance/ledger IDOR, starter-grant open) |
| payouts | `require_service_auth` per-route | **C1 — global financials to any user** |
| phone | none (Twilio webhooks) | **H2 — no Twilio sig, raw card capture** |
| phone_dashboard, schedule, website, intelligence, stripe_connect, pos | `require_service_auth` | **C1** |
| vapi_webhook | `x-vapi-secret` if configured | M2 fail-open |
| webhooks (square/clover/toast) | HMAC/auth-code | square/clover OK; **M1 toast unverified** |
| stripe_checkout | none on create; sig on webhook | L2 |
| canada, us | rep-signup rate-limited; rep CRUD `require_admin_jwt`; leads/stats/team `require_jwt` | leads/stats/team rely on in-handler user filtering — verify per-rep scoping |
| onboarding | mixed (`require_service_auth` create/provision; `require_jwt` connect/verify; **none** on send-welcome/mark-onboarded/send-invoice-sms) | send-invoice-sms (`:551`) unauth → SMS-spam abuse vector (MED-adjacent) |
| compliance | privacy/export + dashboard/breach `require_admin_jwt`; pending/{user_id} none | L6 |
| oauth, clover_oauth, pay_redirect, portal/resolve | public by design, signed state / code format | L3 |

---

## Prioritized fix list

Quick, safe wins (config/dep changes, low regression risk):
1. **M1 Toast** — implement HMAC verify, reject on mismatch.
2. **M2 Vapi** — fail closed in prod (require `VAPI_SERVER_SECRET`); verify it is set now.
3. **H1 Vision** — add required `org_id` query + camera-ownership check to PATCH/DELETE/heartbeat.
4. **M3 Spaces** — org-scope `{space_id}/model|status|zones`.
5. **M4 Credits** — add `require_org_member` to balance/ledger; auth on starter-grant.
6. **M5 content scrape / L2 stripe create-checkout / onboarding send-invoice-sms** — add auth + rate limit.

Needs design / broader change:
7. **C1 `require_service_auth`** — redesign authn-vs-authz: drop blanket user-session acceptance for tenant-scoped endpoints, or thread `require_org_member` through every handler; make payouts/financial admin-only. Highest-impact, touches many files — do behind tests.
8. **H2 Telephony/PCI** — add Twilio `RequestValidator` to all webhooks and move card entry to Twilio `<Pay>`/Stripe so raw PAN/CVV never enter app memory; stop storing CVV.
9. **M6 Rate limiting** — shared (Redis) backend for multi-worker correctness; pin trusted-proxy hop.
10. **L1 CSP** — remove `unsafe-eval`/`unsafe-inline` (needs frontend nonce/hash work).

Verify-in-prod items (cannot confirm from source): `VAPI_SERVER_SECRET`, `TOAST_WEBHOOK_SECRET`, `OAUTH_STATE_SECRET`, `TENANCY_ENFORCEMENT_DISABLED` are all set correctly (the last MUST be unset/false in prod — when truthy it converts every `require_org_access`/`require_org_member` 403 into a logged warning that lets the cross-tenant call through; `auth.py:213,241`).
