-- Reservation hand-off for the phone agent: the agent texts callers the
-- restaurant's EXISTING reservation link (OpenTable/Resy/…); Meridian never
-- books tables itself. reservation_url is found by the onboarding scraper
-- (wizard toggle) and editable in the dashboard.
-- Also adds columns merchant_config.py has been reading with defaults but no
-- migration ever created (payment_mode / sms flags / pos_webhook_url).
--
-- Additive migration: safe to apply, reversible by dropping the columns.

ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS website_url text,
  ADD COLUMN IF NOT EXISTS reservation_url text,
  ADD COLUMN IF NOT EXISTS reservation_platform text,
  ADD COLUMN IF NOT EXISTS reservations_enabled boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS payment_mode text DEFAULT 'pay_now',
  ADD COLUMN IF NOT EXISTS sms_checkout_enabled boolean DEFAULT true,
  ADD COLUMN IF NOT EXISTS sms_ordering_enabled boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS pos_webhook_url text;
