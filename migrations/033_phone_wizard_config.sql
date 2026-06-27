-- 032_phone_wizard_config.sql
-- Persist the phone setup wizard's configuration end-to-end.
--
-- The wizard (frontend SetupWizard.tsx) collects an order-routing choice, a
-- human warm-transfer number, and business-hours / after-hours messaging. The
-- live agent (src/api/routes/phone.py) ALREADY reads business_hours,
-- business_timezone, after_hours_message and transfer_number from this row at
-- call time — but the wizard's *routing* choice had nowhere to land.
--
-- This migration adds the missing order_routing column. The other three columns
-- (business_hours / after_hours_message / transfer_number) already exist from
-- the base table (supabase/migrations/20260507_phone_agent.sql); they are
-- re-declared here with ADD COLUMN IF NOT EXISTS purely as a safety net for any
-- environment where the base table predates them. On a normal database these
-- three are no-ops and DO NOT override the existing columns' defaults.
--
-- Additive + idempotent. All columns nullable. RLS on phone_agent_config uses a
-- table-level service-role policy (FOR ALL USING (true)), which already covers
-- new columns, so no extra GRANT/POLICY is required (matches 024/027/028).

-- The genuinely new column: how the merchant wants confirmed orders delivered.
-- One of: 'pos' | 'webhook' | 'sms' | 'email' (free text; not constrained so the
-- set can grow without a migration). NULL => unset (wizard defaults at runtime).
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS order_routing TEXT;

COMMENT ON COLUMN phone_agent_config.order_routing IS
    'Order-delivery routing chosen in the setup wizard: pos | webhook | sms | email. NULL = unset.';

-- Safety-net re-declarations (no-ops where the base table already has them).
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS business_hours JSONB;

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS after_hours_message TEXT;

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS transfer_number TEXT;
