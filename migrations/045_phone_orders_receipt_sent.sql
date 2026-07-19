-- 045_phone_orders_receipt_sent.sql
-- Durable, cross-worker idempotency key for the customer order-receipt SMS.
--
-- Both the turn-based Vapi path (via the Stripe/Clover payment webhooks) and the
-- streaming Pipecat path (pay_on_phone._fanout_release) call the shared
-- order_receipt.send_order_receipt() helper. It claims the one-shot send by
-- conditionally flipping receipt_sent false→true on the matching phone_orders
-- row (WHERE receipt_sent = false). Whoever wins the flip owns the send; a later
-- report of the same order (sidecar AND webhook both reporting) reads the row as
-- already claimed and sends nothing. NOT NULL DEFAULT false so an untouched /
-- pre-existing row is always eligible for its first (and only) receipt.
--
-- Additive + idempotent (ADD COLUMN IF NOT EXISTS). Run in the Supabase SQL editor.

ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS receipt_sent BOOLEAN NOT NULL DEFAULT false;

-- The claim filters by pos_order_id — index it so the conditional PATCH is a
-- cheap point lookup, not a scan, on the payment/settlement hot path.
CREATE INDEX IF NOT EXISTS idx_phone_orders_pos_order_id ON phone_orders (pos_order_id);
