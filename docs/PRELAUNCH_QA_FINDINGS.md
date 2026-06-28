# Pre-Launch QA Findings — Meridian (2026-06-28)

Full-product sweep across 7 domains (public funnel/auth, POS connect, phone agent, payments, camera, merchant portal, API security). Each finding is code-located; **LIVE** = reproduced against prod read-only. Deduplicated across domains.

**Counts:** ~14 P0 · ~17 P1 · ~16 P2 · ~7 P3.
**Bottom line:** do NOT open self-service onboarding until the P0s are fixed. Several are unauthenticated data/abuse endpoints **live in prod right now**, and the phone agent silently drops real orders for the default (no-POS) merchant.

---

## 🔴 P0 — Launch blockers

### Security — unauthenticated endpoints LIVE in prod
1. **`GET /api/credits/ledger/{merchant_id}` — no auth (LIVE 200).** Full credit/billing ledger for any org readable with no creds. `credits.py:96` (note: `/balance` right above it correctly uses `Depends(require_jwt)`). Fix: add `require_jwt` + org-member check.
2. **`POST /api/credits/starter-grant/{merchant_id}` — no auth (confirmed: `def post_starter_grant(merchant_id)`, no Depends).** Anyone can create starter-grant rows / pre-consume a merchant's one-time grant. `credits.py:167`.
3. **`POST /api/onboarding/mark-onboarded` — no auth (LIVE 200).** Anyone can mark any org onboarded, bypassing setup/payment gating. `onboarding.py:515`.
4. **`POST /api/onboarding/send-invoice-sms` — no auth.** Unauthenticated SMS send with attacker-controlled number + URL → SMS phishing/spam on Meridian's Telnyx account. `onboarding.py:554`.
5. **Twilio phone webhooks: no `X-Twilio-Signature` verification + raw PAN/CVV held in app memory.** Forged `CallSid` can drive the order/DTMF state machine; storing raw card+CVV puts the backend in PCI scope. `phone.py` (no `RequestValidator`; `phone.py:1573/1612`). Fix: verify signature on every Twilio webhook; move card entry to Twilio `<Pay>`/Stripe so raw PAN/CVV never touch app code.
6. **Vision tables RLS `FOR ALL USING(true)` applies to `public` (not `TO service_role`).** Same class as the #198 bug just fixed — if `authenticated` has default SELECT, cross-tenant camera/occupancy/visitor data is readable. `20260516_vision_cameras.sql:80`. **Verify in prod DB + scope to service_role.**
7. **`us_leads` RLS has no per-rep scoping.** Any authenticated rep can read/write/delete ALL US leads via the anon key. `20260522_us_leads_rls.sql`. (Also a dead `GRANT SELECT TO anon`.)

### Money
8. **Per-order service fee defaults to $0 (CONFIRMED, 3 sites).** `MERIDIAN_SERVICE_FEE_CENTS`/`MERIDIAN_PLATFORM_FEE_BPS` default `"0"` → `application_fee` never added → **Meridian earns $0 on every phone order** and the voice-ledger credits $0. `payment_links.py:33,38`, `stripe_connect.py:197`. Fix: set the env vars (the pending $1.50 decision) AND change defaults to non-zero / assert >0 when `UNIFIED_PAYMENTS_ENABLED=1`.
9. **Incomplete-Stripe merchant → platform captures the payment.** If `stripe_charges_enabled` is stale/false, `connect_account=""` → no destination charge → full order amount lands in Meridian's platform account while the kitchen ticket releases. Merchant silently unpaid. `payment_links.py:119-122,173-181`. Fix: live `Account.retrieve()` before checkout for real merchants; fail loudly.
10. **Double commission on webhook retry (Square + Stripe).** Commission insert has no idempotency/dedup; Stripe/Square retry on 5xx → rep paid N× per deal. `billing.py:557-598`, `stripe_checkout.py:319-334`. Fix: reuse `_record_webhook_event` dedup (already used for Square POS webhooks).
11. **No Stripe refund endpoint exists.** Unified-payments (Stripe Connect) orders can't be refunded through Meridian at all. Fix: add `POST /api/stripe/connect/refund` with `reverse_transfer=True, refund_application_fee=True`.

