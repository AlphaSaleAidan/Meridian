# Meridian

AI-powered POS analytics platform for independent business owners (restaurants, cafes, retail, smoke shops, auto shops, dispensaries). Two intentionally distinct products: the **US portal** and the **Canada portal** (rep-driven concierge sales motion).

## What It Does

Connects to existing POS systems and delivers:
- **Top Actions / actionable recommendations** (not just charts)
- **"Money Left on the Table" score** — single headline metric
- **Predictive revenue forecasting**, anomaly detection, menu engineering
- **AI phone ordering agent** (Telnyx, turn-based) routing orders to the merchant's connected POS
- **Schedule management** built from real staffing/peak-hours data
- **Anonymous benchmarking** across similar businesses

## Stack

FastAPI + React/Vite/TypeScript + Supabase + Celery/Redis + a 48-agent AI swarm (Karpathy 5-phase reasoning, tiered LLM routing).

```
POS OAuth (Square live, Clover live, Toast pending)
   → Sync Engine (backfill + 15-min incremental + webhooks)
   → Supabase → AI Engine (48 agents) → Dashboards / Phone agent / SMS
```

## Hosting (the part everyone gets wrong)

| Surface | Where | Deploys how |
|---------|-------|-------------|
| `api.meridian.tips` (backend) | Railway | **Auto from `main` on merge** — never merge without review |
| `meridian.tips` (frontend) | Contabo VPS, nginx static `frontend/dist` | **Manual**, only from the canonical tag — see `docs/30-operations/frontend-deploy.md` |
| Database | Supabase | migrations in `supabase/migrations/` + `migrations/` |
| Workers, phone agent, scraper | Contabo VPS, PM2 | `ecosystem.config.js` |

## Project Structure

```
├── src/
│   ├── ai/                 # 41-agent swarm, predictive, generators, analyzers
│   ├── api/                # FastAPI app + 36 route modules (auth deps documented in CLAUDE.md)
│   ├── db/                 # Supabase REST client, Redis cache
│   ├── square/ clover/ toast/   # POS integrations (client, mappers, sync engine, webhooks)
│   └── workers/            # Celery: sync, backfill, token refresh, swarm training
├── services/
│   ├── phone_agent/        # Telnyx turn-based AI phone ordering
│   └── deerflow/ postal/ … # Supporting services
├── frontend/               # React/Vite SPA — US + Canada portals
├── docs/                   # Organized docs — start at docs/known_issues.md for open debt
└── supabase/migrations/    # Database migrations
```

## Current Status (2026-06-12)

- ✅ Backend audit shipped (PRs #86–#89): webhooks, auth hardening, swarm training loop
- ✅ Square + Clover integrations live; Toast pending partner approval
- ✅ Phone agent live-call-tested (turn-based Telnyx path)
- ✅ Rep-driven customer provisioning with forced first-login reset (PR #91)
- 🚧 POS beta pipeline (PR #94) — **gated on first real-merchant connection test** (synthetic-only so far)
- 🚧 Canada canonical portal formalization (PR #90)
- 🚧 Rep commission structure — intentionally unbuilt while the pay model is designed

Open technical debt: `docs/known_issues.md`. Agent docs: `AGENTS.md`. Operating rules and architecture map: `CLAUDE.md`.
