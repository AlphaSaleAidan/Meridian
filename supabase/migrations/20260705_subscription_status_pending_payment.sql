-- billing.py + onboarding.py use subscription status 'pending_payment'
-- (invoice sent, awaiting first payment) but the enum never gained the value,
-- so EVERY provision's subscriptions upsert 400s and auto-billing never
-- engages. Additive, safe, idempotent.
--
-- ⚠ APPLY MANUALLY (gated per deploy runbook):
--   ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'pending_payment';
ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'pending_payment';
