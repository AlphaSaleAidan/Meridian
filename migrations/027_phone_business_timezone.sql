-- 027_phone_business_timezone.sql
-- Timezone for evaluating a merchant's business_hours (after-hours gate).
--
-- The phone agent's after-hours gate (src/api/routes/phone.py /voice) only
-- enforces business_hours when BOTH business_hours AND this timezone are set —
-- the previous helper compared local open/close strings against UTC, which
-- mis-gated merchants. An IANA name (e.g. 'America/Toronto') makes the check
-- correct. NULL/empty => the gate stays open (no behavior change), so this is a
-- safe, additive opt-in.

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS business_timezone TEXT;

COMMENT ON COLUMN phone_agent_config.business_timezone IS
    'IANA timezone (e.g. America/Toronto) used to evaluate business_hours for the after-hours gate. NULL/empty disables the gate.';
