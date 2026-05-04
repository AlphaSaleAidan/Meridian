# CLAUDE.md — Meridian Project Intelligence

> This file is read automatically every session. It is the single source of truth for how this codebase works.

## Cline Rules

- Never hardcode merchant IDs, API keys, or tokens
- All new API routes go in `src/api/routes/` and must be registered in `src/api/app.py`
- Always use Row Level Security on new Supabase tables
- TypeScript strict mode — no `any` types
- Python: type hints required on all functions
- Component files max 300 lines — split if larger
- All API routes must have error handling and return typed responses
- 42+ API routes already exist — check `src/api/routes/` before creating new ones
- Auth is handled via Supabase JWT — never roll your own
- The demo portal mirrors production — every change goes in both
- Read existing similar components before writing new ones
- Check `frontend/src/data/pos-systems.ts` before touching any POS logic
- Ask before deleting anything

---

## Project Overview

**Meridian** is an AI-powered POS analytics platform for independent business owners (restaurants, smoke shops, cafes, retail). It connects to existing POS systems (Square, Clover, Toast) and delivers actionable intelligence — not just charts.

- **Website:** meridian.tips / meridian-dun-nu.vercel.app
- **Sales Portal:** meridian-sales-f7df5b93.viktor.space (Convex-powered CRM)
- **Backend:** FastAPI on Railway
- **Frontend:** Vite + React + Tailwind on Vercel
- **Database:** Supabase (PostgreSQL 15 + TimescaleDB)
- **AI:** 24 analyzers + 6 predictive modules + 15-agent Ruflo swarm
- **Mobile (planned):** Swift/SwiftUI native app for LiDAR scanning

---

## LiDAR Store Scanning — Architecture

### Why Native, Not Web
LiDAR depth sensing is NOT available via the web browser. `getUserMedia` gives a 2D
camera feed only. Apple's LiDAR sensor is only accessible through native iOS frameworks:
- **RoomPlan API** (iOS 16+, iPhone 12 Pro+) — purpose-built for indoor scanning,
  returns structured 3D room data with walls, doors, furniture, and dimensions
- **ARKit + SceneReconstruction** — raw mesh/point cloud from LiDAR

RoomPlan is the correct choice for Meridian because it outputs categorized geometry
(counters, shelves, tables) that maps directly to our zone analytics.

### Implementation Plan

#### Phase 1: Native iOS Scanner App (Swift/SwiftUI)
```
meridian-scanner/
├── MeridianScanner/
│   ├── App.swift
│   ├── ScanView.swift          # RoomPlan RoomCaptureView wrapper
│   ├── ScanSessionManager.swift # RoomCaptureSession delegate
│   ├── ScanResultView.swift     # Preview + confirm scan
│   ├── UploadService.swift      # Upload USDZ to Supabase Storage
│   └── AuthService.swift        # Supabase auth (same project)
├── Models/
│   ├── StoreScan.swift          # Scan metadata
│   └── ZoneAnnotation.swift     # SR-added zone labels
└── Info.plist                   # NSCameraUsageDescription, ARKit capability
```

**Key APIs:**
- `RoomCaptureView` — drop-in SwiftUI view that runs the full scanning UX
- `RoomCaptureSession` — manages LiDAR capture, provides real-time feedback
- `CapturedRoom` — output: walls, doors, windows, objects with dimensions
- Export as `.usdz` (3D model) + `.json` (structured room data)

**Device Requirements:**
- iPhone 12 Pro, 13 Pro, 14 Pro, 15 Pro (any Pro model with LiDAR)
- iPad Pro (2020+)
- iOS 16.0+

#### Phase 2: Upload Pipeline
```
SR scans restaurant with iPhone
    ↓ RoomPlan captures 3D room
    ↓ Export .usdz + zone metadata JSON
    ↓
Upload to Supabase Storage (bucket: store-scans/{org_id}/)
    ↓
POST /api/space/upload — save scan metadata to scans table
    ↓
Frontend loads .usdz via <model-viewer> or Three.js USDZLoader
    ↓
Overlay POS zone analytics (hot zones, traffic, revenue/sqft)
```

**Supabase Storage bucket:** `store-scans`
**Table:** `store_scans` (id, org_id, scan_url, zones_json, scanned_by, scanned_at)

#### Phase 3: Web Viewer Integration
The dashboard already has the 3D Space tab (`SpaceTab.tsx`, `SpaceViewer.tsx`).
Replace the Polycam embed with the merchant's own scan:
1. Fetch latest scan URL from `store_scans` table
2. Load .usdz in Three.js using `USDZLoader` or display via `<model-viewer>`
3. Overlay zone analytics from the existing `demoZones` data structure

#### Phase 4: Zone Analytics Mapping
Map RoomPlan's `CapturedRoom` objects to Meridian zones:
- `CapturedRoom.Object.category == .table` → dining zone
- `CapturedRoom.Object.category == .storage` → shelf/display zone
- `CapturedRoom.Object.category == .stove` → kitchen zone
- Custom annotations by SR → counter zone, entrance zone, etc.

### Interim Solution (Before Native App)
SRs use **Polycam** (free iOS app) to scan, then share the Polycam URL.
The dashboard embeds it via iframe (already implemented in SpaceTab.tsx).
Backend route `POST /api/space/polycam-link` stores the URL per org.

### Web "Open Scanner" Button Behavior
- **Demo portal:** Placeholder animation (current behavior, keep as-is)
- **Business portal (no scan exists):** Show instructions to download Polycam
  or the Meridian Scanner app (when available), with App Store link
