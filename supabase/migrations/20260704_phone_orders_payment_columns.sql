-- Payment-tracking columns on phone_orders. The pay-on-phone flow
-- (pay_on_phone.py / order_router.py) has been PATCHing these since the
-- pay-now hold shipped, but no migration ever added them — PostgREST dropped
-- the writes silently, so no order could actually be marked paid/held.
-- Required for POS-PUSH-AFTER-PAYMENT: the held row is the source of truth
-- that release (mark_order_paid) reads to create the deferred POS ticket.
--
-- Additive migration: safe to apply, reversible by dropping the columns.

ALTER TABLE phone_orders
  ADD COLUMN IF NOT EXISTS payment_status text,
  ADD COLUMN IF NOT EXISTS payment_link text,
  ADD COLUMN IF NOT EXISTS payment_method text,
  ADD COLUMN IF NOT EXISTS sms_sent boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS kitchen_released boolean,
  ADD COLUMN IF NOT EXISTS card_brand text,
  ADD COLUMN IF NOT EXISTS card_last4 text,
  ADD COLUMN IF NOT EXISTS payment_txn_id text,
  ADD COLUMN IF NOT EXISTS payment_note text;

-- mark_order_paid matches held orders by merchant + caller (latest first)
-- when the Stripe session carries no pos_order_id (deferred POS push).
CREATE INDEX IF NOT EXISTS phone_orders_merchant_caller_created_idx
  ON phone_orders (merchant_id, caller_phone, created_at DESC);
