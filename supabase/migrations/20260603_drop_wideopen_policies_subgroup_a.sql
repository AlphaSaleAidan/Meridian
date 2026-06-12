-- Migration: drop wide-open RLS "Service role full access" policies (Tier 1, Subgroup A)
-- Date:      2026-06-03
--
-- Drops 3 RLS policies whose USING clause is `(true)`. service_role bypasses
-- RLS regardless of any policy, so these policies are redundant for the
-- backend service path. But `USING (true)` ALSO matches any authenticated
-- request via PostgREST + anon key, which is the live authz hole this closes.
--
-- LIVE DB CONFIRMATION (via pg_policies on kbuzufjxwflrutowwnfl, 2026-06-03):
-- All three target policies are present with EXACTLY:
--   cmd:        ALL
--   roles:      {public}
--   using:      true
--   with_check: true
-- The rollback CREATE POLICY statements in the PR description reproduce
-- this exactly (no `TO` clause defaults to PUBLIC, matching roles={public}).
--
-- BACKEND PATHS (all SUPABASE_SERVICE_ROLE_KEY → RLS bypassed):
--   merchant_credits  ← src/credits/service.py
--   credit_ledger     ← src/credits/service.py + src/api/routes/credits.py
--   credit_purchases  ← src/credits/purchase.py
--
-- FRONTEND DIRECT ACCESS (anon/authenticated via supabase-js): NONE.
--
-- NOTE: canada_career_applications was originally in scope, but a pg_class
-- check confirmed the table does NOT exist in the live DB
-- (kbuzufjxwflrutowwnfl). The original 20260505_canada_careers.sql
-- migration appears to declare a table that was never created or was
-- dropped later. Removed from this migration; filed as a separate
-- investigation follow-up.
--
-- PRECONDITION: SUPABASE_SERVICE_ROLE_KEY (or _SERVICE_KEY) MUST be set
-- non-empty in the Railway backend env before applying. credits/*.py
-- silently fall back to anon if no service key is set — applying this
-- migration in that misconfigured state would lock the backend out.

BEGIN;

DROP POLICY IF EXISTS "Service role full access on merchant_credits" ON merchant_credits;
DROP POLICY IF EXISTS "Service role full access on credit_ledger" ON credit_ledger;
DROP POLICY IF EXISTS "Service role full access on credit_purchases" ON credit_purchases;

COMMIT;
