# Meridian Dead Code Audit Report

**Date:** 2026-05-08
**Auditor:** Claude Code (automated)
**Scope:** Full codebase — `src/`, `services/`, `frontend/`, `app/`, `storage/`, `marketplace/`, `scripts/`, `tools/`, root files

---

## Section 1 — Summary

| Metric | Count |
|--------|-------|
| **Total dead code items found** | 97 |
| **Items connected (wired up)** | 0 |
| **Items removed** | 113 files changed, 10,656 lines deleted |
| **Items deferred (left with TODO)** | 8 unimplemented agents, vision/predictive routes |
| **Lines before audit** | ~79,400 (source only) |
| **Lines after audit** | ~68,700 (source only) |
| **Disk reclaimed** | 810 MB (.venv) + ~200 KB source |
| **Security fix** | Hardcoded Supabase JWT removed from scripts/verify_supabase.py |
| **Packages removed** | 11 Python, 5 JavaScript |

### By Category

| Category | Items |
|----------|-------|
| Cat 1: Unused Python imports | 35 imports across 26 files |
| Cat 2: Unused JS/TS imports & orphaned components | 20 files (~4,439 lines) |
| Cat 3: Unreachable API routes | 37 of 63 routes (59%) |
| Cat 4: Orphaned frontend components | 8 components + 1 hook + 1 lib |
| Cat 5: Agent config vs implementation gaps | 8 config agents missing impl; 14 impl agents missing config |
| Cat 6: Dead database columns/tables | Not audited (requires DB access) |
| Cat 7: Unused installed packages | See package audit below |
| Cat 8: Dead environment variables | 1 confirmed unused |
| Cat 9: Commented-out code blocks | Included in per-file findings |
| Cat 10: Services defined but not started | `app/` directory (complete duplicate) |

---

## Section 2 — Connected (items wired up that should have been working)

### 2.1 Broken Import: `SquareSyncEngine` does not exist

- **Files:** `src/workers/tasks.py:39`, `src/workflows/nightly_analysis.py:24`
- **What's broken:** Both import `SquareSyncEngine` from `src.square.sync_engine`, but the actual class is named `SyncEngine`.
- **Fix:** Change import to `SyncEngine`. These files are already dead (Celery not used, see Section 6), but fixing for correctness.

### 2.2 Broken Method: `processor.is_duplicate()` does not exist

- **File:** `src/api/routes/webhooks.py:192`
- **What's broken:** Calls `await processor.is_duplicate(event_id)` but `WebhookProcessor` has no `is_duplicate` method. Will raise `AttributeError` at runtime when a Square webhook with an `event_id` arrives.
- **Fix:** Need to implement idempotency check or remove the call.

### 2.3 Path Mismatch: Spaces upload endpoint

- **Frontend:** `frontend/src/lib/spaces-service.ts:98` calls `/api/spaces/process`
- **Backend:** `src/api/routes/spaces.py:45` defines `POST /api/spaces/upload`
- **Neither works.** The paths don't match.

### 2.4 ruflo.config.yaml is missing 14 implemented agents

The config only lists 20 agents, but 27 agent files exist and are actively used by `engine.py`. The following should be added to `ruflo.config.yaml`:
- basket_analysis, cash_flow, cashflow_forecast, staffing, discount_analyzer
- category_mix, pricing_power, growth_score, seasonality, day_of_week
- waste_shrinkage, money_left, payment_optimizer, promo_roi

---

## Section 3 — Removed (items deleted as no longer needed)

### 3.1 Entire `app/` Directory — Complete Duplicate (~2,016 lines)

The `app/` directory is a parallel implementation of the Square integration that duplicates everything in `src/`. Only imported by the root `test_sandbox.py` (also dead). Every module in `app/` has a corresponding, more complete version in `src/`.

| File | Lines | Duplicates |
|------|-------|-----------|
| `app/services/square/client.py` | 264 | `src/square/client.py` |
| `app/services/square/oauth.py` | 193 | `src/square/oauth.py` |
| `app/services/square/mappers.py` | 383 | `src/square/mappers.py` |
| `app/services/square/rate_limiter.py` | 70 | `src/square/rate_limiter.py` |
| `app/services/square/sync_engine.py` | 365 | `src/square/sync_engine.py` |
| `app/services/square/webhook_handlers.py` | 243 | `src/square/webhook_handlers.py` |
| `app/api/square/callback.py` | 107 | `src/api/routes/oauth.py` |
| `app/api/square/webhook.py` | 104 | `src/api/routes/webhooks.py` |
| `app/workers/*` (3 files) | 287 | `src/workers/*` |

### 3.2 Root-Level Stale Files

