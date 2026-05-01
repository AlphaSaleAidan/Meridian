# CLAUDE.md — Meridian Project Intelligence

> This file is read automatically every session. It is the single source of truth for how this codebase works.

---

## Project Overview

**Meridian** is an AI-powered POS analytics platform for independent business owners (restaurants, smoke shops, cafes, retail). It connects to existing POS systems (Square, Clover, Toast) and delivers actionable intelligence — not just charts.

- **Website:** meridian.tips / meridian-dun-nu.vercel.app
- **Sales Portal:** meridian-sales-f7df5b93.viktor.space (Convex-powered CRM)
- **Backend:** FastAPI on Railway
- **Frontend:** Vite + React + Tailwind on Vercel
- **Database:** Supabase (PostgreSQL 15 + TimescaleDB)
- **AI:** 24 analyzers + 6 predictive modules + 15-agent Ruflo swarm

---

## Architecture

```
POS (Square/Clover/Toast)
    ↓ OAuth
Sync Engine (backfill + 15min incremental + webhooks)
    ↓
Supabase (24 tables, RLS, TimescaleDB hypertables)
    ↓
AI Engine (24 analyzers → insights, forecasts, scores)
    ↓
React Dashboard (customer-facing)
```

### Directory Map

```
├── src/                          # Backend source code
│   ├── ai/
│   │   ├── agents/               # 24 AI analysis agents
│   │   │   ├── base.py           # Base agent class
│   │   │   ├── basket_analysis.py
│   │   │   ├── benchmark.py
│   │   │   ├── cash_flow.py
│   │   │   ├── cashflow_forecast.py
│   │   │   ├── category_mix.py
│   │   │   ├── customer_ltv.py
│   │   │   ├── day_of_week.py
│   │   │   ├── discount_analyzer.py
│   │   │   ├── employee_perf.py
│   │   │   ├── forecaster.py      # → Replace with statsforecast
│   │   │   ├── growth_score.py
│   │   │   ├── inventory_intel.py
│   │   │   ├── money_left.py      # Core "Money Left on Table" metric
│   │   │   ├── payment_optimizer.py
│   │   │   ├── peak_hours.py
│   │   │   ├── pricing_power.py
│   │   │   ├── product_velocity.py
│   │   │   ├── promo_roi.py
│   │   │   ├── revenue_trend.py
│   │   │   ├── seasonality.py
│   │   │   ├── staffing.py
│   │   │   └── waste_shrinkage.py
│   │   ├── analyzers/            # Core analysis engines
│   │   │   ├── money_left.py
│   │   │   ├── patterns.py
│   │   │   ├── products.py
│   │   │   └── revenue.py
│   │   ├── predictive/           # ML prediction modules
│   │   │   ├── churn_warning.py
│   │   │   ├── demand_forecast.py
│   │   │   ├── dynamic_pricing.py
│   │   │   ├── goal_tracker.py
│   │   │   ├── root_cause.py
│   │   │   └── scenario_engine.py
│   │   ├── generators/           # Output generators
│   │   │   ├── forecasts.py
│   │   │   ├── insights.py
│   │   │   └── reports.py
│   │   ├── engine.py             # Main AI pipeline orchestrator
│   │   └── llm_layer.py          # LLM abstraction (OpenAI → add Anthropic)
│   ├── api/
│   │   ├── app.py                # FastAPI app + CORS
│   │   └── routes/
│   │       ├── admin.py
│   │       ├── billing.py
│   │       ├── dashboard.py
│   │       ├── oauth.py           # POS OAuth flows
│   │       ├── onboarding.py
│   │       ├── payouts.py
│   │       ├── predictive.py
│   │       └── webhooks.py        # POS webhook receivers
│   ├── billing/
│   │   └── billing_service.py    # → Upgrade to Stripe SDK
│   ├── square/                   # Square POS integration
│   │   ├── client.py             # → Replace with square-python-sdk
│   │   ├── mappers.py            # Data mapping Square → Supabase
│   │   ├── oauth.py
│   │   ├── rate_limiter.py
│   │   ├── sync_engine.py        # Backfill + incremental + webhooks
│   │   └── webhook_handlers.py
│   ├── clover/                   # Clover POS integration
│   │   ├── client.py             # Same structure as Square
│   │   ├── mappers.py
│   │   ├── oauth.py
│   │   ├── rate_limiter.py
│   │   ├── sync_engine.py
│   │   └── webhook_handlers.py
│   ├── db/                       # Database clients & queries
│   ├── payouts/
│   ├── security/
│   ├── sync/
│   │   └── customer_app.py
│   ├── workers/                  # Background workers
│   ├── config.py                 # All config from env vars
│   ├── pipeline.py               # Main data pipeline orchestrator
│   └── tests/
├── app/                          # Application services layer
│   ├── api/square/               # Square API handlers
│   ├── services/square/          # Square service layer
│   └── workers/                  # Background workers
├── frontend/                     # Vite + React frontend
│   ├── src/
│   │   ├── pages/                # All dashboard pages
│   │   │   ├── OverviewPage.tsx     # Main dashboard
│   │   │   ├── RevenuePage.tsx
│   │   │   ├── ProductsPage.tsx
│   │   │   ├── CustomersPage.tsx
│   │   │   ├── StaffPage.tsx
│   │   │   ├── ForecastsPage.tsx
│   │   │   ├── InsightsPage.tsx
│   │   │   ├── AnomaliesPage.tsx
│   │   │   ├── InventoryPage.tsx
│   │   │   ├── MarginsPage.tsx
│   │   │   ├── PeakHoursPage.tsx
│   │   │   ├── MenuEngineeringPage.tsx
│   │   │   ├── ActionsPage.tsx
│   │   │   ├── AgentDashboardPage.tsx
│   │   │   ├── NotificationsPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   ├── OnboardingPage.tsx
│   │   │   ├── OnboardingWizard.tsx
│   │   │   ├── LandingPage.tsx
│   │   │   ├── PortalPage.tsx
│   │   │   ├── CareersPage.tsx
│   │   │   ├── AdminPage.tsx
│   │   │   ├── sales/              # Sales rep pages
│   │   │   └── customer/           # Customer portal pages
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── SalesLayout.tsx
│   │   │   ├── DashboardTiltCard.tsx
│   │   │   ├── InsightCard.tsx
│   │   │   ├── MoneyLeftCard.tsx
│   │   │   ├── RevenueChart.tsx
│   │   │   ├── StatCard.tsx
│   │   │   ├── ConnectionBadge.tsx
│   │   │   ├── ScrollReveal.tsx
│   │   │   ├── TransactionDrillDown.tsx
│   │   │   └── landing/            # Landing page components
│   │   ├── hooks/
│   │   │   ├── useApi.ts           # API client hook
│   │   │   └── useOrg.ts           # Org context hook
│   │   └── lib/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── vercel.json
├── docs/
│   ├── architecture-decisions.md   # ADRs (read these!)
│   └── customer-sop.md             # Sales-to-onboarding SOPs
├── scripts/
│   ├── run_pipeline.py
│   └── verify_supabase.py
├── supabase/migrations/            # DB migration files
├── 000_SCHEMA_OVERVIEW.md          # Database schema documentation
├── 001-010_*.sql                   # SQL migration files (numbered)
├── ruflo.config.yaml               # 15-agent swarm configuration
├── Dockerfile                      # Railway deployment
├── Procfile                        # Railway process file
├── requirements.txt                # Python dependencies
└── .env.example                    # Required environment variables
```

