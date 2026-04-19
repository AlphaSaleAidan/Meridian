# Meridian

AI-powered POS analytics platform for independent business owners.

## What It Does
Connects to existing POS systems (Square, Toast, Clover) and delivers:
- **Actionable recommendations** (not just charts)
- **"Money Left on the Table" score** — single headline metric
- **Predictive revenue forecasting**
- **Delivery/event schedule management** with smart notifications
- **Anonymous benchmarking** across similar businesses

## Pricing
| Plan | Price/mo | Features |
|------|----------|----------|
| Insights | $500 | Core analytics + recommendations |
| Optimize | $750 | + Forecasting + notifications |
| Command | $1,000 | + Benchmarking + what-if simulator |

## Architecture
```
Square OAuth → Sync Engine → Supabase → AI Engine → Dashboard
                (backfill + incremental + webhooks)
```

## Key Components
- **Database**: 24 tables, 4 materialized views, 21 RLS policies, 9 functions (Supabase)
- **Square Integration**: OAuth, sync engine (18mo backfill + 15min incremental + webhooks), rate limiter
- **AI Engine**: Revenue Analyzer, Product Intelligence, Pattern Detection, Money Left on Table, Forecasting, Weekly Reports
- **Backend**: FastAPI application with full pipeline orchestration

## Project Structure
```
├── src/                    # Modular source code
│   ├── ai/                 # AI analysis engines
│   ├── api/                # FastAPI application
│   ├── db/                 # Database clients + queries
│   ├── square/             # Square POS integration
│   ├── tests/              # Test suites
│   └── workers/            # Background workers
├── app/                    # Application services
├── scripts/                # Pipeline + verification scripts
├── 001-009_*.sql           # Database migrations
├── meridian_backend_complete.py   # Combined backend (8,954 lines)
├── ai_engine_combined.py          # Combined AI engine (4,443 lines)
└── meridian_supabase_migration.sql # Full DB schema (1,441 lines)
```

## Status
- ✅ Database schema deployed to Supabase
- ✅ Square integration tested (32/32 sandbox tests)
- ✅ AI insights engine operational
- ✅ Live pipeline: Square → Supabase → AI (1,000 txns tested)
- 🚧 Frontend polish
- 🚧 Toast + Clover integrations
- 🚧 Notification system (Twilio + SendGrid)
- 🚧 What-If Simulator
- 🚧 Anonymous benchmarking
