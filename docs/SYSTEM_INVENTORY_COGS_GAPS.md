# Meridian — System Inventory, COGS & Gap Analysis

> Source: `origin/main` HEAD in `/root/meridian-sprint` (read-only). Branch checked out: `sprint/8h-base`, top commit `918193da`. Generated for a founder-facing system diagram + cost-of-goods table + "not built yet" list.
> Stack: FastAPI backend (`src/`) + a "sidecar" phone-agent package (`services/phone_agent/`), React/Vite frontend (`frontend/`), Supabase Postgres, Railway compute, Cloudflare (Stream + R2). Standalone Node SEO engine (`seo-engine/`) + Jetson edge agent (`edge/`).

---

## 0. One-paragraph mental model

Meridian is a multi-tenant restaurant/SMB operating layer. It (a) **reads** each merchant's POS (Square live; Clover + Toast built) and turns raw sales into analytics + AI insights; (b) **answers the phone** with an AI agent that takes orders and pushes them to the POS; (c) **takes the money** through one Stripe Connect rail regardless of POS, auto-skimming a flat service fee; (d) **watches the room** with edge cameras (people-counting / dwell, optional live view); and (e) wraps it all in rep + merchant **portals** with email + a separate SEO content engine. Revenue = SaaS subscriptions + per-order service fee + voice overage + prepaid AI "credits". The recurring external costs (COGS) are telephony+voice-AI minutes, Stripe processing, LLM tokens, Cloudflare GB-watched, Supabase, and Railway.

```
                         ┌─────────────────── CUSTOMER (diner) ───────────────────┐
                         │  calls DID / texts / scans pay-link                     │
                         ▼                                                         ▼
   Telnyx/Twilio  ──►  phone.py (turn-based)        Vapi line ──► vapi_webhook.py   Stripe Checkout
   (DID + voice)       DeepSeek→SambaNova→Qwen      GPT-4.1 + Deepgram + Elliot     (destination charge)
   Polly TTS           submit_order ─┐              _place_order ─┐                 application_fee=$2.50
                                     ▼                            ▼                       │
                              POS order (Square OPEN/unpaid)  Stripe pay-link + Telnyx SMS│
                                     │                            │                       ▼
                                     ▼                            ▼              voice_ledger(credit stripe_fee)
   Square/Clover/Toast  ◄── connect/digest/propagate ──►  Supabase Postgres  ◄── voice_ledger(debit vapi_call)
   (OAuth read-only)        sync_engine + webhooks         (orders, products, …)         │
                                     │                                                    ▼
                                     ▼                                            Stripe pays merchant daily
                              AI engine / insights / dashboards ──► merchant & rep portals (React + Supabase JWT)

   Jetson edge (YOLO/ByteTrack/DeepFace/Depth) ──15-min buckets──► vision_traffic/visits
                                     └── on-demand WHIP ──► Cloudflare Stream ──WHEP──► browser live view
```

---

## 1. Feature inventory + data / money flows

For each subsystem: entry-point file(s), external services it calls, and the DB tables it touches.

### 1A. Customer payments — Stripe Connect (the money rail)

- **Entry points:**
  - `src/api/routes/stripe_connect.py` — `POST /api/stripe/connect/onboard/{merchant_id}`, `GET …/status/{merchant_id}`, `POST …/webhook`.
  - Per-order checkout creation: `services/phone_agent/payment_links.py` (`create_checkout`, lines 117–197).
  - Branded short link resolver: `src/api/routes/pay_redirect.py` — `GET /p/{code}` → 303 to Stripe URL; `/pay/success`, `/pay/cancel`.
