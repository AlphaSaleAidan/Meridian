-- ORDER DELIVERY FAN-OUT + KITCHEN PROVE-OUT (2026-07-16)
--
-- Before this change, order delivery was effectively either/or: the POS push
-- and the SMS legs ran sequentially and only coarse pos_success/sms_sent flags
-- were recorded, so support could not see WHICH channel fired and which failed.
-- These columns give phone_orders a per-channel delivery ledger plus a
-- fulfillment-confirmation pair proving the ticket actually reached a
-- make-able state in the POS (kitchen prove-out / test orders).
--
-- Idempotent: safe to re-run.

-- Per-channel delivery status. Values (TEXT, not enum, so new channels/POSes
-- can add states without a migration):
--   pos_delivery_status:      sent | failed | deferred_pending_payment |
--                             skipped_disabled | skipped_no_pos | demo_safe
--   sms_delivery_status:      sent | failed | skipped_disabled |
--                             skipped_no_phone | skipped_no_link
--   merchant_notify_status:   sent | failed | deferred_pending_payment |
--                             skipped_disabled | skipped_no_number
ALTER TABLE phone_orders
    ADD COLUMN IF NOT EXISTS pos_delivery_status TEXT,
    ADD COLUMN IF NOT EXISTS sms_delivery_status TEXT,
    ADD COLUMN IF NOT EXISTS merchant_notify_status TEXT,
    -- Per-channel timestamps/errors, e.g.
    -- {"pos": {"at": "...", "error": "square_api_error"}, "customer_sms": {...}}
    ADD COLUMN IF NOT EXISTS delivery_detail JSONB DEFAULT '{}',
    -- Kitchen prove-out: set when the POS-side order is confirmed in a
    -- make-able state (Square: state OPEN/COMPLETED with line items present),
    -- either by the post-create verification poll or by the POS webhook.
    ADD COLUMN IF NOT EXISTS fulfillment_confirmed_at TIMESTAMPTZ,
    -- Raw POS-side order state (Square: OPEN/COMPLETED/CANCELED/DRAFT), or
    -- 'unsupported' when no verifier exists for the merchant's POS yet.
    ADD COLUMN IF NOT EXISTS fulfillment_state TEXT;

COMMENT ON COLUMN phone_orders.pos_delivery_status IS
    'Per-channel outcome of the POS push leg (sent/failed/deferred_pending_payment/skipped_*/demo_safe).';
COMMENT ON COLUMN phone_orders.sms_delivery_status IS
    'Per-channel outcome of the customer SMS leg (sent/failed/skipped_*).';
COMMENT ON COLUMN phone_orders.merchant_notify_status IS
    'Per-channel outcome of the merchant notification SMS leg (sent/failed/deferred_pending_payment/skipped_*).';
COMMENT ON COLUMN phone_orders.delivery_detail IS
    'Per-channel timestamps + error strings for support: {"pos": {...}, "customer_sms": {...}, "merchant_sms": {...}}.';
COMMENT ON COLUMN phone_orders.fulfillment_state IS
    'POS-side order state from the fulfillment verifier or POS webhook (Square: OPEN/COMPLETED/...; unsupported = no verifier for this POS).';
COMMENT ON COLUMN phone_orders.fulfillment_confirmed_at IS
    'When the order was confirmed make-able in the POS (kitchen prove-out).';

-- Fast webhook lookups: order.updated events match phone orders by POS order id.
CREATE INDEX IF NOT EXISTS idx_phone_orders_pos_order_id
    ON phone_orders(pos_order_id) WHERE pos_order_id IS NOT NULL AND pos_order_id <> '';

-- Per-merchant delivery-channel override. NULL = defaults
-- ({"pos": true, "customer_sms": true, "merchant_sms": true}); individual keys
-- may be set to false to disable a leg (e.g. {"merchant_sms": false}).
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS delivery_channels JSONB;

COMMENT ON COLUMN phone_agent_config.delivery_channels IS
    'Delivery-leg toggles: {"pos": bool, "customer_sms": bool, "merchant_sms": bool}. NULL/missing keys = enabled (fan-out default: all on).';
