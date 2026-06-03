-- Per-merchant kill switch for live POS writes.
--
-- The demo merchant runs through the same code path as a real merchant
-- (production-shaped). Once Square OAuth completes, pos_access_token is
-- populated and the only thing standing between create_pos_order and a
-- live order is the correctness of the NULL-check on the token. That is
-- too thin a margin for a demo number that gets prodded constantly.
--
-- demo_safe = true → create_pos_order returns logs-only regardless of
-- whether pos_access_token is populated. The merchant's order still
-- persists in phone_orders, so the demo flow is observable, but no
-- HTTP call to Square / Toast / Clover is ever attempted.
--
-- This is the protection that makes the "no money risk" claim about
-- the demo path testable (see tests/unit/test_pos_order_guards.py)
-- rather than resting on the assumption that the token stays NULL.

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS demo_safe BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN phone_agent_config.demo_safe IS
    'When true, create_pos_order returns logs-only regardless of pos_access_token presence. Set true for demo / test merchants; false for real merchants.';