| File | Lines | Why dead |
|------|-------|---------|
| `test_sandbox.py` | 401 | Stale copy; newer version at `src/tests/test_sandbox.py` |
| `test_results.json` | 169 | Generated test artifact, should not be in VCS |
| `research_square_api.py` | 21 | One-time research script, imports non-existent SDK |

### 3.3 Root-Level SQL Files — Superseded by `supabase/migrations/`

All 13 files use the old schema (`organizations`, `locations`, `users`) while the live DB uses `businesses`, `business_users`, `business_locations`. Never referenced by application code.

| File | Lines |
|------|-------|
| `000_SCHEMA_OVERVIEW.md` | 81 |
| `001_extensions_and_enums.sql` | 38 |
| `002_core_tables.sql` | 148 |
| `003_product_and_transaction_tables.sql` | 159 |
| `004_operations_tables.sql` | 137 |
| `005_intelligence_tables.sql` | 175 |
| `006_benchmark_and_warehouse.sql` | 125 |
| `007_continuous_aggregates.sql` | 119 |
| `008_rls_policies.sql` | 198 |
| `009_functions_and_triggers.sql` | 318 |
| `010_sales_rep_commissions.sql` | 214 |
| `00_cleanup.sql` | 10 |
| `grants.sql` | 87 |
| **Total** | **1,809** |

### 3.4 Orphaned Python Modules (never imported)

| File | Lines | Why dead |
|------|-------|---------|
| `src/vectorstore/qdrant_store.py` | 122 | Qdrant integration, zero imports outside dir |
| `src/streaming/producer.py` | 103 | Kafka/Redpanda producer, never imported |
| `src/streaming/consumer.py` | 81 | Kafka/Redpanda consumer, never imported |
| `src/observability/tracer.py` | 191 | Langfuse tracing decorators, never applied |
| `src/analytics/posthog_service.py` | 95 | PostHog tracking, never called |
| `src/serving/service.py` | 149 | BentoML serving layer, duplicates FastAPI routes |
| `src/documents/ocr_service.py` | 209 | PaddleOCR receipt parsing, never imported |

### 3.5 Orphaned Frontend Files

| File | Lines | Why dead |
|------|-------|---------|
| `frontend/src/pages/OnboardingPage.tsx` | 814 | Replaced by `CustomerOnboardingWizard` |
| `frontend/src/pages/PortalPage.tsx` | 283 | Replaced by `CustomerLoginPage`/`CustomerSignupPage` |
| `frontend/src/pages/sales/*` (11 files) | 2,260 | All `/sales/*` routes redirect via iframe |
| `frontend/src/components/PortalPOSPicker.tsx` | 326 | Replaced by `POSSystemPicker`/`POSSelectorPanel` |
| `frontend/src/components/SalesLayout.tsx` | 192 | Sales CRM is now an iframe |
| `frontend/src/components/SalesProtectedRoute.tsx` | 86 | Sales CRM is now an iframe |
| `frontend/src/components/ResponsiveLayout.tsx` | 229 | Never wired into app |
| `frontend/src/components/space/ScanControls.tsx` | 68 | `SpaceTab` uses `ScanWizard` instead |
| `frontend/src/hooks/useIsMobile.ts` | 46 | Only consumer was `ResponsiveLayout` (dead) |
| `frontend/src/lib/errorMonitor.ts` | 135 | Error batching system, never initialized |

### 3.6 Unused Python Imports (35 across 26 files)

| File | Unused Import |
|------|--------------|
| `services/phone_agent/llm_service.py` | `LLMMessagesFrame` |
| `services/phone_agent/order_router.py` | `smtplib`, `MIMEText`, `Optional` |
| `src/ai/agent_memory.py` | `Any` |
| `src/ai/economics/market_data.py` | `os` |
| `src/ai/scheduling/optimizer.py` | `Any` |
| `src/ai/swarm_trainer.py` | `os`, `timedelta`, `Any` |
| `src/api/routes/training.py` | `HTTPException` |
| `src/auth/manager.py` | `UUID`, `Depends` |
| `src/auth/models.py` | `EmailStr` |
| `src/auth/rbac.py` | `wraps` |
| `src/auth/router.py` | `require_role` |
| `src/camera/line_counter.py` | `field`, `np` |
| `src/camera/rtsp_handler.py` | `Any` |
| `src/data_quality/expectations.py` | `Any`, `gx` |
| `src/data_quality/runner.py` | `ExpectationSuite` |
| `src/documents/ocr_service.py` | `Optional` |
| `src/email/templates/payment_receipt.py` | `info_box` |
| `src/marketing/campaigns.py` | `Optional` |
| `src/streaming/producer.py` | `Any` |
| `src/tests/test_ai_engine.py` | `json`, `math`, `AnalysisResult` |
| `src/tests/test_sandbox.py` | `SyncResult` |
| `src/webhooks/delivery.py` | `Any` |
| `src/workers/tasks.py` | `logging`, `wraps` |
| `src/workflows/nightly_analysis.py` | `timedelta`, `task_input_hash` |
| `src/workflows/report_generator.py` | `asyncio` (inside function) |

