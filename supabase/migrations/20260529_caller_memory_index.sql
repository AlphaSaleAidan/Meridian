-- Per-caller memory: index for phone-number lookups in phone_orders.
-- The phone agent runs this query once per call at handshake:
--   SELECT items, total, created_at FROM phone_orders
--   WHERE caller_phone = ? AND merchant_id = ? AND status = 'placed'
--   ORDER BY created_at DESC LIMIT 5;

CREATE INDEX IF NOT EXISTS idx_phone_orders_caller_phone
    ON phone_orders(caller_phone, merchant_id, created_at DESC)
    WHERE status = 'placed';
