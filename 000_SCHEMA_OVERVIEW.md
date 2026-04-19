# Meridian Database Schema — Complete Overview

## Architecture

Built for **Supabase (PostgreSQL 15+)** with **TimescaleDB** extension for time-series data.

## File Structure

| File | Contents |
|------|----------|
| `001_extensions_and_enums.sql` | Extensions (uuid, pgcrypto, timescaledb) + all enum types |
| `002_core_tables.sql` | Organizations, Locations, Users, Subscriptions, POS Connections |
| `003_product_and_transaction_tables.sql` | Products, Categories, Transactions (hypertable), Transaction Items (hypertable), Inventory |
| `004_operations_tables.sql` | Suppliers, Scheduled Events, Notifications, Notification Rules |
| `005_intelligence_tables.sql` | AI Insights, Money Left Scores, Forecasts, Chat History, Weekly Reports |
| `006_benchmark_and_warehouse.sql` | Benchmark Profiles, Benchmark Snapshots, Industry Aggregates (THE DATA ASSET), Export Logs |
| `007_continuous_aggregates.sql` | TimescaleDB continuous aggregates: hourly, daily, weekly revenue + daily product performance |
| `008_rls_policies.sql` | Row-Level Security policies for complete data isolation between merchants |
| `009_functions_and_triggers.sql` | Utility functions, dashboard queries, onboarding flow, compression policies |

## Table Count: 24 tables + 4 continuous aggregates

### Core (5 tables)
- `organizations` — The merchant business
- `locations` — Multi-location support (Tier 3)
- `users` — Team members linked to Supabase Auth
- `subscriptions` — Stripe billing state
- `pos_connections` — OAuth connections to POS systems

### Product & Transactions (5 tables, 3 hypertables)
- `product_categories` — Hierarchical categories
- `products` — Product catalog with AI scoring
- `transactions` ⏱️ — Every sale/refund/void (hypertable)
- `transaction_items` ⏱️ — Line items per transaction (hypertable)
- `inventory_snapshots` ⏱️ — Daily inventory tracking (hypertable)

### Operations (4 tables)
- `suppliers` — Vendor directory
- `scheduled_events` — Deliveries, inspections, meetings
- `notifications` — SMS/email/push delivery tracking
- `notification_rules` — Custom alert routing

### Intelligence (5 tables, 2 hypertables)
- `insights` — AI-generated recommendations
- `money_left_scores` ⏱️ — Daily "money left on table" tracking (hypertable)
- `forecasts` ⏱️ — Revenue/demand predictions (hypertable)
- `chat_conversations` — AI advisor conversation threads
- `chat_messages` — Individual chat messages
- `weekly_reports` — Pre-computed weekly snapshots

### Benchmarking & Data Warehouse (4 tables, 2 hypertables)
- `benchmark_profiles` — Anonymized merchant classification
- `benchmark_snapshots` ⏱️ — Weekly anonymized KPIs (hypertable)
- `industry_aggregates` ⏱️ — Fully anonymized industry data (hypertable) — **THE SELLABLE ASSET**
- `data_export_logs` — Track data licensing/exports

### Continuous Aggregates (4 views)
- `hourly_revenue` — Powers heatmaps and peak hour analysis
- `daily_revenue` — Powers daily dashboard
- `daily_product_performance` — Powers product scorecards
- `weekly_revenue` — Powers weekly trend analysis

## Key Design Decisions

1. **TimescaleDB Hypertables** for all time-series data (transactions, inventory, scores, forecasts). This gives us 10-100x faster queries on time-range data and automatic data compression.

2. **Row-Level Security** on every merchant table. Data isolation is enforced at the database level — even if application code has a bug, one merchant can never see another's data.

3. **Continuous Aggregates** pre-compute hourly/daily/weekly rollups automatically. Dashboard queries hit pre-computed data instead of scanning millions of rows.

4. **Compression Policies** automatically compress data older than 6 months, reducing storage costs by 90%+ while keeping it queryable.

5. **Anonymized Data Warehouse** is a separate layer from merchant data. The ETL pipeline strips all identifying information before aggregating into `industry_aggregates`. This is the sellable asset.

6. **All money stored in cents** (INTEGER) to avoid floating-point precision issues.

7. **JSONB for flexible fields** (business hours, report data, AI recommendations) — gives us schema flexibility where we need it while keeping core fields strictly typed.

## Deployment Order

Run the SQL files in order (001 → 009). Each file is idempotent where possible.
