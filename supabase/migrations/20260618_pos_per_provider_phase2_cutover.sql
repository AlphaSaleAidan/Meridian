-- POS per-provider tables — PHASE 2 (cutover)
-- =====================================================================
-- Apply this TOGETHER with the Phase 2 code (which sets POS_PER_PROVIDER_TABLES=1):
-- the app then writes per-provider tables and reads the `transactions` view below.
--
-- Prereq: Phase 1 migration applied (provider tables exist + populated).
-- Ordering is deliberate: re-copy → dedupe ITEMS before TRANSACTIONS (the item
-- join needs the still-present parent rows) → rename → views.
-- =====================================================================

BEGIN;

-- 1. Catch rows added since Phase 1 (idempotent) ------------------------
INSERT INTO public.square_transactions SELECT t.* FROM public.transactions t
  JOIN public.pos_connections c ON c.id = t.pos_connection_id WHERE c.provider = 'square' ON CONFLICT DO NOTHING;
INSERT INTO public.clover_transactions SELECT t.* FROM public.transactions t
  JOIN public.pos_connections c ON c.id = t.pos_connection_id WHERE c.provider = 'clover' ON CONFLICT DO NOTHING;
INSERT INTO public.toast_transactions  SELECT t.* FROM public.transactions t
  JOIN public.pos_connections c ON c.id = t.pos_connection_id WHERE c.provider = 'toast'  ON CONFLICT DO NOTHING;

INSERT INTO public.square_transaction_items SELECT ti.* FROM public.transaction_items ti
  JOIN public.transactions t ON t.id = ti.transaction_id
  JOIN public.pos_connections c ON c.id = t.pos_connection_id WHERE c.provider = 'square' ON CONFLICT DO NOTHING;
INSERT INTO public.clover_transaction_items SELECT ti.* FROM public.transaction_items ti
  JOIN public.transactions t ON t.id = ti.transaction_id
  JOIN public.pos_connections c ON c.id = t.pos_connection_id WHERE c.provider = 'clover' ON CONFLICT DO NOTHING;
INSERT INTO public.toast_transaction_items  SELECT ti.* FROM public.transaction_items ti
  JOIN public.transactions t ON t.id = ti.transaction_id
  JOIN public.pos_connections c ON c.id = t.pos_connection_id WHERE c.provider = 'toast'  ON CONFLICT DO NOTHING;

-- 2. Dedupe base so the UNION (provider tables + legacy) has no duplicates.
--    Items first — their join needs the still-present parent transactions.
DELETE FROM public.transaction_items ti
  USING public.transactions t, public.pos_connections c
  WHERE t.id = ti.transaction_id AND c.id = t.pos_connection_id
    AND c.provider IN ('square', 'clover', 'toast');
DELETE FROM public.transactions t
  USING public.pos_connections c
  WHERE c.id = t.pos_connection_id
    AND c.provider IN ('square', 'clover', 'toast');

-- 3. Rename the now-orphan-only base tables out of the way ---------------
ALTER TABLE public.transactions      RENAME TO transactions_legacy;
ALTER TABLE public.transaction_items RENAME TO transaction_items_legacy;

-- 4. Read-only UNION views the app reads (security_invoker so underlying
--    RLS applies to authenticated readers; service-role reads bypass RLS).
CREATE VIEW public.transactions WITH (security_invoker = true) AS
  SELECT * FROM public.square_transactions
  UNION ALL SELECT * FROM public.clover_transactions
  UNION ALL SELECT * FROM public.toast_transactions
  UNION ALL SELECT * FROM public.transactions_legacy;

CREATE VIEW public.transaction_items WITH (security_invoker = true) AS
  SELECT * FROM public.square_transaction_items
  UNION ALL SELECT * FROM public.clover_transaction_items
  UNION ALL SELECT * FROM public.toast_transaction_items
  UNION ALL SELECT * FROM public.transaction_items_legacy;

COMMIT;

-- 5. RLS read policies — mirror transactions_legacy's authenticated SELECT
--    policy onto each provider table BEFORE flipping to authenticated reads.
--    (Provider tables already have RLS enabled from Phase 1. Verify the exact
--    legacy policy in Supabase; the org-scoped shape is typically:)
--
--    CREATE POLICY pos_read ON public.square_transactions FOR SELECT TO authenticated
--      USING (org_id IN (SELECT org_id FROM business_users WHERE user_id = auth.uid()));
--    -- repeat for clover_/toast_ transactions and *_transaction_items
--
-- Rollback:
--   DROP VIEW public.transactions, public.transaction_items;
--   ALTER TABLE public.transactions_legacy      RENAME TO transactions;
--   ALTER TABLE public.transaction_items_legacy RENAME TO transaction_items;
--   -- then, if needed, copy provider-table rows back into the base tables.
