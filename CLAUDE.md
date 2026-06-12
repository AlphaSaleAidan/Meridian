# Meridian Intelligence Platform

> AI-powered POS analytics for independent businesses (restaurants, smoke shops, cafes, retail, auto shops, dispensaries).
> FastAPI + React/Vite + Supabase + Square/Clover/Toast + Celery/Redis + 48-agent AI swarm (registry: agents/registry.yaml).

> **Security posture (post 2026-05-31 audit merges):** All four SEV-0 customer-readiness gaps and the canada.py JWT-forwarding work are now on `main`. See [`docs/AUTH_HARDENING_PLAN.md`](docs/AUTH_HARDENING_PLAN.md) for the original findings and the resolution commits (`dbc333f`, `c9cbb07`).

## Deployment Reality (read this before deploying ANYTHING)

- **Backend (`api.meridian.tips`) = Railway**, auto-deploys from `main` on merge. Don't run `railway up`; merge → watch → verify `/health` (route check: 403 = exists+gated, 404 = missing).
- **Frontend (`meridian.tips`) = Contabo nginx serving static `/root/Meridian/frontend/dist`** — NOT Vercel, NOT Railway, NOT auto-deployed. Built MANUALLY, only from the canonical tag lineage (`canada-portal-canonical` until PR #90 merges). Builds MUST have `frontend/.env.local` present (gitignored) or the site silently ships demo-mode with broken Supabase auth. Full procedure: `docs/30-operations/frontend-deploy.md`.
- **Two clobber incidents (2026-06-08, 2026-06-12)** came from deploying frontend builds of `main`/WIP trees. Before any dist swap: `cp -a` backup; after: verify the served bundle hash via `curl` + nginx access.log (trust logs over mtimes).

## Runtime (Contabo box 209.126.80.45)

| Service | Location | Runtime | Port |
|---------|----------|---------|------|
| API (local instance) | `src/api/app.py` | pm2 `meridian-api` (4 workers, 512MB) — public API is Railway, see above | :8000 |
| Frontend | `frontend/dist` | nginx static (manual canonical-tag deploys) | :443 |
| Workers | `src/workers/` | pm2 `celery-worker` + `celery-beat` | — |
| Scraper | `scripts/scraper-daemon.py` | pm2 `scraper` (paused — Chrome OOM) | — |
| DeerFlow | `services/deerflow/` | pm2 `deerflow` (`app.gateway.app:app`) | :8001 |
| Qwen Server | `data/models/` | pm2 `qwen-server` (12GB max) | :8002 |
| Phone Agent | `services/phone_agent/` + `src/api/routes/phone.py` | Telnyx TeXML, turn-based (streaming/Pipecat path is DEAD — do not revive) | webhook |
| Garry | `/root/garry` | pm2 `garry` (self-healing agent) | — |
| DB | Supabase (kbuzufjxwflrutowwnfl) | hosted (24 tables, 4 mat views) | — |
| Cache | Redis | systemd | :6379 |
| Local LLM | `data/models/` Llama 3.1 8B, Qwen 2.5 7B | loaded on-demand | — |

Server: 209.126.80.45 (AMD EPYC 12c, 48GB RAM, 484GB disk)

## Key IDs

- Canada org: `168b6df2-e9af-4b00-8fec-51e51149ff19`
- Square location: `LY1VJBWJ2J13J`
- Admin phone: +19495067494
- Supabase project: kbuzufjxwflrutowwnfl

## LLM Routing Chain

`llm_layer.py` routes through LiteLLM Router **tier groups** (`meridian-t1/t2/t3`) — per-agent tiers come from `agents/registry.yaml` via `src/ai/routing/registry_loader.py`; latency-based routing picks the fastest provider inside the group. Fallback chain: DeepSeek V3 → SambaNova (free, 405B) → Groq (free, 70B) → Local Llama → Cerebras (free, 70B) → OpenAI. Every call is teed to `swarm_traces` (`src/ai/trace_recorder.py`).

Env vars: `DEEPSEEK_API_KEY`, `SAMBANOVA_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `OPENAI_API_KEY`. When `OPENAI_BASE_URL` is set, calls route via the local LiteLLM gateway on :4000 (kimi-k2.6-gateway branch).

## Backend Map (`src/`)

**API Routes** (`src/api/routes/`, 36 modules): dashboard, onboarding (656L), pos_connections (717L), website (715L), billing (478L), us (465L), vision (397L), webhooks (397L), phone (407L), stripe_checkout (366L), canada (371L), spaces (308L), schedule (403L), oauth (275L), predictive (204L), intelligence (227L), email (190L), inference (93L), careers (143L), admin (56L), compliance, phone_dashboard (204L), inventory_docs (224L), and more

**AI Engine** (`src/ai/`): engine.py (main orchestrator), llm_layer.py (LiteLLM Router with auto-failover + caching across DeepSeek/SambaNova/Groq/Cerebras/OpenAI), swarm_trainer.py, agent_memory.py, reasoning/karpathy_loop.py, cross_reference_orchestrator.py, dspy_optimizer.py (lazy-loaded)

**AI Agents (48 registered — agents/registry.yaml)** (`src/ai/agents/`): All inherit base.py — action_prioritizer, basket_analysis, customer_ltv, customer_recognizer, day_of_week, demographic_profiler, discount_analyzer, dwell_time, employee_perf, feature_engineer, foot_traffic, forecaster, and 29 more. Subdirs: alerts/, canada/, economics/, financial/, freemocap/, industry_templates/, reid/, scheduling/, security/

**Predictive** (`src/ai/predictive/`): churn_warning, demand_forecast, dynamic_pricing, goal_tracker, root_cause, scenario_engine

**Generators** (`src/ai/generators/`): insights, forecasts, reports, economic_insights, revenue_insights, anomaly_insights, money_left_insights, pattern_insights, product_insights

**Analyzers** (`src/ai/analyzers/`): patterns, products, revenue, money_left

**DB** (`src/db/`): supabase_rest.py (main client), cache.py (Redis TTL), queries.py, repos/ (sync, query, persist)

**POS**: square/ (client, mappers, oauth, sync_engine, webhooks), clover/ (same), toast/ (same), services/pos_connectors/ (universal framework, registry 1206L)

**Workers** (`src/workers/`): tasks.py (sync, analysis, swarm training, burn rate, vector ingestion, batch inference), celery_app.py (beat schedules), backfill.py, incremental_sync.py, token_refresh.py, cold_storage.py

**Inference** (`src/inference/`): local_llm.py (llama-cpp CPU), router.py (batch→local, realtime→OpenAI), embeddings.py (sentence-transformers + SQLite vectors)

**Other**: email/ (Postal+Resend, 14 templates), sms/client.py (Telnyx+Twilio), billing/billing_service.py, auth/ (Supabase JWT, RBAC), analytics/burn_rate.py, cline/ (self-healing agent)

## Authorization (`src/api/auth.py`)

Pick the right dep per endpoint — getting this wrong is what produced the 2026-05-29 audit:

| Dep | Use for | Mechanism |
|-----|---------|-----------|
| `require_admin` | Internal admin tools that no end user touches | `X-Admin-Key` header against `MERIDIAN_ADMIN_KEY` env var |
| `require_admin_jwt` | Admin operations performed by a known Aidan/Enoch user | JWT verify → email in `ADMIN_EMAILS` allowlist |
| `require_jwt` | Any authenticated request | Supabase JWT verification only |
| `require_org_access` | Any per-org data endpoint (dashboard, analytics, predictive, pos_connections, etc.) | `require_jwt` + membership check (`businesses.owner_user_id` OR `business_users` active OR admin allowlist) |
| `require_service_auth` | Service-to-service calls | Either admin key OR valid JWT |

Emergency rollback knob: `TENANCY_ENFORCEMENT_DISABLED=true` flips `require_org_access` into warn-only without redeploying.

`canada.py` and `us.py` admin endpoints now **forward the caller's JWT** to Supabase (`Bearer {user_token}`) so RLS enforces row-level access at the DB layer; the service-role key is only used for `/auth/v1/admin/users` calls (where Supabase rejects non-service tokens) and as a fall-through when the user token is somehow missing.

Customer-facing flows:
- Customer accounts are created server-side. Since PR #91, provisioning returns a readable temp password (`Mer-XXXXXXXX`) to the rep and forces a first-login reset via the `must_reset_password` metadata flag — deliberately NOT relying on Supabase recovery email (its SMTP path has burned us; see `docs/runbooks/`). The existing-user reset path is restricted to Canada customer-owner accounts (account-takeover guard, `canada.py`).
- SLA signatures captured during onboarding persist to `sla_signatures` with IP + UA audit trail; agreement text is the legally binding record.

Rate-limited routes: `/api/canada/rep-signup` (5/hr per IP) via `HourRateLimiter`.

## Services (`services/`)

| Service | Stack | Purpose |
|---------|-------|---------|
| phone_agent | Telnyx TeXML (turn-based `<Record>` capture) + Telnyx STT + Kokoro/CosyVoice2 TTS | AI phone order agent — Kokoro default, CosyVoice2 when merchant has a voice clone. The Pipecat/Twilio streaming path drifted dead (pipecat 0.0.45→0.0.108) and was never functional — turn-based is the launch path |
| deerflow | FastAPI + frontend | Visual knowledge graph builder |
| evolver | Node.js | ML model training/optimization (GEP) |
| labellerr_cv | Python notebooks | Computer vision labeling/training |
| postal | Docker | Self-hosted email delivery |
| training_video_pipeline | Python | Video generation/processing |

### Phone Agent Pipeline (live, turn-based)
Telnyx TeXML webhook → `<Record>` turn capture → Telnyx STT → LLM brain (DeepSeek 8s ceiling → SambaNova → local Qwen failover, `src/api/routes/phone.py`) → TTS → TeXML response. Live-call-tested (PRs #82/#83/#85). TeXML app "Meridian Phone Calls" = `TELNYX_VOICE_CONNECTION_ID`.
TTS factory: `build_tts(merchant_config)` returns `CosyVoiceTTS` when the merchant has a `ref_audio` clone, otherwise `KokoroTTS` (Kokoro-82M, Apache-2.0, ~300 MB, realtime on CPU). Voice profiles: US (female, north american), Canada (female, canadian). Both implementations live in `services/phone_agent/tts_service.py`.

## Frontend Map (`frontend/src/`)

**Stack**: React 18 + TypeScript + Vite + Tailwind CSS + Recharts + Three.js/R3F + Framer Motion + GSAP + Lenis + Supabase JS + Sentry

**Pages** (30+): LandingPage, OverviewPage, InsightsPage (2hr cooldown), AnomaliesPage, ForecastsPage, RevenuePage, MarginsPage, ProductsPage, InventoryPage, CustomersPage, PeakHoursPage, SchedulePage, MenuEngineeringPage, ActionsPage, PhoneOrdersPage, NotificationsPage, AgentDashboardPage, ITDashboardPage, CameraAnalyticsDemoPage, CameraIntelligencePage, CareersPage, SettingsPage, AdminPage, MyWebsitePage, MerchantSitePage. Canada portal: pages/canada/portal/ (15 pages). Customer: OnboardingWizard, CreateCustomerPage. Sales: pages/sales/ (rep tools). SEO tools: FoodCostCalculatorPage, PrimeCostCalculatorPage, MenuPricingCalculatorPage. SEO content: GuidesIndexPage, GuidePage (9 guides), FAQHubPage, BestAnalyticsSoftwarePage, CityIndustryPage (280+ programmatic pages)

**Components**: GarryWidget.tsx (AI chat), POSSystemPicker.tsx (80 POS systems), landing/ (MeshGradient, BentoGrid, TiltCard, ScrollReveal, MagneticButton, CountUp, TextReveal, GrainOverlay), vision/, compliance/, schedule/, demo/, space/, website/, ui/ (shadcn)

**Hooks**: useOrg.ts (CRITICAL: isDemoPath — demo only on /demo and /canada/demo), useApi.ts, useInsightsCooldown.ts

**Lib**: demo-data.ts, demo-industries.ts, agent-data.ts (frontend agent registry; 41 backend agents), pos-systems.ts (4492L — 80+ POS systems), auth.tsx, supabase.ts

**Data**: seo-cities.ts (20 CA + 20 US cities × 7 industries), seo-guides.ts (9 guides), pos-systems.ts

## MCP Servers

Configured in `.claude/settings.json`:
- **Supabase**: `npx -y @supabase/mcp-server` — database operations
- **GitHub**: `npx -y @modelcontextprotocol/server-github` — repo management

## Common Tasks

- **Add API endpoint**: Create in `src/api/routes/`, import+include_router in `src/api/app.py`. **Pick an auth dep** (`require_admin` / `require_admin_jwt` / `require_jwt` / `require_org_access` / `require_service_auth`) per the Authorization table above — never ship an unauthenticated data endpoint.
- **Add Celery task**: Define in `src/workers/tasks.py`, add route+beat in `celery_app.py`
- **Add AI agent**: Inherit `src/ai/agents/base.py:BaseAgent`, register in `__init__.py`
- **Add email template**: Create in `src/email/templates/`, use base.py helpers
- **Restart**: `pm2 restart meridian-api celery-worker celery-beat --update-env`
- **Build check**: `cd frontend && npm run build`
- **Dev server**: `cd frontend && npx vite --port 3003 --host`

## Rules

- Never commit `.env` or credentials
- All Supabase tables need RLS
- Use `org_id` guards on all data endpoints — prefer the `require_org_access` dep over hand-rolled checks
- Never accept `admin_email` / role / org_id from a request body — derive from the JWT
- Demo data only on `/demo` and `/canada/demo` paths
- Money in cents (integer), display with CA$ for Canada
- Email: Postal primary, Resend fallback
- SMS: Telnyx primary, Twilio fallback
- Pre-push: `cd frontend && npm run build` must pass. Merging to `main` auto-deploys the BACKEND to Railway prod — never merge without Aidan's review. Frontend never auto-deploys (manual canonical-tag procedure only).
- Max 500 lines per file — split if larger
- Heavy ML packages (torch, prophet, dspy, mem0ai) are lazy-imported — don't add to top-level imports
- LLM calls go through `src/ai/llm_layer.py` — never call OpenAI/DeepSeek directly from route handlers
- Customer account setup: rep-shared temp password + forced first-login reset (PR #91 flow) — do NOT route account setup through Supabase recovery email

## Product Doctrine (decisions, not bugs)

- **US and Canada portals are intentionally different products.** Never unify their UI; demos must reflect the difference.
- **Rep commission system is intentionally unbuilt.** `calculate_commission` has no callers; the fraction-vs-percent rate units are unresolved BY DESIGN. Do not wire it or "fix" the units — a unique pay structure is still being designed.
- **POS beta (P0–P6 pipeline, PR #94) is gated on a real merchant connection test.** Everything so far is verified on synthetic payloads only; the first real Square/Clover/Toast merchant IS the test. See `docs/known_issues.md` §4.
- **Canonical Canada frontend = tag `canada-portal-canonical`** until PR #90 merges; main-built frontend deploys revert the portal (it happened twice).
- Open technical debt is tracked in `docs/known_issues.md` — keep it authoritative.