---

## Database Schema

24 tables + 4 continuous aggregates across 5 domains:
- **Core:** organizations, locations, users, subscriptions, pos_connections
- **Product & Transactions:** products, categories, transactions (hypertable), transaction_items (hypertable), inventory_snapshots (hypertable)
- **Operations:** suppliers, scheduled_events, notifications, notification_rules
- **Intelligence:** insights, money_left_scores, forecasts, chat_conversations, chat_messages, weekly_reports
- **Benchmarking:** benchmark_profiles, benchmark_snapshots, industry_aggregates (THE DATA ASSET), data_export_logs

**TimescaleDB hypertables** for all time-series data. **RLS** on every table. **Continuous aggregates** for hourly/daily/weekly rollups.

---

## Key Business Rules

- **All money values are stored in CENTS** (integer). Never use floats for money. $250.00 = 25000 cents.
- **Flat pricing: $250/mo per account** (standard Meridian plan). No tiers.
- **Commission rate: 70%** for all sales reps. $250 × 70% = $175/deal.
- **POS data flow:** OAuth → Sync Engine (18mo backfill + 15min incremental + webhooks) → Supabase → AI Engine → Dashboard
- **Demo mode** uses `org_id = 'demo'` with client-side mock data. No auth required for `/demo` routes.
- **Multi-tenant** — every query scoped to `business_id`. RLS enforces isolation at DB level.
- **Token-based provisioning** — sales rep generates single-use access token, customer redeems to activate.

---

## Guard Rails

### NEVER do these:
- ❌ Modify numbered SQL migration files (001-010) directly
- ❌ Delete or overwrite seed data without explicit permission
- ❌ Use floating point for money calculations
- ❌ Store money in dollars (always cents)
- ❌ Make global queries without business_id scoping
- ❌ Commit directly to main — always create a branch
- ❌ Change the database schema without creating a migration file
- ❌ Expose internal API keys or secrets in frontend code
- ❌ Remove RLS policies from any table

