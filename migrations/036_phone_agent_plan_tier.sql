-- 036: plan_tier on phone_agent_config — the merchant's subscription tier
-- (standard | premium | command) driving the per-order Meridian fee under the
-- fee-split model (MERIDIAN_FEE_SPLIT_ENABLED):
--   standard → no per-order fee · premium → US$1.49 / CA$1.99 · command → US$1.00 / CA$1.39
-- NULL/'' = unset → payment_links falls back to the default tier's rate.

ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS plan_tier text;

COMMENT ON COLUMN phone_agent_config.plan_tier IS
  'Subscription plan tier (standard | premium | command); drives the per-order Meridian fee under the fee-split model. NULL = default tier rate.';

-- Website orders under the split model record the merchant-side 2.99% of the
-- subtotal separately from the customer-paid fee_amount (per-order fee + 30¢).
ALTER TABLE website_orders
  ADD COLUMN IF NOT EXISTS merchant_fee_amount numeric;

COMMENT ON COLUMN website_orders.merchant_fee_amount IS
  'Merchant-side platform fee (2.99% of subtotal) under the fee-split model; settled out of the payout, never added to the customer total.';
