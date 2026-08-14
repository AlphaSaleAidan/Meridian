-- 080_phone_tables_rls_declared.sql
-- Declare in migrations/ what production already does: RLS on the two phone
-- tables that were locked down by a direct push instead of a migration.
--
-- WHAT WAS ACTUALLY WRONG. Production is fine — verified 2026-08-14:
-- phone_call_transcripts and phone_vocab_terms both have relrowsecurity = true,
-- zero policies, and no anon/authenticated SELECT. Nothing is exposed today.
-- The gap is that `migrations/` never said so, because RLS was enabled by hand
-- on the live database. So the repo and production disagreed, and **a fresh
-- environment rebuilt from migrations/ would have created both tables with no
-- RLS at all** — call transcripts being the most sensitive rows in the product.
--
-- That divergence is exactly what tests/compliance/test_cc6_1_rls_migrations.py
-- (SOC 2 CC6.1) exists to catch, and it did. It has been failing since the
-- phone-vocab work landed, and because Railway waits for CI, **every backend
-- deploy since 2026-08-12 was SKIPPED** — main and the live API silently
-- drifted apart for two days. Declaring the control here is what unblocks it.
--
-- Idempotent and a no-op against the live database (it already matches). Run
-- it anyway in every environment so the two can never drift again.
--
-- NOTE: written without IF EXISTS on purpose — 076 creates both tables earlier
-- in the ordered set, and the CC6.1 control matches the plain ALTER TABLE form
-- that every other migration here uses.

-- ═══════════════════════════════════════════════════════════════
-- phone_call_transcripts — recorded call text, the most sensitive
-- rows in the product. Service-role only.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_call_transcripts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON phone_call_transcripts FROM anon, authenticated;

-- ═══════════════════════════════════════════════════════════════
-- phone_vocab_terms — per-merchant vocabulary the agent learns.
-- Written server-side by the phone pipeline with the service-role
-- key, which bypasses RLS; no anon/authenticated path exists.
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_vocab_terms ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON phone_vocab_terms FROM anon, authenticated;

-- Explicit-deny posture (075 doctrine): RLS enabled with NO policy means no
-- anon/authenticated row is ever visible, while the service role continues to
-- read and write normally. Adding a policy here would loosen it, not tighten
-- it — so there deliberately isn't one.
