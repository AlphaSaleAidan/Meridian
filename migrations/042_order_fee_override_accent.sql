-- 042: per-merchant order-fee override + agent accent, and catch prod up on
-- plan_tier (036 was authored but never applied, while merged code already
-- SELECTs the column — the failed select silently dropped stripe_account_id
-- from the same query and pushed website orders to platform-direct charges).

-- Rep-negotiated per-order Meridian fee, in cents of the merchant's charge
-- currency. NULL = use the plan-tier / env default. Sliders in the sales
-- portals enforce tier redlines (premium ≥ 65¢, command ≥ 45¢); the backend
-- clamps again on write.
ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS order_fee_cents integer
  CHECK (order_fee_cents IS NULL OR order_fee_cents >= 0);

COMMENT ON COLUMN phone_agent_config.order_fee_cents IS
  'Per-merchant Meridian per-order fee override in cents (charge currency). NULL = plan-tier/env default. Set from the rep portal fee slider; floors: premium 65, command 45.';

-- Agent accent chosen in the phone setup wizard (north_american | indian |
-- east_asian). Presentation-level grouping of the live Vapi voice roster;
-- the voice column still carries the actual voice id.
ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS accent text;

COMMENT ON COLUMN phone_agent_config.accent IS
  'Voice accent group picked at setup (north_american | indian | east_asian). Pairs with language=multi for Hindi/Punjabi code-switch understanding.';

-- From 036 (never applied): merged code selects this column on every website
-- order. All-NULL = default tier behavior, so this is purely additive.
ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS plan_tier text;

COMMENT ON COLUMN phone_agent_config.plan_tier IS
  'Subscription plan tier (standard | premium | command); drives the per-order Meridian fee under the fee-split model. NULL = default tier rate.';

ALTER TABLE website_orders
  ADD COLUMN IF NOT EXISTS merchant_fee_amount numeric;

COMMENT ON COLUMN website_orders.merchant_fee_amount IS
  'Merchant-side platform fee (2.99% of subtotal) under the fee-split model; settled out of the payout, never added to the customer total.';