### Order integrity / phone agent
12. **Orders silently dropped for no-POS merchants (the DEFAULT state).** `_dispatch_order` returns fabricated `success=True, MRD-####` when `pos_system==""` without calling the SMS/email fallback. Caller hears "order placed"; merchant gets nothing. `phone.py:1148-1157`. Fix: only short-circuit for the demo merchant; otherwise run `_fallback_order`.
13. **"Activate" ignores save failure → agent silently broken.** `handleWizardDone` discards `saveConfig()`'s return and marks setup complete even on 4xx/5xx; next call falls to DEMO_MERCHANT (demo menu/greeting, order never routed). `PhoneOrdersPage.tsx:627-631`, `SetupWizard.tsx:562-587`. Fix: only complete on success; show error.
14. **Portal crashes on real call statuses.** Backend writes `order_failed`/`credits_paused`/`after_hours`/`order_placed_awaiting_card`; frontend `STATUS_CFG[status]` is undefined → TypeError crashes Overview + Call Log + Transcript modal after the first failed/paused call. `PhoneOrdersPage.tsx:105/246/296`, `phone-orders-demo-data.ts:21`. Fix: add the statuses (or a fallback).

---

## 🟠 P1 — Breaks a core flow

15. **Stripe Connect status fetch missing auth headers → every real merchant sees "Not Connected"** (the Get-Paid money flow is unreachable). `PhoneOrdersPage.tsx:400` (found by 2 agents). Fix: `headers: await getAuthHeaders()`.
16. **Square `oauth=partial` callback handled by NO wizard** — merchant authorizes, DB save fails, connection silently lost, no retry. `oauth.py:321`, `clover_oauth.py:308`, both onboarding wizards. Fix: handle `partial` branch.
17. **CSV import always imports 0 records** — `file: bytes = b""` missing `File(...)`. `pos_connections.py:711`. Fix: `File(...)`.
18. **`GET /api/square/status` returns connected when only Clover is live** (provider-agnostic query) → wrong provider shown / `pos_system` clobbered. `oauth.py:345`. Fix: filter `provider=eq.square`.
19. **Clover menu sync skips token refresh → fails silently after ~30 min** (token expiry). `phone_dashboard.py:219`. Fix: `ensure_fresh_clover_token`.
20. **`menu_sync_error` never written → sync failures show no error**, widget just disappears. `phone_dashboard.py` sync impl. Fix: write the error field on failure.
21. **Self-service checkout creates TWO $250 invoices** (setup + monthly) → customer double-billed. `CustomerOnboardingWizard.tsx:484-508`. Fix: only the recurring invoice unless a rep set a setup fee.
22. **Email-confirmation signup traps user on POS step with null org** (no "check your email" handling). `CustomerOnboardingWizard.tsx:282-293`.
23. **Already-paid / expired short link shows Stripe's native page, not the branded one** — webhook never sets `checkout_sessions.status`, and string check misses `"completed"`. `pay_redirect.py:71`, `stripe_connect.py`.
24. **No Stripe `payment_failed`/`session.expired` handling** — declined phone-order card = silent: no merchant alert, no retry SMS, kitchen ticket stuck. `stripe_connect.py:155`.
25. **`payment_intent.succeeded` path releases possibly-wrong order** (no `pos_order_id` in PI metadata → falls back to latest-pending by phone). `stripe_connect.py:155-169`. Fix: only release on `checkout.session.completed`.
26. **Qwen LLM fallback carries no tools → orders can't be placed** if DeepSeek+SambaNova both down (agent chats but never submits). `phone.py:500-521`. Fix: pass tools or hang up gracefully.
27. **Setup wizard "Next" not disabled during number provisioning** → can activate with empty `phone_number` → inbound calls don't resolve merchant. `SetupWizard.tsx:554`.
28. **Canada merchants get `country:'US'` + `taxRate:0.08`** hardcoded in the Phone pillar → wrong tax on receipts. `PhoneOrdersPage.tsx:620-621`. Fix: use the `cad` flag.
29. **Camera "Analytics" tab serves the public SEO marketing page** (pricing, FAQ, CTAs) to logged-in merchants — and it advertises "opt-in identity" as live, contradicting the gate. `merchantPillars.tsx:35` imports `@/pages/seo/CameraIntelligencePage`. Fix: import the app page.
30. **Identity-tier vision agents run without the gate** — `DemographicProfilerAgent`/`CustomerRecognizerAgent` read pre-gate `vision_visitors` rows and return demographics/face data even with `CAMERA_IDENTITY_ENABLED=0`. `vision.py:546-554`. Fix: gate the agent list.
31. **Notification-prefs fetches still unauthenticated (CA-16)** — GET/PUT no auth headers; endpoints 404 today but become a BOLA when implemented. `SettingsPage.tsx:58-77`.
32. **`email.py /send` missing `enforce_service_member`** — any authenticated user can send email branded as any org. `email.py:29`.
33. **Rep attribution silently dropped** — `connected_by_rep_id` not in `ConnectRequest` model → never persisted (commission attribution broken). `pos_connections.py:89`.
34. **`POSSelectorPanel` manual connect (Toast) missing auth headers → 401.** `POSSelectorPanel.tsx:332`.

---