- **External services:** Stripe (`Account.create(type="express")`, `AccountLink.create`, `checkout.Session.create` with `payment_intent_data.transfer_data.destination` = connected account, `Webhook.construct_event`); Telnyx SMS for receipts (`services/phone_agent/sms_checkout.py` → `POST https://api.telnyx.com/v2/messages`).
- **DB tables:** `phone_agent_config` (stripe_account_id, stripe_charges_enabled), `checkout_sessions` (short_code→checkout_url, status), `voice_ledger` (service-fee credit).
- **Money flow:** Diner pays via Stripe Checkout → **destination charge** to merchant's Express account → Stripe deducts processing fee from the *platform* → `application_fee_amount = SERVICE_FEE_CENTS + amount*PLATFORM_FEE_BPS/10000`, capped to `amount-1` (`payment_links.py:178-180`) is retained by Meridian → remainder settles to merchant **daily** → on `checkout.session.completed` a Telnyx receipt SMS fires and `MERIDIAN_SERVICE_FEE_CENTS` is credited to `voice_ledger` (`stripe_connect.py:195-203`).
- **Fee model (exact):** `MERIDIAN_SERVICE_FEE_CENTS=250` ($2.50 flat); `MERIDIAN_PLATFORM_FEE_BPS=0` → **the percentage fee is currently OFF**. There is **no `1.9%`/`0.019` literal anywhere** in the payments code; the percentage rail exists (`PLATFORM_FEE_BPS`) but is set to zero. Flat $2.50 is the only active per-order charge.
- **⚠ Critical gate:** `UNIFIED_PAYMENTS_ENABLED` defaults to `"0"` (`payment_links.py:30`). When off, checkout falls back to native per-POS payment links and **no service fee / short-link is taken at all**. The entire Stripe-Connect fee path only runs when this flag = `1`.

### 1B. SaaS subscription billing (Meridian's recurring revenue)

Two *separate* billing surfaces with two *different* price sheets — flag this, it's a real inconsistency:
- `src/api/routes/stripe_checkout.py` — Stripe subscriptions: **$299 / $599 / $1199** (`PLAN_PRICES`, lines 41-45). Tables: `checkout_sessions`, `organizations`, `commissions` (setup fee → 100% to rep).
- `src/billing/billing_service.py` + `src/api/routes/billing.py` — Square invoices/subscriptions: **$250 / $500 / $1000 / $65-wk** (`PLAN_PRICES`, lines 45-50). Square `/v2/online-checkout/payment-links`, `/v2/invoices(+/publish)`, `/v2/subscriptions`, `/v2/customers`, `/v2/cards`, `/v2/catalog`. Tables: `subscriptions`, `commissions`. Renewal idempotency key `renewal-{sub}-{period_end}`.
- Prepaid AI **credits**: `src/api/routes/credits.py` + `src/credits/purchase.py`. Packs: starter 2k/$2(USD)·$2.75(CAD); popular 5k/$4.50·$6.20; pro 15k/$12·$16.50; agency 50k/$35·$48. Free `STARTER_GRANT=1000` on signup. Square invoices fund packs. Tables: `credit_ledger`, `credit_purchases`.

### 1C. AI phone agent + voice billing

