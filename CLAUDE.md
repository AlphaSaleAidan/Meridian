# Meridian Intelligence Platform

> AI-powered POS analytics for independent businesses (restaurants, smoke shops, cafes, retail).
> FastAPI + React/Vite + Supabase + Square/Clover/Toast + Celery/Redis

## Runtime

| Service | Location | Runtime |
|---------|----------|---------|
| API | `src/api/app.py` :8000 | pm2 `meridian-api` |
| Frontend | `frontend/` | Vercel (meridian.tips) |
| Workers | `src/workers/` | pm2 `celery-worker` + `celery-beat` |
| Scraper | `scripts/scraper-daemon.py` | pm2 `scraper` |
| DeerFlow | :8001 | pm2 `deerflow` |
| DB | Supabase (kbuzufjxwflrutowwnfl) | hosted |
| Cache | Redis :6379 | systemd |
| Local LLM | `data/models/` Llama 3.1 8B | loaded on-demand |

Server: 209.126.80.45 (AMD EPYC 12c, 48GB RAM, 484GB disk)

## Key IDs

- Canada org: `168b6df2-e9af-4b00-8fec-51e51149ff19`
- Square location: `LY1VJBWJ2J13J`
- Admin phone: +19495067494

## Backend Map (`src/`)

**API Routes** (`src/api/routes/`): dashboard (703L), onboarding (525L), pos_connections (505L), billing (478L), vision (439L), canada (371L), phone (364L), cline (280L), oauth (275L), webhooks (249L), predictive (204L), email (190L), inference (93L), careers (143L), admin (56L)

**AI** (`src/ai/`): engine.py (main orchestrator), llm_layer.py (OpenAI wrapper), swarm_trainer.py, reasoning/karpathy_loop.py, agents/ (30+ agents inheriting base.py), analyzers/ (patterns, products, revenue, money_left), predictive/ (churn, demand, pricing, scenarios, goals, root_cause), generators/ (insights, forecasts, reports)

**DB** (`src/db/`): supabase_rest.py (main client), cache.py (Redis TTL), queries.py, repos/ (sync, query, persist)

**POS**: square/ (client, mappers, oauth, sync_engine, webhooks), clover/ (same structure), toast/ (same), services/pos_connectors/ (universal framework, registry 1206L)

**Workers** (`src/workers/`): tasks.py (sync, analysis, swarm training, burn rate, vector ingestion, batch inference), celery_app.py (beat schedules)

**Inference** (`src/inference/`): local_llm.py (llama-cpp CPU), router.py (batch→local, realtime→OpenAI), embeddings.py (sentence-transformers + SQLite vectors)

**Other**: email/ (Postal+Resend, 14 templates), sms/client.py (Telnyx+Twilio), billing/billing_service.py, auth/ (Supabase JWT, RBAC), analytics/burn_rate.py, cline/ (self-healing agent)

## Frontend Map (`frontend/src/`)

**Pages**: pages/canada/portal/ (15 Canada sales portal pages), pages/customer/ (onboarding wizard), pages/sales/ (rep tools), pages/admin/, InsightsPage.tsx (with 2hr cooldown)

**Components**: GarryWidget.tsx (AI chat), POSSystemPicker.tsx (80 POS systems), landing/, vision/, ui/ (shadcn)

**Hooks**: useOrg.ts (CRITICAL: isDemoPath logic — demo only on /demo and /canada/demo), useApi.ts, useInsightsCooldown.ts

**Lib**: demo-data.ts, demo-industries.ts, agent-data.ts, pos-systems.ts (4492L), auth.tsx, supabase.ts

## Common Tasks

- **Add API endpoint**: Create in `src/api/routes/`, import+include_router in `src/api/app.py`
- **Add Celery task**: Define in `src/workers/tasks.py`, add route+beat in `celery_app.py`
- **Add AI agent**: Inherit `src/ai/agents/base.py:BaseAgent`, register in `__init__.py`
- **Add email template**: Create in `src/email/templates/`, use base.py helpers
- **Restart**: `pm2 restart meridian-api celery-worker celery-beat --update-env`
- **Build check**: `cd frontend && npm run build`

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
- Library docs are in `docs/library-skills.md` — only read when working on those integrations
