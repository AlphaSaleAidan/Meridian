-- POS metadata → queryable columns — part of the coordinated core-flows deploy
-- =====================================================================
-- The digest upgrades write tenders / refunds / service charges / device into
-- transactions.metadata (JSONB) so they ship with NO migration. This promotes
-- them to first-class columns for querying/indexing, WITHOUT a code change:
-- they're GENERATED ALWAYS columns derived from metadata, so the mappers keep
-- writing metadata and these stay in sync automatically.
--
-- ⚠️ VALIDATE BEFORE APPLYING (live schema not in repo):
--   • Confirm transactions.metadata is JSONB (if JSON, cast or change ->/->>).
--   • Run this BEFORE the per-provider phase-1 migration so the
--     `CREATE TABLE … (LIKE transactions INCLUDING ALL)` copies these columns
--     into square_/clover_/toast_transactions. If phase-1 already ran, repeat
--     the ADD COLUMNs on each provider table.
--   • Casts use nullif(...,'')::int to tolerate absent/empty values; verify no
--     non-numeric values exist in those metadata keys first.
-- Additive + idempotent (IF NOT EXISTS). No data is rewritten.
-- =====================================================================

begin;

alter table public.transactions
    add column if not exists tenders jsonb
        generated always as (metadata -> 'tenders') stored,
    add column if not exists refund_cents integer
        generated always as (nullif(metadata ->> 'refund_cents', '')::int) stored,
    add column if not exists service_charge_cents integer
        generated always as (nullif(metadata ->> 'service_charge_cents', '')::int) stored,
    add column if not exists device_id text
        generated always as (metadata ->> 'device_id') stored;

-- Helpful indexes for the new columns (optional; uncomment if queried often).
-- create index if not exists idx_transactions_device_id on public.transactions (org_id, device_id) where device_id is not null;
-- create index if not exists idx_transactions_refund on public.transactions (org_id) where refund_cents is not null;

commit;
