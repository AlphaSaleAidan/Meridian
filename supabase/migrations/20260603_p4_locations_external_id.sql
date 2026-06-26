-- ============================================================
-- Migration: P4 — locations.external_id + matching unique indexes
-- Date:      2026-06-03
-- Applied:   2026-06-03 via Supabase Management API
--            (statement-by-statement; mgmt API does not batch DDL)
-- ============================================================
--
-- Purpose
-- -------
-- Close the schema/code mismatch surfaced by the P3 e2e backfill
-- test. The Square + Clover mappers carry a source-POS row id
-- (`external_id`) for every record, and the existing
-- _run_*_backfill helpers all use `on_conflict="org_id,external_id"`
-- when batch-upserting. But:
--   1. `locations` had no `external_id` column at all → PostgREST
--      returned `column "external_id" does not exist` and aborted
--      the whole backfill chain on the very first upsert.
--   2. `products` and `transactions` had the column but no UNIQUE
--      index on (org_id, external_id) → PostgREST returned
--      `42P10 there is no unique or exclusion constraint matching
--      the ON CONFLICT specification` on the next upsert.
--
-- After this migration:
--   * `locations` has a nullable `external_id TEXT` column.
--   * All three tables have a non-partial unique index on
--     (org_id, external_id).
--   * The sync engines' on_conflict spec resolves cleanly and
--     the full chain (locations → products → transactions →
--     transaction_items) can complete.
--   * Re-runs are idempotent on (org_id, external_id).
--
-- Why non-partial unique indexes (not partial WHERE external_id IS
-- NOT NULL)?
-- ----------------------------------------------------------------
-- Postgres allows partial unique indexes to be used by ON CONFLICT
-- only if the INSERT statement repeats the partial predicate in
-- its ON CONFLICT clause. PostgREST's upsert API does not expose
-- that — it sends a bare `ON CONFLICT (org_id, external_id)`. So
-- partial indexes return error 42P10 in this code path. A non-
-- partial unique index is safe here because Postgres treats each
-- NULL value as distinct in unique-index comparisons by default:
-- the one pre-P4 `locations` row with NULL external_id continues
-- to coexist with the new non-NULL rows the sync engines insert,
-- and any future legacy or manually-created row with NULL
-- external_id is also fine.
--
-- Rollback
-- --------
-- Documented at the bottom of the file (commented out).
-- ============================================================


-- ─── 1. locations.external_id column ─────────────────────────
-- Nullable so manually-created locations (no upstream POS link)
-- coexist with sync'd rows. TEXT matches the source providers:
-- Square gives a base-36 id, Clover gives a merchant id, Toast
-- gives a guid; all fit TEXT.
ALTER TABLE locations
    ADD COLUMN IF NOT EXISTS external_id TEXT;


-- ─── 2. Unique indexes for the upsert key ────────────────────
-- Non-partial unique indexes on (org_id, external_id) for all
-- three sync-engine destination tables. See header note for why
-- non-partial.
--
-- Rows with NULL external_id are still allowed (Postgres treats
-- NULL = NULL as NULL → unique-index comparisons don't collide
-- on NULL pairs). Counts at migration time:
--   locations:    2 rows total · 1 NULL · 1 with external_id
--   products:     4 rows total · 0 NULL · 4 with external_id
--   transactions: 3 rows total · 0 NULL · 3 with external_id
CREATE UNIQUE INDEX IF NOT EXISTS uq_locations_org_external_id
    ON locations (org_id, external_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_org_external_id
    ON products (org_id, external_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_org_external_id
    ON transactions (org_id, external_id);


-- ─── 3. Self-documenting comment on the new column ───────────
COMMENT ON COLUMN locations.external_id IS
    'Source-POS location identifier (Square location.id, '
    'Clover merchant.id, Toast restaurant.guid). Nullable for '
    'manually-created locations. Populated by the canonical sync '
    'engines on ingest. (org_id, external_id) is the upsert '
    'idempotency key.';


-- ============================================================
-- ROLLBACK START — uncomment + run to undo:
--
-- DROP INDEX IF EXISTS uq_transactions_org_external_id;
-- DROP INDEX IF EXISTS uq_products_org_external_id;
-- DROP INDEX IF EXISTS uq_locations_org_external_id;
-- ALTER TABLE locations DROP COLUMN IF EXISTS external_id;
--
-- ROLLBACK END
-- ============================================================