Two independent call paths plus an SMS path:
- **Turn-based (live default)** — `src/api/routes/phone.py`, prefix `/twilio`. `POST /twilio/voice` (greeting + credit gate), `/twilio/gather` (per-turn STT→LLM→TwiML, runs `submit_order`), `/twilio/status` (charges credits), `WS /twilio/media-stream/{merchant_id}` (Pipecat, gated). Telephony: **Telnyx-first** in practice (cheaper, SMS already there) though `PHONE_PROVIDER` defaults `"twilio"`. LLM fallback chain `_ask_ai()` (phone.py:524-537): **DeepSeek `deepseek-chat` → SambaNova `Meta-Llama-3.3-70B-Instruct` → local Qwen 2.5 7B** (`http://localhost:8002`). TTS: **AWS Polly `Polly.Joanna`** rendered via TeXML `<Say>` (so Polly is billed inside the Telnyx/Twilio leg, **not** a separate AWS bill). STT: Telnyx-hosted `deepgram/nova-3`.
- **Vapi demo line (separate)** — `src/api/routes/vapi_webhook.py`, `POST /api/vapi/webhook` handles `assistant-request` / `tool-calls` / `end-of-call-report`. Uses **Vapi-native telephony + Deepgram nova-3 + GPT-4.1 + Vapi "Elliot" TTS**. No credits table; bills via `voice_ledger`.
- **Pipecat streaming path** (gated `MEDIA_STREAMS_ENABLED=0`): NVIDIA Nemotron STT/TTS (NVCF, EN/FR) → Kokoro/Moonshine local fallback.
- **SMS ordering** — `src/api/routes/sms.py` re-exports the real handler at `services/phone_agent/sms_order.py` (exists, 20KB, `POST /sms/inbound`); falls back to a `sms-order-stub` only if the sidecar isn't on `sys.path`. LLM chain `["deepseek","sambanova"]`.
- **Order flow:** voice → `submit_order` tool → resolve merchant POS (`pos_connections`, decrypt token) → `create_pos_order` (direct POS API; Square order created **OPEN/unpaid**, pay-at-pickup or pay-now Stripe link) → log. Tables: `phone_call_logs`, `credit_ledger` (turn-based), `phone_orders` (Vapi/pay-on-phone path), `voice_ledger`.
- **Voice billing math:**
  - Turn-based = **credits**: `PHONE_CALL_PER_MIN = 50 credits/min` ($0.05 retail at 1¢/10 credits), rounded up to 30s, min 1 min; pre-call gate refuses if balance < 50 (`src/credits/costs.py:41,119-131`). Codebase's own stated underlying cost ≈ **$0.015/min** (Twilio voice $0.0085 + media-streams $0.004 + SambaNova ~$0.002 + compute) → ~3.3× target margin.
  - Vapi path = **voice_ledger**: `MERIDIAN_VOICE_INCLUDED_MIN=3` min included, `MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN=45` ($0.45/min over the block); overage computed at end-of-call as `(ceil(dur_min)-3)*45¢` and posted as a `duration_overage` credit; Vapi's reported all-in `cost` is posted as a `vapi_call` debit (`vapi_webhook.py:326-357`). Idempotent on `(source, ref)`. Per-merchant net P&L = SUM(credit)−SUM(debit) (`src/services/voice_ledger.py`, `migrations/029_voice_ledger.sql`).
  - SMS = credits: inbound 20cr/~$0.0085 cost; outbound 30cr/~$0.0089 cost.

### 1D. POS integrations + connect/digest/propagate

- **Entry points:** OAuth — `src/api/routes/oauth.py` (Square), `clover_oauth.py` (Clover). Manual/Toast — `src/api/routes/pos_connections.py` (`/api/pos/connect`, `/test-connection`, `/sync/{org}/{system}`, `/upload-csv`, `/disconnect`). Webhooks — `src/api/routes/webhooks.py` (`/api/webhooks/{square,clover,toast}`). Sync workers — `src/workers/backfill.py`, `incremental_sync.py`; `src/services/pos_scheduler.py` (cron, 15-min).
- **External APIs:** Square Connect (`Square-Version 2025-04-16`; orders/payments/refunds/catalog/inventory/team), rate-limited 8 req/s (batch 4). Clover (`/v3/merchants/{mId}/…`, region-hosted, 90-day windowing, 12 req/s; v2 expiring-token refresh inline). Toast (`authentication.toasttab.com` + `ws-api.toasttab.com`, client_credentials, **no rate limiter**).
- **DB tables:** `pos_connections`, `organizations`, `businesses`, `locations`, `product_categories`, `products`, `transactions`, `transaction_items`, `inventory_snapshots`, `notifications`, `schedule_staff`, `pos_waitlist`, `webhook_registrations`, `webhook_deliveries` (read-only/never written). Downstream: `daily_revenue` view; Convex mirror (`src/sync/customer_app.py` → `industrious-rabbit-343.convex.site`).
- **Flow:** CONNECT (HMAC-signed OAuth state, encrypted tokens) → DIGEST (18-month backfill in monthly/weekly chunks, then 15-min incremental, plus real-time webhooks) → PROPAGATE (`_write_sync_result` upserts products→transactions→items FK-safe; deterministic uuid5 PKs for Square/Clover; then `MeridianPipeline` AI analysis + dashboard cache invalidation + `send_pos_connected` email).
- **Gating:** Clover `POS_CLOVER_ENABLED` (config.py:96) is **defined but never read** — the only real production gate is the OAuth 503 when `CLOVER_APP_ID/SECRET` are absent; "coming soon" is enforced by the frontend registry, not the server. Manual `/api/pos/connect` with `pos_system=clover` is NOT gated.

