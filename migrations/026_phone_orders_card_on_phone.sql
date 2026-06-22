-- 026_phone_orders_card_on_phone.sql
-- Card-on-the-phone backup payment: when the SMS pay-link can't be delivered, the
-- voice agent takes the card on the call (keypad/DTMF), charges it, and — on
-- approval — marks the held order paid via pay_on_phone.mark_order_paid(), which
-- now records HOW it was paid. Only the last-4 is ever stored (never the PAN).
--
-- Extends the pay-status columns from 025_phone_orders_pay_status.sql.
-- Idempotent (ADD COLUMN IF NOT EXISTS). Run manually in the Supabase SQL editor.

ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS card_brand     TEXT;  -- visa | mastercard | amex | discover | unknown
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS card_last4     TEXT;  -- last 4 only — never the full card number
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS payment_txn_id TEXT;  -- gateway/sim transaction id
ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS payment_note   TEXT;  -- e.g. 'simulated (demo)' (defensive: also set on the link path)
