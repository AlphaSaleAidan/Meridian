-- P6 — pos_connections column renames (for-the-record migration).
--
-- These renames were applied to prod via the Supabase Management API at the
-- time the P6 code commit (3eeeeca5 in original off-main history) was authored.
-- That direct DDL was never captured as a tracked migration, so a fresh deploy
-- from this repo would have the OLD column shape while the code expects the
-- NEW shape — exactly the drift this reconciliation is closing.
--
-- This migration is IDEMPOTENT: against current prod (already renamed) it is a
-- complete no-op; against a fresh env from scratch it applies the renames in
-- the same shape prod has. Each rename is guarded by an information_schema
-- check that runs the ALTER only when the OLD column still exists.
--
-- Renames applied:
--   merchant_id              -> external_merchant_id
--   access_token_encrypted   -> access_token_enc
--   refresh_token_encrypted  -> refresh_token_enc
--   location_ids (text[])    -> external_location_id (text, singular)
--
-- The last one is a TYPE change (array → singular text). The information_schema
-- guard checks that the old `location_ids` array column still exists before
-- attempting the drop-and-add.

DO $$
BEGIN
  -- 1. merchant_id -> external_merchant_id
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pos_connections'
      AND column_name = 'merchant_id'
  ) THEN
    ALTER TABLE public.pos_connections RENAME COLUMN merchant_id TO external_merchant_id;
  END IF;

  -- 2. access_token_encrypted -> access_token_enc
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pos_connections'
      AND column_name = 'access_token_encrypted'
  ) THEN
    ALTER TABLE public.pos_connections RENAME COLUMN access_token_encrypted TO access_token_enc;
  END IF;

  -- 3. refresh_token_encrypted -> refresh_token_enc
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pos_connections'
      AND column_name = 'refresh_token_encrypted'
  ) THEN
    ALTER TABLE public.pos_connections RENAME COLUMN refresh_token_encrypted TO refresh_token_enc;
  END IF;

  -- 4. location_ids (text[]) -> external_location_id (text)
  --    Only act if the OLD array column still exists AND the NEW singular
  --    column doesn't, so a partial prior state can't get clobbered.
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pos_connections'
      AND column_name = 'location_ids'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pos_connections'
      AND column_name = 'external_location_id'
  ) THEN
    ALTER TABLE public.pos_connections ADD COLUMN external_location_id TEXT;
    -- Best-effort migration of existing data: take the first array element if
    -- the array has values. If the existing row uses different semantics, the
    -- application is expected to backfill — this preserves at least one ID per row.
    UPDATE public.pos_connections
       SET external_location_id = location_ids[1]
     WHERE array_length(location_ids, 1) >= 1
       AND external_location_id IS NULL;
    ALTER TABLE public.pos_connections DROP COLUMN location_ids;
  END IF;
END $$;