## 🟡 P2 — Noticeable defects (representative; full list in agent outputs)
- **Stale pricing everywhere**: `index.html` JSON-LD + FAQ ($250/$490/$980), `/faq` page, and 6 SEO pages still advertise retired tiers despite Schedule-a-Quote. (SEO rich-results show old prices to prospects.)
- **Two price tables drift**: Square billing $250 vs Stripe subscription $299 for "standard". `billing.py:37` vs `stripe_checkout.py:42`.
- **CAD orders default to USD** in the Square fallback link. `payment_links.py:273`.
- **"Top Actions" pillar ignores `topActions:false` flag** (always shows); **mobile bottom nav overflows** with 8 pillars (Camera/Settings clipped). `MerchantLayout.tsx`.
- **POS UI leaking into the rep portal** (Kanban "POS Connected" column, "POS connected & billing" copy) — violates the ZERO-POS-UI doctrine (3 prior clobber incidents). `CanadaPortalDashboardPage.tsx`.
- **Analytics showcase claims "from your live feeds"** but shows hardcoded numbers incl. a Demographics card (gated feature) to real merchants. `CameraAnalyticsShowcase.tsx:55`.
- **Settings "Saved" shown on save failure** (ignores `saveConfig` result). `SettingsTab.tsx:44`.
- **"Active" badge hardcoded** — shows Active even when agent deactivated. `PhoneOrdersPage.tsx:656`.
- **`order_routing` wizard choice never read** by the call handler. `phone.py:_dispatch_order`.
- **LiveCallsBanner shows random fake "1 active call"** on real dashboards (no `isDemo` gate). `LiveCallsBanner.tsx:29`.
- **Canada login auto-logs-out** an already-authenticated user landing on `/canada/login`. `CanadaLoginPage.tsx:38`.
- **Password min length 6 (wizard) vs 8 (signup)** inconsistency.
- **Stripe SDK exception strings leaked** in error `detail`. `stripe_checkout.py:250`, `content.py`.
- **`/api/content/scrape/website` unauthenticated** outbound-fetch proxy. `content.py:615`.
- **Stripe setup fee charges immediately even with `first_month_free`** (no "free month" for the setup fee → chargeback risk). `stripe_checkout.py:146`.
- **Vapi webhook fail-OPEN** if `VAPI_SERVER_SECRET` unset (safe today; should fail closed). `vapi_webhook.py:255`.
- **`GET /api/compliance/pending/{user_id}` unauthenticated (LIVE 200)** — leaks which policies a user hasn't accepted.
- **Live-view failure shows generic "Could not connect"** even when the real cause is "live view off". `LiveCamerasPage.tsx:40`.
- **Pre-existing `opt_in_identity` cameras never downgraded** on PATCH (gate only checks the incoming field). `vision.py:224`.

---

## 🔵 P3 — Polish (selected)
- Dead `OnboardingWizard.tsx` navigates to nonexistent `/dashboard`, has hardcoded prices + fake promo.
- Schedule-a-Quote date picker only offers today/tomorrow (weekend dead-ends).
- Stale `v0.2.0` version strings on public login/signup footers.
- CSP allows `unsafe-inline`/`unsafe-eval`.
- Personality panel settings not persisted.
- Canada phone wizard uses loose phone validation (not E.164) → bad transfer numbers hang up callers.
- Privacy step "Next" disabled with no hint the consent checkbox is required.
- Camera demo page implies in-browser face tracking == production capability.

---

## ⚙️ Owner: Aidan / config (verify in Railway, not code)
- **Set `MERIDIAN_SERVICE_FEE_CENTS`** (the $1.50 decision) — without it, $0 revenue (P0-8).
- **Confirm `UNIFIED_PAYMENTS_ENABLED=1`** in prod.
- **Confirm `TENANCY_ENFORCEMENT_DISABLED` is unset/false** — if true, ALL cross-tenant enforcement is silently off.
- **Set `VAPI_SERVER_SECRET`, `STRIPE_CONNECT_WEBHOOK_SECRET`** (the latter gates charges_enabled sync → P0-9).

---

## Recommended fix order for Wednesday
1. **Auth holes (P0 #1-7)** — one focused PR: add `require_jwt`/`require_service_auth`/`enforce_service_member` to the open endpoints; scope vision + us_leads RLS to service_role; Twilio signature verify. *Highest risk, all live.*
2. **Order integrity (P0 #12-14)** — fallback for no-POS orders, activate-on-success-only, status-crash fallback.
3. **Money (P0 #8-11 + env)** — set the fee env, dedup commissions, refund endpoint, charges_enabled live check.
4. **P1 connect/get-paid bugs** (#15-20) — the merchant can't actually see they're connected/paid.
5. Stale-pricing sweep + the rest of P2/P3 post-launch.
