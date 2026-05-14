# src/db/ — Database Layer

Primary client: `supabase_rest.py` (async REST client for Supabase)
Cache: `cache.py` (Redis-backed TTL, falls back to in-memory)
Connection: `__init__.py` exports `init_db()`, `close_db()`, `_db_instance`

## Tables (24 total)
Core: organizations, locations, users, subscriptions, pos_connections
Transactions: products, categories, transactions (hypertable), transaction_items (hypertable)
Intelligence: insights, money_left_scores, forecasts, weekly_reports
Operations: notifications, notification_rules, scheduled_events

## Rules
- All money in cents (integer)
- All tables have RLS
- Always scope by org_id/business_id