### ALWAYS do these:
- ✅ Run tests before committing
- ✅ Create a git branch for any changes
- ✅ Use cents for all money values
- ✅ Scope data queries to business_id
- ✅ Check architecture-decisions.md before making structural changes
- ✅ Add type hints to all Python functions
- ✅ Handle rate limiting when calling POS APIs
- ✅ Ask before changing billing logic or commission calculations

---

## Ruflo Agent Swarm (ruflo.config.yaml)

15-agent hierarchical swarm with 7 execution levels:
- **Level 0:** Transaction Analyst (foundation)
- **Level 1:** Revenue Forecaster, Product Intelligence, Customer Segmentor, Staff Performance
- **Level 2:** Retention Strategist, Peak Hour Optimizer, Inventory Intelligence, Margin Optimizer
- **Level 3:** Competitor Benchmarker, Loyalty Architect, Location Analyst
- **Level 4:** Insight Narrator (writes plain English summaries)
- **Level 5:** Action Prioritizer (Top 3 daily actions)
- **Level 6:** Feature Engineer (product roadmap)

Model: `claude-haiku-3-5-20251001`, consensus: raft, memory: Supabase-backed shared context.

---

## Library Skills

### Currently Installed (Python)
- `fastapi` + `uvicorn` — API server
- `httpx` — Async HTTP (used for POS API calls)
- `supabase` + `asyncpg` — Database
- `openai` — LLM for AI insights
- `numpy` + `pandas` + `polars` — Data processing
- `prophet` + `statsforecast` — Time-series forecasting
- `pyod` — Anomaly detection
- `mlxtend` — Basket/association analysis
- `dowhy` — Causal inference
- `scipy` — Statistical analysis
- `cryptography` + `bcrypt` — Security

### Currently Installed (Frontend)
- `react` 18 + `react-dom` + `react-router-dom`
- `@react-three/fiber` + `@react-three/drei` + `three` — 3D visualizations
- `framer-motion` + `gsap` + `lenis` — Animations
- `recharts` — Charts
- `lucide-react` — Icons
- `@supabase/supabase-js` — Auth + DB client
- `tailwindcss` — Styling

### Recommended Additions
| Library | Purpose | Replaces/Enhances |
|---------|---------|-------------------|
| `square-python-sdk` | Official Square SDK | `src/square/client.py` (raw httpx) |
| `@square/web-sdk` | Frontend card tokenization | Manual checkout flow |
| `anthropic` | Claude as LLM fallback | `src/ai/llm_layer.py` |
| `stripe` + `react-stripe-js` | Subscription billing | `src/billing/billing_service.py` |
| `sentry-sdk` + `@sentry/react` | Error tracking | No monitoring currently |
| `opentelemetry-api` | Pipeline tracing | No observability currently |
| `posthog-python` | Product analytics | No usage tracking currently |
| `duckdb` | In-process analytics | Complex pandas aggregations |
| `@supabase/auth-helpers-react` | Simplified React auth | Custom auth hooks |

---

## Environment Variables

```
# Square
SQUARE_ENVIRONMENT=sandbox|production
SQUARE_APP_ID=
SQUARE_APP_SECRET=
SQUARE_ACCESS_TOKEN=

# Clover
CLOVER_ENVIRONMENT=sandbox|production
CLOVER_APP_ID=
CLOVER_APP_SECRET=
CLOVER_ACCESS_TOKEN=
CLOVER_MERCHANT_ID=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
DATABASE_URL=

# AI
OPENAI_API_KEY=
```

---

## Key Commands

```bash
# Backend
pip install -r requirements.txt
uvicorn src.api.app:app --reload          # Start dev server
python scripts/run_pipeline.py             # Run full AI pipeline
python scripts/verify_supabase.py          # Verify DB connection

# Frontend
cd frontend
npm install
npm run dev                                # Start Vite dev server
npm run build                              # Production build

# Deploy
# Backend: push to main → Railway auto-deploys
# Frontend: push to main → Vercel auto-deploys
```

---

## Common Patterns

### Adding a new AI agent
1. Create `src/ai/agents/your_agent.py`
2. Extend `BaseAgent` from `src/ai/agents/base.py`
3. Implement `analyze(data)` method
4. Register in `src/ai/engine.py`
5. Add to `ruflo.config.yaml` if it should run in the swarm

### Adding a new API route
1. Create handler in `src/api/routes/your_route.py`
2. Register in `src/api/routes/__init__.py`
3. Always scope queries to `business_id` from auth context
4. Return cents for money values

### Adding a new frontend page
1. Create `frontend/src/pages/YourPage.tsx`
2. Add route in `frontend/src/App.tsx`
3. Use `useApi()` hook for backend calls
4. Use `useOrg()` hook for business context
5. Money display: always `(cents / 100).toLocaleString()`