### 1E. Camera / vision / live streaming

- **Entry points:** `src/api/routes/vision.py` (`/api/vision/*` — register/list/patch/delete cameras, `heartbeat`, `cameras/{id}/live` WHEP provisioning, `cameras/{id}/live-state` edge poll, `ingest/traffic`, `ingest/visits`, `traffic/{org}`, `agents/{org}`). Edge: `edge/edge_agent.py`, `edge/live_publisher.py`, `edge/depth_processor.py` + `edge/docker-compose.yml`.
- **External services:** **Cloudflare Stream** (`src/services/cloudflare_stream.py` — create/get/delete Live Inputs; `recording.mode="off"`; returns WHIP ingest + WHEP playback URLs) — **relay only, on-demand**. All ML runs **on the edge device (Jetson)**: YOLO11n detection, ByteTrack tracking, DeepFace demographics (gated), Depth Anything V2 (gated), CompreFace VIP (sidecar). `requirements-ml.txt` confirms ultralytics/torch are **commented out on the server** (Railway OOM) → **zero server/cloud GPU cost**.
- **DB tables:** `vision_cameras` (+`features` JSONB from migration 030; live_input/whip/whep/requested_at from 031), `vision_traffic` (15-min buckets), `vision_visits`, `vision_visitors` (hashed). Privacy defaults: detection+zones on; demographics/vip/depth/**live_view off**.
- **Flow:** edge runs detection locally, pushes 15-min aggregates to `ingest/traffic`. Live view is on-demand: browser POSTs `/live` → CF Live Input created/reused → edge polls `live-state`, ffmpeg WHIP-publishes only while a viewer ping is fresh (TTL 30s) → browser plays WHEP. **Pay Cloudflare only while someone is watching.**

### 1F. Dashboard / portals / onboarding

- Three portals: **merchant** (`src/api/routes/portal.py`, token-in-URL auth), **Canada rep** (`canada.py`, Supabase JWT + admin allowlist, hard-coded `CANADA_ORG_ID`), **US rep** (`us.py`). Dashboard `src/api/routes/dashboard.py` (router-level `require_org_access` JWT). Onboarding `src/api/routes/onboarding.py` (`provision-customer` creates Supabase user, `businesses` row, Square invoice, credentials email, Celery analysis). Admin `admin.py` (`X-Admin-Key`). Frontend: ~14 Canada + ~14 US rep pages, merchant onboarding wizards, Stripe-Connect step, CPA handoff (`frontend/src/pages/...`).
- **Auth:** `_verify_supabase_token` → `{SUPABASE_URL}/auth/v1/user`; `require_service_auth` accepts X-Admin-Key / service token / JWT.
- **DB tables:** `businesses`, `organizations`, `sales_reps`, `deals`/`us_leads`, `data_sales`, `sla_signatures`, `commissions`, `payouts`, `daily_revenue`/`weekly_revenue`, `products`, `insights`, `notifications`, `forecasts`, `transactions`.

### 1G. Email

- **Two paths, deliberately separate.** App transactional: `src/email/send.py` + `postal_client.py` → **Postal (self-hosted) primary, Resend fallback** (credentials + update-brief go Resend-first). 15+ templates; inbound delivery webhook `POST /webhooks/postal` updates `email_send_log`. Login/recovery: **Supabase Auth SMTP** (built-in, dev-only/rate-limited) — the app deliberately bypasses it by minting temp passwords and emailing credentials via Postal/Resend.
- **DB table:** `email_send_log`.

### 1H. SEO / brand subsystem

- **Standalone Node** in `seo-engine/` (not imported by Python; cron/loop). `content-drafter.mjs` (LLM drafts, never auto-publishes), `daily-report.mjs` (GSC + Telegram/Resend), `reddit-monitor.mjs` (read-only mention monitor). Plus ~19 static programmatic SEO pages in `frontend/src/pages/seo/`. File-based state only, no DB.

---

## 2. Per-feature COGS

**Cost bearer key:** *Platform* = Meridian pays; *Merchant* = passed through (credits/overage/fee); *Customer* = diner.

| Feature | External service | Unit cost (approx) | Est. cost per order/call/min | Who bears it | Margin note |
|---|---|---|---|---|---|
| Customer payment | **Stripe** (destination charge) | 2.9% + $0.30 | $1.17 on a $30 order | **Platform** (deducted from platform balance on destination charges) | Covered by $2.50 flat fee **only up to ~$76**; above that the flat fee loses money (see §3) |
| Customer payment | Stripe **Connect** (Express acct) | $0 create; payouts free (daily, CAD) | ~$0 | Platform | Active only when `UNIFIED_PAYMENTS_ENABLED=1` |
| SaaS billing | **Square** invoices/subs | 2.9% + $0.30 (Square online) | ~$7.55 on a $250/mo plan | Platform (or merchant card) | One-time; tiny vs subscription |
| Phone call (turn-based) | **Telnyx/Twilio** voice + Polly TTS (in-leg) | Telnyx ~$0.007–0.01/min; Twilio voice $0.0085 + media-stream $0.004 | ~$0.015/min (repo's own figure) | Merchant (50 credits/min ≈ $0.05) | ~3.3× margin per `costs.py` |
| Phone call (turn-based) | **LLM** DeepSeek/SambaNova/Qwen | DeepSeek ~$0.27/Mtok in, ~$1.10 out; SambaNova ~$0.60/Mtok; Qwen local = $0 | ~$0.002/min | Merchant (in the 50cr) | Cheap; local Qwen is the free floor |
| Phone STT | Telnyx-hosted **Deepgram nova-3** | ~$0.0043/min (Deepgram) | ~$0.004/min | Platform/merchant (in telephony) | Bundled in telephony leg |
| Phone call (Vapi line) | **Vapi** all-in (platform+STT+LLM+TTS) | ~$0.10–0.15/min typical | ~$0.40–0.60 on a 4-min call | Platform → reconciled via `voice_ledger` debit | Funded by $2.50 fee + $0.45/min overage |
| Voice overage | (revenue, not cost) | +$0.45/min over 3 min | +$0.45 on a 4-min call | Merchant pays Platform | Pure margin; offsets Vapi cost on long calls |
| SMS (receipt + pay link) | **Telnyx** SMS | ~$0.004/segment (Telnyx) | ~$0.008–0.012 per order (2–3 msgs) | Platform (receipts) / Merchant (credits 20–30cr on AI SMS) | Negligible per order |
| POS sync | **Square/Clover/Toast** APIs | $0 (free read APIs) | ~$0 | Platform | Only compute/egress |
| Camera analytics | **Edge Jetson** (YOLO/DeepFace/Depth) | $0 cloud (runs on merchant HW) | $0 | Merchant (owns device) | No cloud GPU bill at all |
| Camera live view | **Cloudflare Stream** | ~$1/1000 min stored (recording off) + ~$0.05/GB *delivered* | ~$0.05–0.15 per 10-min view session (~1–3 GB) | Platform | On-demand only (zero idle) — cost scales with watch time |
| Cold storage | **Cloudflare R2 / S3** | ~$0.015/GB-mo | small | Platform | `src/workers/cold_storage.py` |
| Database | **Supabase** | Plan (~$25/mo Pro + usage) | flat | Platform | Shared across all tenants |
| Compute | **Railway** | ~$20–100+/mo (services + workers) | flat | Platform | `--workers 4`; scheduler dedup needed |
| App email | **Postal (self-host) / Resend** | Postal ~$0 marginal; Resend ~$0.001/email after free tier | ~$0–0.001/email | Platform | Cheap |
| Auth email | **Supabase SMTP** | $0 (rate-limited 2/hr) | $0 | Platform | Deliberately minimized |
| Analytics LLM (insights) | DeepSeek/SambaNova/Groq/Cerebras/OpenAI via LiteLLM | per-token, tiered | ~$0.01–0.10 per insight batch | Platform | 3-tier router; confidence-escalates 1 step |
| Content gen (credits) | fal.ai image + LLM | $0.005–0.10 per asset | per `costs.py` | Merchant (75–250 credits) | Margins built into pack pricing |
| Error/analytics | Sentry + PostHog | plan/free tier | flat | Platform | `posthog` disabled w/o key |

### Vapi note
Vapi's reported `cost` is debited verbatim to `voice_ledger`, so the platform's real voice COGS is *measured, not estimated* per call. The system is explicitly built so per-order Stripe service-fee **revenue funds per-merchant voice usage** (auto-reload concept), with Vapi's card-on-file covering the global float.

---

## 3. Does the $2.50 flat fee cover costs? — sample $30 phone order

Assumptions: `UNIFIED_PAYMENTS_ENABLED=1`, Vapi line, ~4-minute call, two receipt SMS.

| Line | Amount |
|---|---|
| Diner pays (order total) | **$30.00** |
| Meridian service fee retained (`application_fee_amount`, flat) | **+$2.50** |
| Stripe processing (2.9% + $0.30, platform-borne on destination charge) | **−$1.17** |
| Vapi call cost (≈4 min @ ~$0.13/min, debited to ledger) | **−$0.52** |
| Voice overage revenue (4 min − 3 included = 1 min × $0.45) | **+$0.45** |
| Telnyx receipt + pay-link SMS (~2–3 segments) | **−$0.01** |
| **Net to Meridian on this order** | **≈ +$1.25** |

**Verdict:** Yes — on a typical restaurant ticket ($20–40) the flat $2.50 fee comfortably covers Stripe + Vapi + SMS, netting ~$1–1.5, and the $0.45/min overage protects margin on long calls.

**But two structural warnings (because the 1.9% is OFF):**
1. **Large tickets go underwater.** Platform net on payment = `$2.50 − (0.029×amount + $0.30)`. Break-even is **amount ≈ $75.86**. A $100 order: $2.50 − $3.20 = **−$0.70 on Stripe fees alone**, before voice. With `PLATFORM_FEE_BPS=0` there is no protection on big orders. Re-enabling even a small bps (e.g. 100–190 bps) would fix the scaling. *(This is exactly the "1.9% removed" risk in the brief — confirmed it's set to zero in code.)*
2. **The fee path is off by default.** With `UNIFIED_PAYMENTS_ENABLED=0` (the default) Meridian takes **$0** per order — payments fall back to native POS links. Until that flag is flipped per-merchant/globally, the entire service-fee economy is inert. Also `MERIDIAN_SERVICE_FEE_CENTS` defaults to `0` in `stripe_connect.py` if unset — must be explicitly `250` in env or no ledger credit posts.

---

## 4. Not-built-yet / gated / stubbed — gap list

Effort: **S** ≈ <1 day, **M** ≈ 1–3 days, **L** ≈ 1–2 weeks.

### P1 — security / money-correctness

| # | Gap | Current state | What's needed | Effort |
|---|---|---|---|---|
| 1 | **Toast webhook HMAC verification** | `webhooks.py:355-366` — fails *closed* if `TOAST_WEBHOOK_SECRET` unset, but if set, **any well-formed JSON is processed unsigned**. No verify helper in `src/toast/`. | Implement Toast signature verification per Toast webhook docs; add `src/toast/verify.py`. | S–M |
| 2 | **Rep commission never fires** | `calculate_commission` RPC + `CommissionService` + `init_commission_hook()` all exist and the hook is initialized at startup (`app.py:115-118`), but **`on_payment_received()` has no call site** — `square/webhook_handlers.py:204-205` explicitly says it must NOT be called from POS webhooks, and nothing on the billing side calls it. Commission rows are never created. *(Note: memory said "no callers" — accurate at the function level; the service is wired but never invoked.)* | Call `on_payment_received` from the billing/subscription payment-confirmation path. Decide units (fraction vs percent) — still unresolved. | M |
| 3 | **Stripe fee scaling (1.9% off)** | `MERIDIAN_PLATFORM_FEE_BPS=0`; flat $2.50 loses money above ~$76 order. | Set a non-zero bps, or cap/tier the fee. Config-only + math review. | S |
| 4 | **Unified payments gated off** | `UNIFIED_PAYMENTS_ENABLED=0` default → no service fee taken. | Flip per-merchant once Connect onboarding verified; confirm `MERIDIAN_SERVICE_FEE_CENTS=250` in env. | S |
| 5 | **Vapi webhook auth open by default** | `VAPI_SERVER_SECRET` unset → `x-vapi-secret` check skipped; the order-placing webhook is internet-open (`vapi_webhook.py:48,255`). | Set the secret in env + on the Vapi assistant. | S |
| 6 | **`mark-onboarded` has no auth** | `onboarding.py:512` — open POST; any caller can flag any org onboarded. | Add `require_service_auth`. | S |
| 7 | **Square webhook dedupe is in-process only** | `_seen_events` dict, lost on restart / not shared across 4 workers (`square/webhook_handlers.py:62-66`). | Add `webhook_events` table (insert-or-conflict on event_id) + migration. | M |

### P2 — reliability / features incomplete

| # | Gap | Current state | What's needed | Effort |
|---|---|---|---|---|
| 8 | **Webhook retry / dead-letter queue** | `RetryConfig.dead_letter_after=5` defined but **never read**. `src/webhooks/delivery.py` sets `status="dead_letter"` in-memory but is **never imported/called**; `webhook_deliveries` table is read by `registry.py` but never written. Dead events silently dropped. | Wire `deliver_webhook` into outbound dispatch; persist deliveries + DLQ + a drain worker. | M–L |
| 9 | **Clover POS gated off (correctly) but inconsistently** | `POS_CLOVER_ENABLED` defined, never read; only OAuth 503 (missing app creds) gates it; manual `/api/pos/connect` for Clover is ungated. | Enforce `cl_config.enabled` in connect/test/webhook routes, or remove the dead flag. | S |
| 10 | **Cloudflare live-PLAYBACK activation** | Ingest (WHIP) works; **playback returns empty** — browser opens WHEP immediately but edge polls `live-state` every 5s, so ffmpeg isn't publishing yet → no frames; no retry/renegotiate; `src/streaming/__init__.py` is empty. | Add "wait for publisher" + WHEP reconnect/renegotiate on first-frame; shorten poll or push-signal the edge. | M |
| 11 | **SMS-order intake** | Real handler exists (`services/phone_agent/sms_order.py`), but `routes/sms.py` only mounts it if the sidecar is on `sys.path`; otherwise a `sms-order-stub` 404s. Deploy-dependent. | Confirm sidecar packaging in the deployed image; add health check. | S |
| 12 | **AI accuracy-signal producer** | `swarm_trainer.py:222,350` — pattern store + DSPy examples accept the 0.5 cold-start accuracy because **no real accuracy-signal producer exists (TODO)**. Learning loop trains on un-scored data. | Build a producer that scores agent insights against realized outcomes. | L |
| 13 | **Toast rate limiter** | None — each call makes a fresh `httpx.AsyncClient`; high-volume backfill risks 429. | Add a token-bucket like Square/Clover. | S |
| 14 | **Incremental-sync conflict-key bug** | `incremental_sync.py:50` uses `on_conflict="transaction_id,external_id"` but `transaction_items` has no `external_id`; all other callers use `id,transaction_at`. First conflicting write → Postgres 42P10. | Align the on-conflict key. | S |
| 15 | **LLM budget enforcement** | `llm_layer.check_llm_budget()` returns `True` unconditionally — no enforcement. | Implement per-org token/$ budget at call time. | M |
| 16 | **POS poll-fallback for stuck payments** | `phone.py:1401` — no poll of Square `/v2/payments?order_id=` for orders stuck `awaiting_payment` if a webhook is missed. | Add a reconciliation poller. | M |

### P3 — vision / compliance / hygiene

| # | Gap | Current state | What's needed | Effort |
|---|---|---|---|---|
| 17 | **Vision compliance enforcement + consent copy** | `register_camera` and `request_live_view` do **zero** consent checks; no setup-wizard route; `camera_disclosure` doc type exists in `compliance_documents` but **no disclosure copy seeded**; `compliance_mode` is a label only. | Gate camera enable on accepted `camera_disclosure`; seed consent copy; build the signage/consent wizard step. | M |
| 18 | **Vision base migration missing** | `vision_cameras/visits/visitors/traffic` CREATE TABLE exists only in `docs/architecture-decisions.md`; migrations 030/031 `ALTER` an assumed table. The referenced `20260516_vision_cameras` migration is absent. | Add the base migration to the repo for reproducible deploys. | S |
| 19 | **VIP face-matching stubbed** | `edge_agent.py:186-188` — `_check_vip()` exists but never called; `vip_sightings` always flushes `[]`. | Make the per-frame loop async and wire `_check_vip` in (privacy review first). | M |
| 20 | **Orphaned server-side camera pipeline** | `src/camera/*` (full pipeline) is **never imported by any route**; edge re-implements its own `CameraProcessor`. Writes bypass API auth. | Delete or repurpose `src/camera/`; one source of truth. | S |
| 21 | **Edge `MERIDIAN_DEVICE_TOKEN` missing from compose** | `edge/docker-compose.yml` omits the device token required by `require_device_token` routes → fresh device 401s on ingest/live-state. | Add the env var to compose + docs. | S |
| 22 | **Two SaaS price sheets** | Stripe ($299/$599/$1199) vs Square ($250/$500/$1000) for the same tiers. | Reconcile to one canonical price table. | S |
| 23 | **`billing_service.py` hardcoded Square App ID fallback** | `os.getenv("SQUARE_APP_ID", "sq0idp-…")` (line 35). | Make env-only; remove the literal. | S |
| 24 | **Short-link has no expiry check** | `pay_redirect.py` fetches `status` but redirects regardless — expired/cancelled sessions still redirect. | Check status before 303. | S |
| 25 | **Subscription cancel doesn't revoke access** | `stripe_checkout.py` `customer.subscription.deleted` only logs / flips `payment_status`. | Revoke feature access on cancel. | S |
| 26 | **SEO engine cron not scheduled** | `seo-engine/*.mjs` ready but only "suggested" cron times; no crontab in repo. | Add cron entries on the host. | S |
| 27 | **Square catalog event over-fetches** | `catalog.version.updated` discards the `updated_at` and refetches the full catalog every time. | Incremental catalog fetch. | M |

---

## 5. Key file index (for the diagram)

- Money: `src/api/routes/stripe_connect.py`, `services/phone_agent/payment_links.py`, `src/api/routes/pay_redirect.py`, `src/billing/billing_service.py`, `src/services/voice_ledger.py`, `migrations/029_voice_ledger.sql`, `src/credits/costs.py`
- Voice: `src/api/routes/phone.py`, `vapi_webhook.py`, `sms.py`, `services/phone_agent/{sms_order,pay_on_phone,order_processor}.py`, `src/ai/routing/tiered_router.py`
- POS: `src/{square,clover,toast}/*`, `src/api/routes/{oauth,clover_oauth,pos_connections,webhooks}.py`, `src/workers/{backfill,incremental_sync}.py`, `src/services/pos_scheduler.py`, `src/webhooks/{delivery,registry}.py`
- Vision: `src/api/routes/vision.py`, `src/services/cloudflare_stream.py`, `edge/{edge_agent,live_publisher,depth_processor}.py`, `migrations/030_camera_feature_toggles.sql`, `031_camera_live_view.sql`
- Portals/email/SEO: `src/api/routes/{portal,canada,us,dashboard,onboarding,admin,billing,credits,email}.py`, `src/email/*`, `seo-engine/*.mjs`
- Config: `src/config.py` (all feature flags + fee env), `.env.example`, `requirements*.txt`
