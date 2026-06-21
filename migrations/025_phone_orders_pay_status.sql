-- 025_phone_orders_pay_status.sql
-- Pay-on-the-phone (anti-scam): hold the kitchen ticket until payment clears.
--
-- pay_on_phone.py writes these columns when payment_mode = pay_now: the order is
-- created `status='awaiting_payment'` + `kitchen_released=false` + `payment_status='pending'`,
-- then the /twilio/payment-webhook flips it to `status='paid'`, `kitchen_released=true`,
-- `payment_status='paid'` once Square confirms payment. Defaults below preserve today's
-- behavior for every existing/pay_at_pickup order (confirmed + released).
--
-- Idempotent (ADD COLUMN IF NOT EXISTS). Run manually in the Supabase SQL editor.

ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS status            TEXT    NOT NULL DEFAULT 'confirmed';   -- confirmed | awaiting_payment | paid
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS kitchen_released  BOOLEAN NOT NULL DEFAULT true;          -- false while awaiting payment (held)
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS payment_status    TEXT             DEFAULT 'none';         -- none | pending | paid
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS payment_link      TEXT;
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS payment_method    TEXT;
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS sms_sent          BOOLEAN          DEFAULT false;

-- Find held (unpaid) orders fast for the kitchen-release flip.
CREATE INDEX IF NOT EXISTS idx_phone_orders_awaiting
    ON phone_orders (merchant_id, status) WHERE status = 'awaiting_payment';