### 3.7 Stale Tooling & Artifacts

| Item | Size | Why dead |
|------|------|---------|
| `tools/scraper/` (entire dir) | ~250 lines + 810 MB (.venv) | Crawl4AI scraper, crashed on first run, empty output |
| `.clinerules` | 112 lines | Config for Cline (not used; project uses Claude Code) |
| `__pycache__` dirs in edge/, storage/ | 36 KB | Build artifacts |

---

## Section 4 — Deferred (intentionally incomplete, left with TODO comment)

### 4.1 Agent Config Agents With No Implementation (8 agents)

These are in `ruflo.config.yaml` but have no corresponding `.py` file. Two are marked `priority: critical`.

| Config ID | Priority | Status |
|-----------|----------|--------|
| `retention-strategist` | medium | Planned — churn/winback analysis |
| `competitor-benchmarker` | low | Planned — industry comparison (partial overlap with `benchmark.py`) |
| `margin-optimizer` | high | Planned — margin leakage analysis |
| `loyalty-architect` | low | Planned — loyalty program design |
| `location-analyst` | low | Planned — multi-location comparison |
| `insight-narrator` | **critical** | Planned — plain-English agent summaries |
| `action-prioritizer` | **critical** | Planned — daily Top 3 Actions |
| `feature-engineer` | low | Planned — feature roadmap generation |

### 4.2 Vision Routes (ADR-011)

All 9 `/api/vision/*` routes are currently unreachable but are part of ADR-011 (In-Store Vision Intelligence). The edge device integration has not been completed. Leaving with TODO comments.

### 4.3 Predictive Routes

All 7 `/api/predictive/*` routes have backend implementations but no frontend consumers. These are planned features per the architecture.

### 4.4 Camera Module (`src/camera/`)

Scaffolded RTSP video pipeline (~400 lines). Part of ADR-011 vision system. Not yet integrated.

### 4.5 Marketing Module (`src/marketing/`)

Campaign triggers and email templates (~237 lines). Planned feature, not yet wired.

---

## Section 5 — Flagged for Aidan Pierce Decision

### 5.1 Celery Workers (`src/workers/celery_app.py` + `tasks.py`, 247 lines)

Celery tasks are defined but never started. The app uses FastAPI `BackgroundTasks` instead. The `tasks.py` also has the broken `SquareSyncEngine` import.
- **Decision needed:** Are you planning to move to Celery for production, or should these be removed?

### 5.2 `storage/` Module (842 lines across 7 files)

Only `r2_publisher` is imported (by `marketplace/webhook.py`). The other 6 files (`supabase_to_arrow.py`, `anonymizer.py`, `b2_uploader.py`, `iceberg_catalog.py`, `nightly_pipeline.py`, `quality_checks.py`) are unreachable.
- **Decision needed:** Is this a WIP data pipeline? Should it stay or be removed?

### 5.3 Payouts Routes (6 routes, entire `payouts.py`)

Sales rep commission/payout endpoints with no frontend consumer.
- **Decision needed:** Is the payout system still planned, or has it been superseded by the Convex-powered sales CRM?

### 5.4 `cash_flow.py` vs `cashflow_forecast.py` Overlap

Both agents compute day-of-week revenue averages and forecast future cash positions. ~80 lines of overlapping computation.
- **Decision needed:** Consolidate into one agent with configurable horizon?

### 5.5 Database Columns

Cannot audit without direct DB access. Recommend running:
```sql
-- Find tables with no queries
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name NOT IN (
  -- list tables referenced in codebase
);
```

---

## Section 6 — Could Not Resolve

### 6.1 `src/data_quality/` Module

Contains Great Expectations integration (`expectations.py`, `runner.py`). Imports `great_expectations` which is not in `requirements.txt`. May be planned or abandoned.

### 6.2 Frontend Demo Data Overlap

`demo-data.ts` (782 lines) and `demo-industries.ts` (1,786 lines) have structural overlap. `demo-industries.ts` provides per-business-type overrides that may shadow most of `demo-data.ts`. Runtime analysis needed to determine which exports are actually reached.

### 6.3 `Procfile` vs `Dockerfile`

Both start `uvicorn src.api.app:app`. If deploying exclusively via Docker, the Procfile is dead. If using Railway's native Procfile support, both are needed.

---

## SECURITY — Hardcoded Supabase Service Role Key

