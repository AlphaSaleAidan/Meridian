-- 041: per-merchant native POS pay-by-text opt-in
--
-- When true (AND the global CLOVER_NATIVE_PAY_ENABLED env is on — two
-- independent gates, both default OFF), phone orders for Clover merchants
-- text a Clover Hosted Checkout link instead of Stripe: the customer pays on
-- the merchant's own Clover processing, and Meridian's fee is added as a
-- checkout line item + booked to the voice ledger on verified payment.

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS native_pos_pay BOOLEAN NOT NULL DEFAULT false;
