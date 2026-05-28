# Meridian Intelligence Platform

> AI-powered POS analytics for independent businesses (restaurants, smoke shops, cafes, retail, auto shops, dispensaries).
> FastAPI + React/Vite + Supabase + Square/Clover/Toast + Celery/Redis + 39-Agent AI Swarm

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

`llm_layer.py` routes: DeepSeek V3 → SambaNova (free, 405B) → Groq (free, 70B) → Local Llama → Cerebras (free, 70B) → OpenAI (fallback).

Env vars: `DEEPSEEK_API_KEY`, `SAMBANOVA_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `OPENAI_API_KEY`

## Backend Map (`src/`)

**API Routes** (`src/api/routes/`, 37 modules): dashboard, onboarding (656L), pos_connections (717L), website (715L), billing (478L), us (465L), vision (397L), webhooks (397L), phone (407L), stripe_checkout (366L), canada (371L), spaces (308L), schedule (403L), oauth (275L), predictive (204L), intelligence (227L), email (190L), inference (93L), careers (143L), admin (56L), compliance, phone_dashboard (204L), inventory_docs (224L), and more

**AI Engine** (`src/ai/`): engine.py (main orchestrator), llm_layer.py (multi-provider routing), swarm_trainer.py, agent_memory.py, reasoning/karpathy_loop.py, cross_reference_orchestrator.py, dspy_optimizer.py (lazy-loaded)

**45 AI Agents** (`src/ai/agents/`): All inherit base.py — action_prioritizer, basket_analysis, customer_ltv, customer_recognizer, day_of_week, demographic_profiler, discount_analyzer, dwell_time, employee_perf, feature_engineer, foot_traffic, forecaster, and 33 more. Subdirs: alerts/, canada/, economics/, financial/, freemocap/, industry_templates/, reid/, scheduling/, security/

**Predictive** (`src/ai/predictive/`): churn_warning, demand_forecast, dynamic_pricing, goal_tracker, root_cause, scenario_engine

**Generators** (`src/ai/generators/`): insights, forecasts, reports, economic_insights, revenue_insights, anomaly_insights, money_left_insights, pattern_insights, product_insights

**Analyzers** (`src/ai/analyzers/`): patterns, products, revenue, money_left

**DB** (`src/db/`): supabase_rest.py (main client), cache.py (Redis TTL), queries.py, repos/ (sync, query, persist)

**POS**: square/ (client, mappers, oauth, sync_engine, webhooks), clover/ (same), toast/ (same), services/pos_connectors/ (universal framework, registry 1206L)

**Workers** (`src/workers/`): tasks.py (sync, analysis, swarm training, burn rate, vector ingestion, batch inference), celery_app.py (beat schedules), backfill.py, incremental_sync.py, token_refresh.py, cold_storage.py

**Inference** (`src/inference/`): local_llm.py (llama-cpp CPU), router.py (batch→local, realtime→OpenAI), embeddings.py (sentence-transformers + SQLite vectors)

**Other**: email/ (Postal+Resend, 14 templates), sms/client.py (Telnyx+Twilio), billing/billing_service.py, auth/ (Supabase JWT, RBAC), analytics/burn_rate.py, cline/ (self-healing agent)

## Services (`services/`)

| Service | Stack | Purpose |
|---------|-------|---------|
| phone_agent | Pipecat + OmniVoice TTS + WhisperLiveKit STT + Ollama | AI phone order agent (600+ languages, voice cloning) |
| deerflow | FastAPI + frontend | Visual knowledge graph builder |
| evolver | Node.js | ML model training/optimization (GEP) |
| labellerr_cv | Python notebooks | Computer vision labeling/training |
| postal | Docker | Self-hosted email delivery |
| training_video_pipeline | Python | Video generation/processing |

### Phone Agent Pipeline
Fonoster audio → WhisperLiveKit STT → Ollama LLM (llama3.3:70b) → OmniVoice TTS → Fonoster audio. Voice profiles: US (female, north american), Canada (female, canadian). Supports voice cloning via ref_audio. KokoroTTS legacy preserved for rollback.

## Frontend Map (`frontend/src/`)

**Stack**: React 18 + TypeScript + Vite + Tailwind CSS + Recharts + Three.js/R3F + Framer Motion + GSAP + Lenis + Supabase JS + Sentry

**Pages** (30+): LandingPage, OverviewPage, InsightsPage (2hr cooldown), AnomaliesPage, ForecastsPage, RevenuePage, MarginsPage, ProductsPage, InventoryPage, CustomersPage, PeakHoursPage, SchedulePage, MenuEngineeringPage, ActionsPage, PhoneOrdersPage, NotificationsPage, AgentDashboardPage, ITDashboardPage, CameraAnalyticsDemoPage, CameraIntelligencePage, CareersPage, SettingsPage, AdminPage, MyWebsitePage, MerchantSitePage. Canada portal: pages/canada/portal/ (15 pages). Customer: OnboardingWizard, CreateCustomerPage. Sales: pages/sales/ (rep tools). SEO tools: FoodCostCalculatorPage, PrimeCostCalculatorPage, MenuPricingCalculatorPage. SEO content: GuidesIndexPage, GuidePage (9 guides), FAQHubPage, BestAnalyticsSoftwarePage, CityIndustryPage (280+ programmatic pages)

**Components**: GarryWidget.tsx (AI chat), POSSystemPicker.tsx (80 POS systems), landing/ (MeshGradient, BentoGrid, TiltCard, ScrollReveal, MagneticButton, CountUp, TextReveal, GrainOverlay), vision/, compliance/, schedule/, demo/, space/, website/, ui/ (shadcn)

**Hooks**: useOrg.ts (CRITICAL: isDemoPath — demo only on /demo and /canada/demo), useApi.ts, useInsightsCooldown.ts

**Lib**: demo-data.ts, demo-industries.ts, agent-data.ts (39 agents), pos-systems.ts (4492L — 80+ POS systems), auth.tsx, supabase.ts

**Data**: seo-cities.ts (20 CA + 20 US cities × 7 industries), seo-guides.ts (9 guides), pos-systems.ts

## MCP Servers

Configured in `.claude/settings.json`:
- **Supabase**: `npx -y @supabase/mcp-server` — database operations
- **GitHub**: `npx -y @modelcontextprotocol/server-github` — repo management

## Common Tasks

- **Add API endpoint**: Create in `src/api/routes/`, import+include_router in `src/api/app.py`
- **Add Celery task**: Define in `src/workers/tasks.py`, add route+beat in `celery_app.py`
- **Add AI agent**: Inherit `src/ai/agents/base.py:BaseAgent`, register in `__init__.py`
- **Add email template**: Create in `src/email/templates/`, use base.py helpers
- **Restart**: `pm2 restart meridian-api celery-worker celery-beat --update-env`
- **Build check**: `cd frontend && npm run build`
- **Dev server**: `cd frontend && npx vite --port 3003 --host`

## Rules

- Never commit `.env` or credentials
- All Supabase tables need RLS
- Use `org_id` guards on all data endpoints
- Demo data only on `/demo` and `/canada/demo` paths
- Money in cents (integer), display with CA$ for Canada
- Email: Postal primary, Resend fallback
- SMS: Telnyx primary, Twilio fallback
- Pre-push: `cd frontend && npm run build` must pass (Vercel auto-deploys main)
- Max 500 lines per file — split if larger
- Heavy ML packages (torch, prophet, dspy, mem0ai) are lazy-imported — don't add to top-level imports
- LLM calls go through `src/ai/llm_layer.py` — never call OpenAI/DeepSeek directly from route handlers
