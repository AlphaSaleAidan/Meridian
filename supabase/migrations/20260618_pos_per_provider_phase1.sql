-- POS per-provider tables — PHASE 1 (additive, zero production impact)
-- =====================================================================
-- Goal (Option C): each POS system gets its own canonical table so ingestion
-- paths can never overwrite each other, with a read-only `transactions` UNION
-- view introduced at cutover. This migration is PHASE 1 only:
--
--   • creates square_/clover_/toast_ copies of transactions + transaction_items
--     using LIKE ... INCLUDING ALL (mirrors the live schema exactly — columns,
--     types, defaults, NOT NULLs, indexes, the (org_id, external_id) unique key),
--   • copies existing rows into the right provider table, routed by
--     pos_connections.provider,
--   • enables RLS (service-role ingestion still writes; nothing reads these yet).
--
-- It does NOT touch the live `transactions` / `transaction_items` tables, so the
-- running app is unaffected. Safe to apply anytime; safe to re-run (idempotent).
--
-- PHASE 2 (cutover — separate, coordinated PR, applied WITH the code rewire):
--   1. rewire writes (backfill / incremental_sync / webhooks / pos_sync_runner)
--      to target the provider table for their provider,
--   2. ALTER TABLE transactions RENAME TO transactions_legacy (same for items),
--   3. CREATE VIEW transactions AS SELECT * FROM square_transactions
--        UNION ALL clover_transactions UNION ALL toast_transactions (+ legacy),
--   4. mirror the authenticated-read RLS policy from transactions_legacy onto
--      each provider table.
--   The view cannot accept ON CONFLICT upserts, which is why the write rewire
--   (step 1) must ship in the same change as the rename (step 2).
-- =====================================================================

BEGIN;

-- ── transactions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.square_transactions (LIKE public.transactions INCLUDING ALL);
CREATE TABLE IF NOT EXISTS public.clover_transactions (LIKE public.transactions INCLUDING ALL);
CREATE TABLE IF NOT EXISTS public.toast_transactions  (LIKE public.transactions INCLUDING ALL);

ALTER TABLE public.square_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clover_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.toast_transactions  ENABLE ROW LEVEL SECURITY;

INSERT INTO public.square_transactions
  SELECT t.* FROM public.transactions t
  JOIN public.pos_connections c ON c.id = t.pos_connection_id
  WHERE c.provider = 'square'
  ON CONFLICT DO NOTHING;

INSERT INTO public.clover_transactions
  SELECT t.* FROM public.transactions t
  JOIN public.pos_connections c ON c.id = t.pos_connection_id
  WHERE c.provider = 'clover'
  ON CONFLICT DO NOTHING;

INSERT INTO public.toast_transactions
  SELECT t.* FROM public.transactions t
  JOIN public.pos_connections c ON c.id = t.pos_connection_id
  WHERE c.provider = 'toast'
  ON CONFLICT DO NOTHING;

-- ── transaction_items (routed via its parent transaction's connection) ──
CREATE TABLE IF NOT EXISTS public.square_transaction_items (LIKE public.transaction_items INCLUDING ALL);
CREATE TABLE IF NOT EXISTS public.clover_transaction_items (LIKE public.transaction_items INCLUDING ALL);
CREATE TABLE IF NOT EXISTS public.toast_transaction_items  (LIKE public.transaction_items INCLUDING ALL);

ALTER TABLE public.square_transaction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clover_transaction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.toast_transaction_items  ENABLE ROW LEVEL SECURITY;

INSERT INTO public.square_transaction_items
  SELECT ti.* FROM public.transaction_items ti
  JOIN public.transactions t ON t.id = ti.transaction_id
  JOIN public.pos_connections c ON c.id = t.pos_connection_id
  WHERE c.provider = 'square'
  ON CONFLICT DO NOTHING;

INSERT INTO public.clover_transaction_items
  SELECT ti.* FROM public.transaction_items ti
  JOIN public.transactions t ON t.id = ti.transaction_id
  JOIN public.pos_connections c ON c.id = t.pos_connection_id
  WHERE c.provider = 'clover'
  ON CONFLICT DO NOTHING;

INSERT INTO public.toast_transaction_items
  SELECT ti.* FROM public.transaction_items ti
  JOIN public.transactions t ON t.id = ti.transaction_id
  JOIN public.pos_connections c ON c.id = t.pos_connection_id
  WHERE c.provider = 'toast'
  ON CONFLICT DO NOTHING;

COMMIT;

-- Rollback (Phase 1 is fully reversible — these tables are not yet referenced):
--   DROP TABLE IF EXISTS public.square_transactions, public.clover_transactions,
--     public.toast_transactions, public.square_transaction_items,
--     public.clover_transaction_items, public.toast_transaction_items;