- **Business portal (scan exists):** Show "Re-scan" option, same flow

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

### Python Libraries

#### 1. Square Python SDK (`squareup`)

**What it does**: Official Python SDK for the Square REST API — payments, orders, catalog, customers, inventory, team, OAuth.

**Our files**: `src/square/client.py` (custom httpx wrapper — **keep this**, don't migrate to SDK)

**Why we don't use the official SDK**: The SDK is synchronous-only. Our custom async httpx client gives us full control over rate limiting, retries, and asyncio integration. The SDK would require `asyncio.to_thread()` wrapping everywhere.

**Key patterns (reference only)**:
```python
from square.client import Client
client = Client(access_token="...", environment="sandbox")
result = client.orders.search_orders(body={"location_ids": ["LOC"], "query": {...}})
if result.is_success():
    orders = result.body.get("orders", [])
    cursor = result.body.get("cursor")  # pagination — loop until None
```

**Gotchas**:
- Money is `{"amount": 25000, "currency": "USD"}` (cents) — matches our convention
- Pagination uses cursors, NOT page numbers — must loop until `cursor is None`
- `Square-Version` header matters — we pin to `"2025-04-16"` in `client.py`
- Rate limits: 20 req/sec most endpoints, lower for batch
- Webhook signature: URL + raw body bytes → HMAC-SHA256, order matters

#### 2. Anthropic SDK (`anthropic`)

**What it does**: Official Python client for Claude — sync/async messaging, streaming, tool use (function calling), vision.

**Our files**: `src/ai/llm_layer.py` (currently uses raw httpx to OpenAI GPT-4o — this SDK adds Claude as alternative/fallback)

**Key patterns**:
```python
import anthropic
client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env

message = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="You are a POS analytics assistant.",  # separate param, NOT in messages
    messages=[{"role": "user", "content": "Analyze this trend..."}]
)
text = message.content[0].text
tokens_used = message.usage.output_tokens

# Streaming
async with client.messages.stream(model=..., messages=...) as stream:
    async for text in stream.text_stream:
        yield text

# Tool use
tools = [{"name": "query_revenue", "description": "...", "input_schema": {...}}]
message = await client.messages.create(model=..., tools=tools, messages=...)
for block in message.content:
    if block.type == "tool_use":
        tool_name, tool_input, tool_id = block.name, block.input, block.id
```

**Gotchas**:
- `max_tokens` is REQUIRED (no default unlike OpenAI)
- `system` is a top-level param, NOT a message role
- Streaming MUST use context manager (`async with ... as stream`)
- Typed exceptions: `anthropic.RateLimitError`, `anthropic.AuthenticationError`
- Auto-retries: 2 retries with exponential backoff for 429/500/529

#### 3. Stripe SDK (`stripe`)

**What it does**: SaaS subscription billing — payment intents, checkout sessions, subscriptions, webhooks, customer management.

**Our files**: `src/billing/billing_service.py` (currently Square-based — Stripe replaces this for Meridian's own SaaS billing)

**Key patterns**:
```python
import stripe
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

# Checkout session for subscription
session = stripe.checkout.Session.create(
    mode="subscription",
    line_items=[{"price": "price_XXX", "quantity": 1}],
    success_url="https://app.meridianpos.ai/billing/success?session_id={CHECKOUT_SESSION_ID}",
    cancel_url="https://app.meridianpos.ai/billing/cancel",
    metadata={"org_id": org_id, "plan": "standard"},
)

# Webhook verification (FastAPI)
event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
if event["type"] == "checkout.session.completed":
    org_id = event["data"]["object"]["metadata"]["org_id"]
elif event["type"] == "customer.subscription.deleted":
    # mark cancelled

# Async: wrap in asyncio.to_thread() — SDK is synchronous
session = await asyncio.to_thread(stripe.checkout.Session.create, mode="subscription", ...)
```

**Gotchas**:
- Amounts in CENTS — `25000` = $250.00 (matches our convention)
- SDK is synchronous — must wrap with `asyncio.to_thread()` for FastAPI
- Always verify webhook signatures via `stripe.Webhook.construct_event()`
- Use idempotency keys for all mutations: `idempotency_key=str(uuid4())`
- Pin API version: `stripe.api_version = "2024-12-18.acacia"`
- Typed exceptions: `stripe.error.CardError`, `stripe.error.RateLimitError`

#### 4. Sentry SDK (`sentry-sdk`)

**What it does**: Error monitoring + performance tracing for Python. Auto-instruments FastAPI, httpx, asyncpg.

**Our files**: `src/api/app.py` (add init before FastAPI), `src/ai/engine.py` (replace silent try/except with capture)

**Key patterns**:
```python
import sentry_sdk
# MUST init BEFORE importing FastAPI
sentry_sdk.init(
    dsn="...",
    traces_sample_rate=0.2,     # 20% in prod, not 1.0
    environment="production",
    release="meridian@0.2.0",
    send_default_pii=False,     # NEVER send merchant PII
)

# Manual capture in engine.py
try:
    result = agent.analyze(ctx)
except Exception as e:
    sentry_sdk.capture_exception(e)
    sentry_sdk.set_tag("agent_name", agent.__class__.__name__)
    sentry_sdk.set_tag("org_id", ctx.org_id)

# Performance spans
with sentry_sdk.start_transaction(op="ai.analyze", name="merchant-analysis") as txn:
    with sentry_sdk.start_span(op="agent", description="revenue"):
        result = revenue_agent.analyze(ctx)
```

**Gotchas**:
- Init BEFORE FastAPI import or auto-integration won't activate
- `send_default_pii=False` — we handle merchant data, no PII to Sentry
- `traces_sample_rate=1.0` burns quota fast — use 0.1-0.2 in prod
- SDK silently swallows its own errors — test with `capture_message("test")`
- Agent exceptions may create 22 separate issues — tag with `agent_name` to group

#### 5. OpenTelemetry (`opentelemetry-api`)

**What it does**: Vendor-neutral distributed tracing, metrics, and logging. Traces the full data flow: Square API → sync → DB → AI analysis.

**Our files**: `src/api/app.py` (instrumentor), `src/square/client.py` (traces), `src/ai/engine.py` (spans)

**Key patterns**:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider(resource=Resource.create({"service.name": "meridian-api"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("meridian.sync")
with tracer.start_as_current_span("backfill", attributes={"org_id": org_id}):
    with tracer.start_as_current_span("sync_orders"):
        await self._sync_orders(result)

# FastAPI auto-instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app)
```

**Gotchas**:
- `opentelemetry-api` alone is a no-op — MUST also install `opentelemetry-sdk` + exporter
- Need separate instrumentation packages: `-fastapi`, `-httpx`, `-asyncpg`
- Sentry + OTel can conflict — use `sentry_sdk.init(instrumenter="otel")` if using both
- Span attributes must be primitives (str, int, float, bool) — no dicts
- `BatchSpanProcessor` buffers in memory — spans lost on crash

#### 6. PostHog (`posthog`)

**What it does**: Product analytics + feature flags. Track merchant usage patterns, A/B test new AI features.

**Our files**: New integration — dashboard event tracking, feature flag gating for tier rollouts

**Key patterns**:
```python
from posthog import Posthog
posthog = Posthog(project_api_key='phc_...', host='https://us.i.posthog.com')

# Track events — use org_id, NOT email
posthog.capture(distinct_id=org_id, event='insight_viewed',
    properties={'category': 'revenue_trend', 'vertical': 'restaurant'})

# Feature flags for tier gating
if posthog.feature_enabled('new_forecasting_model', distinct_id=org_id):
    use_new_model()

# MUST flush on shutdown
posthog.shutdown()  # in FastAPI lifespan teardown
```

**Gotchas**:
- Events are batched async — call `posthog.shutdown()` on app exit or lose events
- `distinct_id` should be `org_id` (stable UUID), not email
- Feature flag eval makes HTTP call — enable local eval with `personal_api_key` for hot paths
- Don't track PII in properties — use org_id and business_vertical only

#### 7. statsforecast

**What it does**: Lightning-fast statistical forecasting — 30+ models (AutoARIMA, AutoETS, AutoTheta, CrostonOptimized). Numba JIT compiled, fits thousands of series in seconds.

**Our files**: `src/ai/generators/forecasts.py` (replaces hand-rolled weighted moving averages), `src/ai/agents/base.py` `forecast()` method

**Key patterns**:
```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS, CrostonOptimized

# Input MUST have columns: unique_id, ds, y (case-sensitive)
df = pd.DataFrame({
    'unique_id': ['org_123'] * len(daily),
    'ds': dates,
    'y': [r['total_revenue_cents'] / 100 for r in daily],
})

sf = StatsForecast(
    models=[AutoARIMA(season_length=7), AutoETS(season_length=7)],
    freq='D', n_jobs=-1,
)
forecasts = sf.forecast(df=df, h=7, level=[80, 95])
# Returns: ds, AutoARIMA, AutoARIMA-lo-80, AutoARIMA-hi-80, ...

# For sporadic product sales (many zero days)
sf = StatsForecast(models=[CrostonOptimized()], freq='D')
```

**Gotchas**:
- Input DataFrame MUST be `unique_id`, `ds`, `y` — exact column names, case-sensitive
- `season_length=7` for daily POS data (weekly cycle) — omitting this loses the key pattern
- First run is slow (30-60s numba JIT compilation) — warm up at startup
- Missing dates cause errors — fill gaps with `reindex(..., fill_value=0)` first
- Forecasts are in same unit as `y` — be consistent with cents vs dollars
- AutoARIMA slower but more accurate than AutoETS/AutoTheta

#### 8. Polars

**What it does**: Rust-powered DataFrame library — 10-100x faster than pandas. Lazy evaluation, columnar memory, SIMD, auto multi-threading.

**Our files**: Listed in `requirements.txt` but not yet used. Target: data transforms in AI engine, replacing pandas for new pipeline work.

**Key patterns**:
```python
import polars as pl

df = pl.DataFrame(daily_revenue)  # list[dict] works directly

# Day-of-week analysis
stats = df.with_columns(
    pl.col("date").dt.weekday().alias("dow"),
).group_by("dow").agg([
    pl.col("revenue_cents").mean().alias("avg"),
    pl.col("revenue_cents").std().alias("std"),
])

# Rolling averages
df = df.with_columns(
    pl.col("revenue_cents").rolling_mean(window_size=7).alias("ma_7d"),
)

# Convert for interop
pandas_df = polars_df.to_pandas()  # for statsforecast
records = df.to_dicts()            # for JSON API responses
```

**Gotchas**:
- NOT pandas — no `.iloc`, `.loc`, `.apply()`. Use `.filter()`, `.select()`, `.with_columns()`
- Columns are immutable — `.with_columns()` returns new DataFrame
- String dates must be cast: `pl.col("date").str.to_date("%Y-%m-%d")`
- LazyFrame does nothing until `.collect()` — forgetting this is the #1 mistake
- Uses `null` not `NaN` — use `.is_null()` and `.fill_null(0)` not `.isna()`/`.fillna()`
- Arrow memory → numpy copies data at boundary

#### 9. DuckDB

**What it does**: In-process analytical SQL engine. Runs SQL directly on DataFrames, Parquet, CSV without a server. "SQLite for analytics."

**Our files**: New — complex analytical joins in AI engine (transactions × products × inventory)

**Key patterns**:
```python
import duckdb

# Query a Polars DataFrame with SQL
transactions = pl.DataFrame(result.transactions)
daily = duckdb.sql("""
    SELECT DATE_TRUNC('day', transaction_at) AS date,
           SUM(total_cents) AS revenue, COUNT(*) AS txns
    FROM transactions
    WHERE status = 'COMPLETED'
    GROUP BY 1 ORDER BY 1
""").pl()  # .pl() → Polars, .df() → pandas

# Query Parquet files directly
duckdb.sql("SELECT * FROM 'exports/*.parquet' WHERE qty < reorder_point")

# Can attach to Postgres/Supabase for analytical queries
con = duckdb.connect()
con.sql("ATTACH 'postgresql://...' AS supabase (TYPE POSTGRES)")
```

**Gotchas**:
- Auto-detects Python variables by name in SQL — name collisions cause surprises
- Each connection is single-threaded — create per-task in async code
- `.df()` → pandas, `.pl()` → polars, `.fetchall()` → tuples — pick the right one
- In-memory DBs lost on connection close — use file path for persistence
- SQL dialect is PostgreSQL-compatible but not identical (some function names differ)

### Frontend Libraries

#### 10. @stripe/react-stripe-js

**What it does**: PCI-compliant React payment form components (`PaymentElement`, `CardElement`) + hooks (`useStripe`, `useElements`) for Stripe checkout and subscription management.

**Our files**: New — powers upgrade/checkout flow for trial→starter→growth→enterprise

**Key patterns**:
```typescript
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';

// MUST be outside component — module-level constant
const stripePromise = loadStripe('pk_live_xxx');

function App() {
  return (
    <Elements stripe={stripePromise} options={{
      clientSecret: 'pi_xxx_secret_xxx',  // from server
      appearance: { theme: 'night', variables: { colorPrimary: '#1A8FD6' } },
    }}>
      <CheckoutForm />
    </Elements>
  );
}

function CheckoutForm() {
  const stripe = useStripe();
  const elements = useElements();
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;  // not yet loaded
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: `${location.origin}/billing/success` },
    });
  };
  return <form onSubmit={handleSubmit}><PaymentElement /><button>Subscribe</button></form>;
}
```

**Gotchas**:
- `loadStripe()` MUST be called outside component — inside causes iframe remount/flicker
- `clientSecret` is required in `Elements` options for `PaymentElement` — without it, renders nothing silently
- `useStripe()` and `useElements()` return `null` until loaded — always guard
- `confirmPayment` redirects by default — use `redirect: 'if_required'` to stay on page
- Requires peer dep `@stripe/stripe-js` — install both packages
- Default theme is light — use `theme: 'night'` for our dark UI (`bg-[#0A0A0B]`)

#### 11. @sentry/react

**What it does**: React error boundary + performance profiling that reports to Sentry. Captures render errors, component mount times, React Router navigation.

**Our files**: `frontend/src/components/ErrorBoundary.tsx` (replace custom impl), `frontend/src/main.tsx` (init)

**Key patterns**:
```typescript
import * as Sentry from '@sentry/react';

// In main.tsx — BEFORE ReactDOM.createRoot()
Sentry.init({
  dsn: '...',
  integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration()],
  tracesSampleRate: 0.2,
  replaysOnErrorSampleRate: 1.0,
  environment: import.meta.env.MODE,
  release: 'meridian-dashboard@0.2.0',
});

// Replace custom ErrorBoundary
<Sentry.ErrorBoundary fallback={({ error, resetError }) => (
  <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
    <button onClick={resetError}>Try again</button>
  </div>
)}>
  <Routes>...</Routes>
</Sentry.ErrorBoundary>

// Set user context after login
Sentry.setUser({ id: user.id });  // org_id only, no PII
Sentry.setUser(null);              // on logout

// Source maps: install @sentry/vite-plugin
```

**Gotchas**:
- `Sentry.init()` must be called BEFORE React renders — top of `main.tsx`
- Need `@sentry/vite-plugin` for readable stack traces (source maps)
- `tracesSampleRate: 1.0` in prod burns quota — use 0.1-0.2
- Error boundaries don't catch event handler errors — use `Sentry.captureException()` manually
- StrictMode causes duplicate events in dev — normal, doesn't happen in prod
- Don't send merchant PII — use `id` and `org_id` only in `setUser()`

#### 12. @supabase/auth-helpers-react

**Status: DEPRECATED — do NOT install.**

**Our files**: `frontend/src/lib/auth.tsx` (custom AuthProvider — **keep this**)

**Why we skip it**: This package is deprecated by Supabase. The recommended pattern for SPAs is to use `@supabase/supabase-js` v2 directly, which is exactly what our custom `AuthProvider` already does. Our implementation correctly handles session hydration, `onAuthStateChange`, sales rep detection, business profile fetching, and token validation. Adding auth-helpers would create conflicts with no benefit.

#### 13. @square/web-sdk

**Status: NOT NEEDED for current architecture.**

**What it does**: Browser-side PCI-compliant payment form for tokenizing card data via Square.

**Why we skip it**: Meridian reads merchant data from Square (read-only OAuth). The merchant's POS collects payments, not Meridian. Only needed if we add "pay invoice through Meridian" feature.

### Additional Python Libraries (in requirements.txt)

#### 14. Prophet (`prophet`)

**What it does**: Facebook's time-series forecasting with automatic seasonality detection, holiday effects, and trend changepoints.

**Our files**: `src/ai/agents/base.py` `forecast()` method (lazy-loaded, falls back to linear extrapolation if unavailable)

**When to use**: ≥30 days of daily data. For shorter series, statsforecast AutoETS is faster. Prophet is our primary forecaster; statsforecast is the batch/speed alternative.

#### 15. PyOD (`pyod`)

**What it does**: Anomaly detection toolkit — 40+ algorithms including IsolationForest, LOF, AutoEncoder.

**Our files**: `src/ai/agents/base.py` `detect_anomalies()` method (lazy-loaded, falls back to z-score if unavailable)

**When to use**: ≥20 data points. For fewer, z-score fallback is fine. Used by revenue anomaly alerts and trend break detection.

#### 16. mlxtend

**What it does**: Frequent pattern mining and association rules (Apriori algorithm) for market basket analysis.

**Our files**: `src/ai/agents/base.py` `find_associations()` method, `src/ai/agents/basket_analysis.py`

**When to use**: ≥50 baskets. For fewer, manual pair-counting fallback activates.

#### 17. DoWhy (`dowhy`)

**What it does**: Causal inference — builds causal graphs, estimates treatment effects, runs refutation tests.

**Our files**: `src/ai/predictive/root_cause.py` (root cause analyzer)

**When to use**: When we need to determine WHY a metric changed (e.g., did a price change cause revenue drop or was it seasonal?)

### Phase 2 Libraries — Data Quality, Explainability, A/B Testing

#### 18. SHAP (`shap`)

**What it does**: Game-theoretic feature importance — Shapley values explain why any ML model made a specific prediction. TreeExplainer for tree models (fast), KernelExplainer for any black-box model.

**Our files**: All 6 predictive engines, `src/ai/generators/insights.py` (adds "why this insight" explanations)

**Key patterns**:
```python
import shap

# Tree models (XGBoost, LightGBM) — fast, exact
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Any model — slow, use small background set
background = shap.sample(X_train, 100)
explainer = shap.KernelExplainer(model.predict, background)
shap_values = explainer.shap_values(X_test[:50], nsamples=200)

# Modern API (auto-selects best algorithm)
explainer = shap.Explainer(model, X_train)
explanation = explainer(X_test)
shap.plots.waterfall(explanation[0])  # single prediction breakdown
shap.plots.beeswarm(explanation)      # global feature importance
```

**Gotchas**:
- KernelExplainer is extremely slow — always subsample background data to 100-200 rows
- Multi-class returns list of arrays (one per class) — `shap_values[1]` for class 1
- Feature mismatch: background data must have exact same columns as explanation data
- Memory blowup: compute in batches of 100-500 rows, not entire dataset
- Additivity check failures: use `feature_perturbation="interventional"` with TreeExplainer

#### 19. shapiq

**What it does**: Extends SHAP to feature *interactions* — not just "feature A is important" but "features A and B together have a synergistic/redundant effect." Implements Shapley Interaction Index, k-SII, Shapley-Taylor, Faith-Shapley.

**Our files**: `src/ai/predictive/root_cause.py` (interaction effects), `src/ai/predictive/scenario_engine.py` (combined factor analysis), all predictive modules

**Key patterns**:
```python
import shapiq

# Tree models — fast exact computation
explainer = shapiq.TreeExplainer(model=xgb_model, max_order=2, index="k-SII")
iv = explainer.explain(X_test.iloc[0])

# Any model — approximate
explainer = shapiq.TabularExplainer(
    model=model.predict, data=X_train, index="k-SII", max_order=2
)
iv = explainer.explain(X_test.iloc[0])

# Access values
iv[(0,)]       # main effect of feature 0
iv[(0, 1)]     # interaction between features 0 and 1
iv.plot_network()       # network diagram of interactions
iv.plot_stacked_bar()   # stacked bar chart
```

**Gotchas**:
- `max_order=2` is usually sufficient — order 3+ produces 1000s of terms and is rarely interpretable
- Background data: need 100-500 rows minimum for stable estimates
- Always use `TreeExplainer` for tree models — `TabularExplainer` is 100x slower
- Negative interaction = features are redundant (knowing A reduces value of B)
- Returns integer feature indices, not names — map back yourself

**Meridian value**: Root-cause analysis can say "price AND day-of-week interact" not just "price matters." Scenario engine can detect that changing price + product mix together differs from changing each alone.

#### 20. Evidently (`evidently`)

**What it does**: ML observability — data drift detection, data quality testing, model degradation monitoring. Generates interactive HTML reports and pass/fail test suites.

**Our files**: New — data pipeline gate before AI agents run, drift alerting on POS data streams

**Key patterns**:
```python
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.test_suite import TestSuite
from evidently.test_preset import DataQualityTestPreset
from evidently.tests import TestShareOfMissingValues, TestNumberOfDriftedColumns

# Drift report (visual)
report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
report.run(reference_data=df_baseline, current_data=df_new_batch)
report.save_html("drift_report.html")
report_dict = report.as_dict()  # for API responses

# Test suite (pass/fail for CI/pipeline gates)
tests = TestSuite(tests=[
    DataQualityTestPreset(),
    TestShareOfMissingValues(lte=0.05),      # max 5% missing
    TestNumberOfDriftedColumns(lte=2),        # max 2 drifted columns
])
tests.run(reference_data=df_ref, current_data=df_current)
if not tests.as_dict()["summary"]["all_passed"]:
    raise ValueError("Data quality gate failed")
```

**Gotchas**:
- Reference data is REQUIRED for drift detection — use validated 30-day historical window
- Always define `ColumnMapping` explicitly — without it, IDs get classified as numerical features
- Large datasets (1M+ rows) are slow — sample first
- Default drift thresholds may be too sensitive for POS data with natural seasonality — tune `stattest_threshold`
- API changed significantly in v0.4+ — use `Report`/`TestSuite`, not deprecated `Dashboard`/`Profile`

#### 21. whylogs

**What it does**: Lightweight statistical data profiling for continuous monitoring. Generates mergeable, serializable profiles (protobuf) that capture distributions, missing values, data types without storing raw data. Privacy-preserving by design.

**Our files**: New — inline profiling on every POS data batch, data quality constraints

**Key patterns**:
```python
import whylogs as why

# Profile a batch
results = why.log(df_transactions)
profile_view = results.profile().view()

# Serialize (very compact — protobuf)
results.writer("local").write(dest="profiles/")

# Constraints (data quality checks)
from whylogs.core.constraints import ConstraintsBuilder
from whylogs.core.constraints.factories import greater_than_number, no_missing_values

builder = ConstraintsBuilder(dataset_profile_view=profile_view)
builder.add_constraint(no_missing_values(column_name="transaction_id"))
builder.add_constraint(greater_than_number(column_name="revenue", number=0))
constraints = builder.build()
report = constraints.generate_constraints_report()

# Drift detection (compare profiles)
from whylogs.viz import NotebookProfileVisualizer
viz = NotebookProfileVisualizer()
viz.set_profiles(target_profile_view=curr_view, reference_profile_view=ref_view)
viz.summary_drift_report()
```

**Gotchas**:
- Profiles are statistical summaries — cannot reconstruct individual rows (feature, not bug)
- Key pattern: merge hourly profiles into daily/weekly via `profile1.merge(profile2)`
- v1 API (`why.log()`) differs significantly from v0 (`session.log_dataframe()`)
- Cardinality uses HyperLogLog — approximate, not exact (within 2%)

**whylogs vs evidently**: whylogs runs inline on every batch (<100ms overhead), produces tiny mergeable profiles. Evidently runs on schedule for deeper analysis with HTML reports. Use both: whylogs for real-time gates, evidently for periodic drift investigations.

#### 22. ydata-profiling (`ydata-profiling`)

**What it does**: One-line comprehensive EDA reports — statistics, distributions, correlations, missing values, duplicates, interactions. Interactive HTML output.

**Our files**: New — on-demand data exploration during POS onboarding, data quality assessment

**Key patterns**:
```python
from ydata_profiling import ProfileReport

# Full report (slow on large datasets)
profile = ProfileReport(df, title="POS Data Profile")
profile.to_file("report.html")
profile.to_json()

# Minimal mode (fast, for large datasets)
profile = ProfileReport(df, title="Quick Profile", minimal=True)

# Compare two time periods
profile_jan = ProfileReport(df_jan, title="January")
profile_feb = ProfileReport(df_feb, title="February")
comparison = profile_jan.compare(profile_feb)
comparison.to_file("jan_vs_feb.html")

# Time-series mode
profile = ProfileReport(df, tsmode=True, sortby="transaction_date")
```

**Gotchas**:
- Extremely slow on 100K+ rows — always use `minimal=True` for large datasets
- Package renamed from `pandas_profiling` to `ydata_profiling` — old import fails
- HTML reports can be 50MB+ — use `to_json()` for programmatic consumption
- Pairwise correlations are O(n^2) in features — disable unnecessary types for wide datasets

**When to use**: On-demand during onboarding, NOT for continuous monitoring (too slow). Use whylogs for that.

#### 23. mlforecast

**What it does**: ML-based time series forecasting — automates lag/rolling feature engineering, supports any scikit-learn/LightGBM/XGBoost model. Multi-series, distributed (Spark/Dask/Ray).

**Our files**: `src/ai/agents/forecaster.py` (complement to statsforecast — ML models instead of statistical), `src/ai/predictive/demand_forecast.py`

**Key patterns**:
```python
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, RollingStd, ExponentiallyWeightedMean
from lightgbm import LGBMRegressor

# Input: unique_id, ds, y columns (same as statsforecast)
fcst = MLForecast(
    models=[LGBMRegressor(n_estimators=100, learning_rate=0.1)],
    freq="D",
    lags=[1, 7, 14, 28],
    lag_transforms={
        7: [RollingMean(window_size=7), RollingStd(window_size=7)],
        28: [ExponentiallyWeightedMean(alpha=0.3)],
    },
    date_features=["dayofweek", "month"],
    num_threads=4,
)
fcst.fit(df_train)
predictions = fcst.predict(h=30)

# Cross-validation
cv_results = fcst.cross_validation(df=df_train, h=7, n_windows=3, step_size=7)

# Exogenous variables (promotions, holidays)
fcst.fit(df_train, static_features=["store_type"])
predictions = fcst.predict(h=30, X_df=df_future_exogenous)
```

**Gotchas**:
- Same strict DataFrame format as statsforecast: `unique_id`, `ds`, `y` — case-sensitive
- Future exogenous variables MUST be provided at predict time — silently dropped if missing
- Series shorter than max lag are silently dropped during fit
- `freq` must match actual data frequency — mismatch breaks lag alignment
- Recursive multi-step prediction compounds errors — use shorter horizons (7-14 days)

**statsforecast vs mlforecast**: statsforecast (AutoARIMA, AutoETS) is statistical, fast, good for simple patterns. mlforecast (LightGBM, XGBoost) handles complex feature interactions (promotions × day-of-week × product). Use both and ensemble.

#### 24. Shapash (`shapash`)

**What it does**: Human-readable ML explanations — wraps SHAP/LIME to produce interactive dashboards and business-friendly text explanations with automatic feature-name mapping.

**Our files**: `src/ai/generators/insights.py` (turns SHAP values into natural language "why this insight" explanations)

**Key patterns**:
```python
from shapash import SmartExplainer

xpl = SmartExplainer(
    model=trained_model,
    features_dict={"col_0": "Customer Age", "col_1": "Revenue Last 30d"},
    label_dict={0: "Not Churned", 1: "Churned"},
)
xpl.compile(x=X_test, y_pred=predictions, y_target=y_test)

# Text explanations for API responses
summary_df = xpl.to_pandas(max_contrib=3)
# Returns: feature_1, value_1, contribution_1, feature_2, ...
# Template into: "Revenue declined primarily because Average Basket dropped 15%..."

# Static plots (for API responses, not Dash dashboard)
xpl.plot.local_plot(index=42)       # single prediction waterfall
xpl.plot.features_importance()       # global importance

# Production deployment
predictor = xpl.to_smartpredictor()
predictor.save("./predictor.pkl")
```

**Gotchas**:
- Requires SHAP or LIME installed — it's a wrapper, not a standalone explainer
- `compile()` computes SHAP for entire X_test — use representative subset (1K-5K rows)
- Dash-based dashboard (`run_app()`) needs separate service — use static methods for FastAPI
- Preprocessing must be invertible for human-readable labels — define `features_dict` explicitly
- Memory-intensive at compile time

#### 25. BayesABTest (`bayesabtest`)

**What it does**: Bayesian A/B testing with conjugate priors (no MCMC — instant results). Supports binary (conversion), continuous (revenue), and count (transactions) data. Outputs probability-of-being-best and expected loss in dollars.

**Our files**: `src/ai/predictive/scenario_engine.py` (promo ROI), new promo A/B analysis capability

**Key patterns**:
```python
from bayesabtest import BinaryTest, ContinuousTest, CountTest

# Binary: did the promo increase conversion?
test = BinaryTest()
test.update('control', trials=1000, successes=50)
test.update('treatment', trials=1000, successes=65)
result = test.evaluate()
# result.probability_of_being_best → {'control': 0.04, 'treatment': 0.96}
# result.expected_loss → how many dollars we lose by picking wrong variant

# Continuous: did the promo increase basket size?
test = ContinuousTest()
test.update('control', data=control_revenue_array)
test.update('treatment', data=treatment_revenue_array)
result = test.evaluate()

# Count: did the promo increase visit frequency?
test = CountTest()
test.update('control', count=500, exposure=1000)
test.update('treatment', count=620, exposure=1000)
result = test.evaluate()
```

**Gotchas**:
- Conjugate priors = fast but rigid assumptions (Beta-Binomial, Normal-Normal, Gamma-Poisson)
- BinaryTest takes summary stats (trials, successes) — NOT raw arrays
- ContinuousTest takes raw arrays — different interface from BinaryTest
- Revenue data is often skewed — Normal assumption may not hold, consider log-transform
- Expected loss > probability-of-best for decision-making (answers "how much money am I risking")

**Why BayesABTest over abyes**: No MCMC means instant results (no PyMC dependency), accepts summary stats (easier POS integration), produces expected-loss in dollars (maps to our confidence-score framework).

#### 26. xplainable

**What it does**: Explainable-by-design ML — models produce per-feature contribution scores natively during prediction (not post-hoc like SHAP). XClassifier and XRegressor with built-in `explain()`.

**Our files**: `src/ai/generators/insights.py` (alternative to SHAP for simpler models)

**Key patterns**:
```python
from xplainable.core.models import XClassifier, XRegressor

model = XClassifier()
model.fit(X_train, y_train)
predictions = model.predict(X_test)

# Built-in explanations (no separate SHAP step)
contributions = model.explain(X_test)
model.feature_importances  # dict of feature → importance
model.plot_contributions(X_test.iloc[0])  # waterfall
```

**Gotchas**:
- NOT a wrapper around sklearn — custom model architecture, accuracy may be lower than XGBoost
- `explain()` returns per-feature contributions per row — can be very large DataFrame
- Cloud/API features require registration — open-source core is fully functional

**When to use**: Simpler classification/regression tasks where built-in explainability saves the SHAP computation step. For complex models where accuracy matters, use SHAP/shapiq on XGBoost instead.

#### 27. BlueGraph (`bluegraph`)

**What it does**: Graph analytics library — property graphs, community detection, node embeddings, path analysis. Multi-backend (NetworkX, Neo4j, Neptune).

**Our files**: `src/ai/agents/basket_analysis.py` (product co-purchase graph, community detection)

**Key patterns**:
```python
from bluegraph.core import PandasPGFrame
from bluegraph.backends.networkx import NXAnalyser, NXNodeEmbedder

# Build product co-purchase graph
graph = PandasPGFrame(nodes=products_df, edges=copurchase_df)
analyser = NXAnalyser(graph)

# Community detection (natural product clusters)
communities = analyser.community_detection(method='louvain')

# PageRank (anchor products that drive baskets)
pagerank = analyser.pagerank()

# Product similarity via embeddings
embedder = NXNodeEmbedder(graph)
embeddings = embedder.fit_transform(method='node2vec', dimensions=64)
similar = embedder.most_similar('product_123', top_n=10)
```

**Gotchas**:
- `pip install bluegraph` gives only NetworkX backend — Neo4j needs `bluegraph[neo4j]`
- Node embedding needs connected graphs — isolated nodes produce meaningless results
- NetworkX backend is slow at 100K+ nodes — switch to Neo4j for large catalogs
- Project maintenance may be reduced — check latest commits before depending on it

**When to use**: When basket analysis needs to go beyond association rules to graph-based product clustering and embeddings. For standard Apriori/FP-Growth, mlxtend is simpler. BlueGraph adds value for 10K+ SKU catalogs with dense co-purchase networks.

### Data Pipeline Architecture

```
POS Data Stream
    │
    ▼
[whylogs] → profile + constraints → PASS/FAIL gate (<100ms)
    │
    ▼ (if PASS)
[evidently] → periodic drift reports + test suites (hourly/daily)
    │
    ▼
[22 AI Agents]
    ├── forecaster → [statsforecast + mlforecast] → ensemble
    ├── churn agent → model → [shap/shapiq] → explained predictions
    ├── pricing agent → model → [shapiq] → interaction effects
    ├── basket agent → [mlxtend + BlueGraph] → associations + graph clusters
    ├── scenario engine → [BayesABTest] → promo ROI with confidence
    └── ... other agents ...
    │
    ▼
[shapash] → human-readable explanations
    │
    ▼
[InsightGenerator] → prioritized insights with "why" attribution
```

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

---

## AI Power-Up Libraries — Wave 2: Vision, Processing, Explainability

### Face Tracking & Customer Indexing (NEW capability)

Architecture: Cameras → YOLO (detect) → ByteTrack (track) → DeepFace/InsightFace (identify) → Meridian DB → AI Agents

| Library | Stars | Purpose | Creates |
|---------|-------|---------|---------|
| `serengil/deepface` | 22,655 | Face recognition + age/gender/emotion analysis. One API = identity + demographics. | NEW: customer indexing agent |
| `deepinsight/insightface` | 25,000+ | State-of-the-art ArcFace embeddings. Higher accuracy for re-identification across visits. | NEW: face embedding engine |
| `exadel-inc/CompreFace` | 7,904 | Self-hosted face recognition REST API in Docker. Zero cloud dependency. | NEW: on-prem face API service |
| `ultralytics/ultralytics` | 40,000+ | YOLOv8/YOLO11 real-time person detection + pose estimation. | NEW: person detection pipeline |
| `FoundationVision/ByteTrack` | 6,339 | Multi-object tracking across frames. Consistent person IDs through store. | NEW: person tracking agent |
| `mikel-brostrom/boxmot` | 8,135 | Pluggable MOT (DeepSORT, ByteTrack, BoT-SORT). Pair with YOLO. | NEW: tracking pipeline |
| `roboflow/supervision` | 25,000+ | CV toolbox for annotation, heatmaps, zone tracking, path visualization. | NEW: visual analytics overlay |

New agents this enables:
- **Foot Traffic Analyzer** — hourly/daily/weekly visit counts + trends
- **Dwell Time Optimizer** — time spent per zone
- **Customer Recognition** — "John visited 12x this month, avg spend $47"
- **Demographic Insights** — age/gender distribution by time of day
- **Queue Length Monitor** — real-time wait time at checkout

### Data Processing & Profiling
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `pola-rs/polars` | 38,348 | 10-100x faster than pandas. Use for all POS data aggregations, RFM, cohorts. | All data crunching across agents |
| `ydataai/ydata-profiling` | 13,000+ | Auto data profiling: missing values, distributions, correlations, duplicates. | Data quality gate in `src/pipeline.py` |
| `MAIF/shapash` | 3,211 | ML explainability dashboard. Shows *why* AI makes each recommendation. | `src/ai/generators/insights.py`, insight-narrator |

### A/B Testing & Experimentation
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `cbellei/abyes` | 61 | Bayesian A/B testing. Measure if pricing/menu changes actually worked. | `src/ai/predictive/scenario_engine.py` |
| `BakermMoran/BayesABTest` | 21 | Simple Bayesian AB test framework for business users. | `src/ai/agents/promo_roi.py` |
| `evidentlyai/evidently` | 6,000+ | ML monitoring + data drift detection. Auto-detect when merchant patterns shift. | Pipeline monitoring, model retraining |

### Explainability & Insight Generation
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `xplainable/xplainable` | 64 | Real-time explainable ML for business optimization. Plain-English explanations. | `src/ai/generators/insights.py` |
| `BlueBrain/BlueGraph` | 34 | Graph analytics for co-occurrence. Customer-product interaction graphs. | `src/ai/agents/basket_analysis.py` |
| `shapiq` | 722 | Shapley interaction values. Feature *combinations* driving predictions. | All predictive modules |

### Advanced Predictions
| Library | Stars | Purpose | Enhances |
|---------|-------|---------|----------|
| `Nixtla/mlforecast` | 1,000+ | ML-based forecasting (LightGBM/XGBoost on time series). | `src/ai/agents/forecaster.py` |
| `whylabs/whylogs` | 3,000+ | Data logging for ML pipelines. Audit every prediction. | Pipeline monitoring |
