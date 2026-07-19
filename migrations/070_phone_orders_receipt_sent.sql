-- 070_phone_orders_receipt_sent.sql
--
-- (Renumbered 045 → 070 to clear a collision: PR #352 owns migration 045
-- (tier-3 grants), and the 045–060 batch is reserved. 070 is well clear.)
--
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
-- CLAIM KEY IS ROW-AWARE (bug fix): the claim no longer keys blindly on
-- pos_order_id (which is "" on pay_now-Stripe held rows and POS-failed
-- pay_at_pickup rows, so the flip matched ZERO rows and the receipt was silently
-- dropped). Each flow claims on a column its row RELIABLY carries:
--   * streaming / POS-failed pay_at_pickup  → id (the phone_orders primary key)
--   * pay_now-Stripe (deferred POS)         → merchant_id + caller_phone, newest
--   * Clover-native                         → pos_order_id (a real ticket id)
-- The indexes below back all three claim paths so the conditional PATCH is a
-- cheap point lookup, not a scan, on the payment/settlement hot path. (id is the
-- primary key and already indexed.)
--
-- Additive + idempotent (ADD COLUMN / CREATE INDEX IF NOT EXISTS). Run in the
-- Supabase SQL editor.

ALTER TABLE phone_orders ADD COLUMN IF NOT EXISTS receipt_sent BOOLEAN NOT NULL DEFAULT false;

-- Clover-native claim: exact match on the POS ticket id.
CREATE INDEX IF NOT EXISTS idx_phone_orders_pos_order_id ON phone_orders (pos_order_id);

-- pay_now-Stripe claim: newest row for (merchant_id, caller_phone). created_at
-- desc so the most-recent lookup mark_order_paid mirrors is a single index seek.
CREATE INDEX IF NOT EXISTS idx_phone_orders_merchant_phone_recent
    ON phone_orders (merchant_id, caller_phone, created_at DESC);