---

## Sales Portal (Separate App)

The sales CRM is a separate Convex app at `meridian-sales-f7df5b93.viktor.space`. It is NOT in this repo — it's managed via Viktor Spaces.
- Stack: Convex + React + Tailwind
- Auth: Convex Auth (email/password)
- Tracks: leads, deals, commissions, proposals
- Flat pricing: $250/mo, 70% commission rate

---

## AI Power-Up Libraries — Customer Data Breakdown

These repos supercharge Meridian's ability to analyze POS customer data:

### Customer Intelligence
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `pymc-labs/pymc-marketing` | 1,139 | Bayesian CLV + BG/NBD models. Predicts customer lifetime value and who's about to churn. | `src/ai/agents/customer_ltv.py`, retention-strategist agent |
| `py-why/EconML` | 4,614 | Microsoft's causal inference. Measures true promo ROI — "did this promotion *cause* more sales?" | `src/ai/agents/promo_roi.py`, `src/ai/predictive/root_cause.py` |
| `yzhao062/pyod` | 9,834 | 60+ anomaly detection algorithms for fraud, refund abuse, suspicious patterns. | `src/ai/agents/money_left.py`, transaction-analyst agent |

### Time-Series & Forecasting
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `unit8co/darts` | 9,354 | Unified API for 30+ forecasting + anomaly detection models. Auto-selects best model. | `src/ai/agents/forecaster.py`, revenue-forecaster agent |
| `nixtla/neuralforecast` | 3,000+ | Deep learning forecasting (N-BEATS, NHITS, PatchTST). Best for 12mo+ data. | `src/ai/predictive/demand_forecast.py` |
| `facebook/prophet` | (existing) | Keep for seasonality decomposition + holiday effects. | `src/ai/agents/seasonality.py` |
| `nixtla/statsforecast` | (existing) | Keep for fast daily AutoARIMA/Theta predictions. | `src/ai/agents/forecaster.py` |

### Tabular ML (Predictions on Structured POS Data)
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `microsoft/LightGBM` | 17,000+ | Gradient boosting for churn prediction, staff scoring, product ranking. | All tabular prediction tasks across agents |
| `catboost/catboost` | 8,000+ | Handles categorical features natively (product types, payment methods, day-of-week). Zero preprocessing. | `src/ai/agents/product_velocity.py`, `src/ai/agents/employee_perf.py` |

### Data Quality & Missing Data
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `great-expectations/great_expectations` | 10,000+ | Validate POS data before AI runs (no negatives, no future dates, sane amounts). | Data ingestion pipeline, `src/pipeline.py` |
| `WenjieDu/PyPOTS` | 2,004 | Fill gaps in incomplete POS data (offline sales, downtime). AI doesn't hallucinate on missing data. | All analyzers that consume transaction data |
| `arundo/adtk` | 1,206 | Rule-based time-series anomaly detection. Auto-detect revenue drops, traffic spikes, seasonal shifts. | `src/ai/agents/peak_hours.py`, `src/ai/agents/revenue_trend.py` |

### NLP & Embeddings (Review/Feedback Data)
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `huggingface/transformers` | 140,000+ | Sentiment analysis on Google/Yelp reviews. What do customers love/hate? | `src/ai/generators/insights.py`, insight-narrator agent |
| `UKPLab/sentence-transformers` | 16,000+ | Embed products + customer patterns into vectors. "Find similar customers" and cross-store benchmarking. | `src/ai/agents/benchmark.py`, competitor-benchmarker agent |

### Basket & Association Analysis
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `rasbt/mlxtend` | (existing) | Use `fpgrowth` instead of `apriori` (10x faster). Bundle recommendations. | `src/ai/agents/basket_analysis.py` |

### Causal Inference
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `py-why/dowhy` | (existing) | Already installed. Use for pricing experiments and treatment effects. | `src/ai/predictive/dynamic_pricing.py` |
| `py-why/EconML` | 4,614 | Heterogeneous treatment effects. Per-customer promo impact. | `src/ai/agents/promo_roi.py` |

### Priority Install Order
1. `pymc-marketing` — CLV prediction is the #1 most requested merchant insight
2. `darts` — replaces fragmented forecasting with unified auto-selecting engine
3. `lightgbm` — one model for all tabular predictions
4. `EconML` — causal promo ROI (huge competitive moat)
5. `great-expectations` — data quality gate prevents bad AI outputs
6. `catboost` — handles POS categorical data natively
7. `adtk` — lightweight anomaly detection
8. `PyPOTS` — missing data handling
9. `sentence-transformers` — cross-store intelligence
10. `neuralforecast` — deep learning for merchants with long history