**CRITICAL:** `scripts/verify_supabase.py:10` contains a hardcoded Supabase `service_role` JWT. This key bypasses Row Level Security and has been committed to git history.

**Immediate actions required:**
1. Rotate the key in Supabase Dashboard → Settings → API
2. Remove or fix the script (replace with `os.environ["SUPABASE_SERVICE_KEY"]`)
3. Consider using `git filter-branch` or `BFG Repo-Cleaner` to remove the key from git history

---

## Unreachable API Routes — Full List (37 routes)

| Module | Route | Line |
|--------|-------|------|
| spaces.py | `POST /api/spaces/upload` | 45 |
| spaces.py | `GET /api/spaces/{org_id}` | 78 |
| spaces.py | `GET /api/spaces/{org_id}/{space_id}` | 88 |
| spaces.py | `PATCH /api/spaces/{space_id}/status` | 101 |
| spaces.py | `POST /api/spaces/{space_id}/zones` | 116 |
| training.py | `GET /api/training/status` | 24 |
| training.py | `GET /api/training/scorecards` | 31 |
| training.py | `POST /api/training/trigger` | 44 |
| training.py | `POST /api/training/signal` | 55 |
| predictive.py | `POST /api/predictive/scenario` | 70 |
| predictive.py | `GET /api/predictive/churn/{org_id}` | 84 |
| predictive.py | `GET /api/predictive/pricing/{org_id}` | 94 |
| predictive.py | `GET /api/predictive/demand/{org_id}` | 104 |
| predictive.py | `GET /api/predictive/goals/{org_id}` | 114 |
| predictive.py | `GET /api/predictive/root-cause/{org_id}` | 127 |
| predictive.py | `GET /api/predictive/alerts/{org_id}` | 141 |
| payouts.py | `GET /api/payouts/reps` | 36 |
| payouts.py | `GET /api/payouts/reps/{rep_id}/earnings` | 45 |
| payouts.py | `GET /api/payouts/reps/{rep_id}/commissions` | 59 |
| payouts.py | `POST /api/payouts/reps/{rep_id}/record-payout` | 69 |
| payouts.py | `GET /api/payouts/balances` | 92 |
| payouts.py | `GET /api/payouts/history` | 110 |
| vision.py | `GET /api/vision/cameras/{org_id}` | 87 |
| vision.py | `POST /api/vision/cameras` | 107 |
| vision.py | `PATCH /api/vision/cameras/{camera_id}` | 136 |
| vision.py | `DELETE /api/vision/cameras/{camera_id}` | 166 |
| vision.py | `POST /api/vision/cameras/{camera_id}/heartbeat` | 184 |
| vision.py | `POST /api/vision/ingest/traffic` | 210 |
| vision.py | `POST /api/vision/ingest/visits` | 245 |
| vision.py | `GET /api/vision/traffic/{org_id}` | 297 |
| vision.py | `GET /api/vision/agents/{org_id}` | 355 |
| billing.py | `POST /api/billing/cancel` | 133 |
| billing.py | `GET /api/billing/status/{org_id}` | 158 |
| billing.py | `POST /api/billing/check-trials` | 187 |
| onboarding.py | `POST /api/onboarding/create-account` | 48 |
| onboarding.py | `POST /api/onboarding/send-welcome` | 108 |
| cline.py | `GET /api/cline/conversations/{org_id}` | 127 |
| cline.py | `GET /api/cline/health/{org_id}` | 159 |
| cline.py | `GET /api/cline/errors/{org_id}` | 188 |
| careers.py | `POST /api/careers/apply` | 123 |
| admin.py | `POST /api/admin/create-rep` | 22 |
| dashboard.py | `POST /api/dashboard/cache/flush` | 647 |
| oauth.py | `GET /api/square/status` | 260 |
| webhooks.py | `GET /api/webhooks/square/health` | 242 |
| pos.py | `GET /api/pos/coverage` | 67 |

---

## Unused Environment Variables

| Variable | Status |
|----------|--------|
| `SQUARE_SANDBOX_BASE_URL` | Unused — never referenced in any source file |

All other `.env.example` variables are referenced in at least one source file.

---

## Frontend Duplicate Consolidation Opportunities

| Items | Estimated Savings |
|-------|------------------|
| `ScrollReveal` (2 copies) | ~45 lines |
| `DashboardTiltCard` / `TiltCard` | ~40 lines |
| `BentoGrid` / `CanadaBentoGrid` (95% identical) | ~145 lines |
| `LandingPage` / `CanadaLandingPage` structure | ~200 lines |
| `CareersPage` / `CanadaCareersPage` structure | ~150 lines |
| Stat card grid repeated across 10+ pages | ~250 lines |
