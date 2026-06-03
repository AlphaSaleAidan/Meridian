# Meridian Intelligence Platform

> AI-powered POS analytics for independent businesses (restaurants, smoke shops, cafes, retail, auto shops, dispensaries).
> FastAPI + React/Vite + Supabase + Square/Clover/Toast + Celery/Redis + 41-agent AI swarm.

> **Security posture (post 2026-05-31 audit merges):** All four SEV-0 customer-readiness gaps and the canada.py JWT-forwarding work are now on `main`. See [`docs/AUTH_HARDENING_PLAN.md`](docs/AUTH_HARDENING_PLAN.md) for the original findings and the resolution commits (`dbc333f`, `c9cbb07`).

## Runtime

| Service | Location | Runtime | Port |
|---------|----------|---------|------|
| API | `src/api/app.py` | pm2 `meridian-api` (4 workers, 512MB) | :8000 |
| Frontend | `frontend/` | Vercel (meridian.tips) | — |
| Workers | `src/workers/` | pm2 `celery-worker` + `celery-beat` | — |
| Scraper | `scripts/scraper-daemon.py` | pm2 `scraper` | — |
| DeerFlow | `services/deerflow/` | pm2 `deerflow` | :8004 |
| Qwen Server | `data/models/` | pm2 `qwen-server` (12GB max) | :8002 |
| Phone Agent | `services/phone_agent/` | Fonoster + Pipecat | WS |
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

`llm_layer.py` routes (in-process, application LLM enhancements): DeepSeek V3 → SambaNova (free, 405B) → Groq (free, 70B) → Local Llama → Cerebras (free, 70B) → OpenAI (fallback).

Env vars: `DEEPSEEK_API_KEY`, `SAMBANOVA_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `OPENAI_API_KEY`

## Model Gateway (2026-06-04)

All NEW agentic work (Ruflo swarm, the fixer, ad-hoc Claude Code sessions) routes through a single LiteLLM proxy on **`127.0.0.1:4000`** (PM2: `litellm-gateway`). Four aliases the rest of the stack speaks:

| Alias | Backed by | Use for |
|-------|-----------|---------|
| `meridian-architect` | Kimi K2.6 via OpenRouter | Swarm queen / planning / critique / safety-critical reasoning |
| `meridian-fixer` | Kimi K2.6 via OpenRouter | Autonomous server fixer (`/opt/meridian-fixer/`, PM2 `meridian-fixer`) |
| `meridian-fast` | Groq / Cerebras / SambaNova / DeepSeek (round-robin) | High-volume mechanical worker subtasks |
| `meridian-local` | `qwen-server` on :8002 (llama-cpp Qwen2.5-7B) | Truly free fallback, no API keys |

**Fallback chain (router-level):** `architect` / `fixer` → `fast` → `local`. The gateway answers even with zero upstream keys.

**Files:**
- `litellm.config.yaml` — model + router config (canonical source for swapping providers)
- `.env.litellm` — secrets (0600, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `SAMBANOVA_API_KEY`, master key)
- `scripts/start-litellm.sh` — PM2 launcher
- Budget cap: `max_budget: $25/30d` on K2.6 (`litellm.config.yaml`); raise after first real workload sized.

**Swap to self-hosted K2.6 (when GPUs land):** edit only `meridian-architect` and `meridian-fixer` entries in `litellm.config.yaml` — change `model:` to `openai/Kimi-K2.6-AWQ` and `api_base: http://gpu-host:8000/v1`. Nothing downstream changes; the aliases stay the same.

**Cline IDE decommissioned same day** — Aidan's ad-hoc fix-it tool now is `/fix <description>` in Telegram (Garry relays to the K2.6 fixer; diff comes back for `/approve <task_id>` or `/reject`). The merchant-facing `src/cline/` Karpathy-reasoning health agent is unrelated and untouched.

**Grafana dashboard for per-model spend/latency**: deferred — see `docs/litellm-grafana-future.md` for the deployment sketch when traffic justifies it.

## Backend Map (`src/`)

**API Routes** (`src/api/routes/`, 36 modules): dashboard, onboarding (656L), pos_connections (717L), website (715L), billing (478L), us (465L), vision (397L), webhooks (397L), phone (407L), stripe_checkout (366L), canada (371L), spaces (308L), schedule (403L), oauth (275L), predictive (204L), intelligence (227L), email (190L), inference (93L), careers (143L), admin (56L), compliance, phone_dashboard (204L), inventory_docs (224L), and more

**AI Engine** (`src/ai/`): engine.py (main orchestrator), llm_layer.py (LiteLLM Router with auto-failover + caching across DeepSeek/SambaNova/Groq/Cerebras/OpenAI), swarm_trainer.py, agent_memory.py, reasoning/karpathy_loop.py, cross_reference_orchestrator.py, dspy_optimizer.py (lazy-loaded)

**41 AI Agents** (`src/ai/agents/`): All inherit base.py — action_prioritizer, basket_analysis, customer_ltv, customer_recognizer, day_of_week, demographic_profiler, discount_analyzer, dwell_time, employee_perf, feature_engineer, foot_traffic, forecaster, and 29 more. Subdirs: alerts/, canada/, economics/, financial/, freemocap/, industry_templates/, reid/, scheduling/, security/

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
- Customer accounts are created server-side (no plaintext password ever leaves the backend or hits the frontend) and the customer sets their own password via `supabase.auth.resetPasswordForEmail()` after onboarding.
- SLA signatures captured during onboarding persist to `sla_signatures` with IP + UA audit trail; agreement text is the legally binding record.

Rate-limited routes: `/api/canada/rep-signup` (5/hr per IP) via `HourRateLimiter`.

## Services (`services/`)

| Service | Stack | Purpose |
|---------|-------|---------|
| phone_agent | Pipecat + Kokoro/CosyVoice2 TTS + WhisperLiveKit STT + Ollama | AI phone order agent — Kokoro default, CosyVoice2 when merchant has a voice clone |
| deerflow | FastAPI + frontend | Visual knowledge graph builder |
| evolver | Node.js | ML model training/optimization (GEP) |
| labellerr_cv | Python notebooks | Computer vision labeling/training |
| postal | Docker | Self-hosted email delivery |
| training_video_pipeline | Python | Video generation/processing |

### Phone Agent Pipeline
Fonoster audio → WhisperLiveKit STT → Ollama LLM (llama3.3:70b) → TTS → Fonoster audio.
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
- Pre-push: `cd frontend && npm run build` must pass (Vercel auto-deploys main)
- Max 500 lines per file — split if larger
- Heavy ML packages (torch, prophet, dspy, mem0ai) are lazy-imported — don't add to top-level imports
- LLM calls go through `src/ai/llm_layer.py` — never call OpenAI/DeepSeek directly from route handlers
- Plaintext customer passwords never leave the backend — use `supabase.auth.resetPasswordForEmail()` for account setup
