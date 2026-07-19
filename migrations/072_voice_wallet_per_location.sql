-- ============================================================================
-- 072 — Per-location voice self-funding: per-merchant balance floor
-- ============================================================================
--
-- The voice_ledger already runs a per-merchant P&L (Stripe/Clover fees CREDIT,
-- each Vapi call's cost DEBITs). The underwater→Telnyx fallback gate
-- (vapi_webhook.py) reads ONE global env floor (VOICE_BALANCE_FLOOR_CENTS) for
-- every merchant. This adds a PER-LOCATION floor so each operator can set how
-- far their account may run underwater before calls fall back to the cheaper
-- rail — i.e. tune their own self-funding tolerance.
--
-- NULL = use the global env default (unchanged behavior). Additive + reversible.
-- ============================================================================

ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS voice_balance_floor_cents integer;

COMMENT ON COLUMN phone_agent_config.voice_balance_floor_cents IS
  'Per-location voice self-funding floor (cents, may be negative = allowed grace '
  'float). When the merchant''s voice_ledger balance is <= this floor, incoming '
  'calls fall back to the cheaper Telnyx rail instead of burning Vapi minutes. '
  'NULL = use the global VOICE_BALANCE_FLOOR_CENTS env default (migration 072).';
