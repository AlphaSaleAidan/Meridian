-- 047: Phone agent "Pay with Cash" opt-in.
--
-- When a merchant turns this on (behind an explicit warning modal in the setup
-- wizard / phone Settings tab), the phone agent may offer CASH as a payment
-- option. Cash orders are dispatched to the kitchen flagged UNPAID / CASH ON
-- PICKUP — mirroring the existing pay-at-pickup unpaid-order path — and NO
-- Stripe/Clover payment link is created for them.
--
-- Purely additive and back-compat: NULL / false = current behavior (the agent
-- never offers cash), so every existing merchant is unchanged until they opt in.
ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS accept_cash boolean;

COMMENT ON COLUMN phone_agent_config.accept_cash IS
  'When true, the phone agent may offer cash as a payment option; cash orders reach the kitchen flagged UNPAID / CASH ON PICKUP with no payment link. NULL/false = never offer cash (default). Opt-in is gated behind a warning modal in the setup wizard / phone Settings.';
