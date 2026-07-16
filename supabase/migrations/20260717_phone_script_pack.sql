-- 20260717_phone_script_pack.sql
-- Per-merchant call-script pack selection for the phone agent.
--
-- The live agent runs one generic system prompt for every merchant. Script
-- packs (services/phone_agent/script_packs.py) are named, versioned,
-- per-vertical variants of the CALL FLOW, tuned for the 5-minute hard call
-- cap. Selection is strictly opt-in:
--
--   script_pack NULL / '' / 'legacy' / any unknown value
--     → the untouched generic prompt, byte-for-byte (fail-legacy resolution
--       in vapi_webhook._resolve_script_pack; golden-snapshot tests in
--       tests/api/test_script_packs.py). Known ids: efficient_v1,
--       pizzeria_v1, cafe_quickserve_v1, indian_v1. Free text (not
--       constrained) so packs can ship without a migration; unknown values
--       are harmless by construction.
--
-- business_type already exists on the base table (20260507_phone_agent.sql,
-- NOT NULL DEFAULT 'restaurant'); it is re-declared here purely as a safety
-- net for environments predating it (matches the 032 pattern). It informs
-- the UI's pack RECOMMENDATION only — it never auto-selects a pack.
--
-- Additive + idempotent. Nullable. RLS on phone_agent_config uses a
-- table-level service-role policy (FOR ALL USING (true)), which already
-- covers new columns — no extra GRANT/POLICY required (matches 024/027/032).

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS script_pack TEXT;

COMMENT ON COLUMN phone_agent_config.script_pack IS
    'Call-script pack id (services/phone_agent/script_packs.py). NULL/''''/legacy/unknown = generic prompt (byte-identical legacy behavior). Never auto-derived from business_type.';

-- Safety-net re-declaration (no-op wherever the base table already has it).
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS business_type TEXT;
