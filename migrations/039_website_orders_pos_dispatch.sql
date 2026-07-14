-- 039: website orders → POS dispatch outcome
--
-- Mobile/website food orders now get pushed into the merchant's connected
-- POS (Clover first: tagged order + line items + kitchen print event) right
-- after the website_orders insert. These columns record that outcome so the
-- merchant dashboard can show whether the kitchen actually received the
-- ticket. Code tolerates their absence, so this can apply after deploy.

ALTER TABLE website_orders
    ADD COLUMN IF NOT EXISTS pos_status TEXT,          -- sent | failed | skipped
    ADD COLUMN IF NOT EXISTS pos_order_id TEXT,        -- id of the order created in the POS
    ADD COLUMN IF NOT EXISTS pos_error TEXT,           -- short reason when failed/skipped
    ADD COLUMN IF NOT EXISTS pos_sent_at TIMESTAMPTZ;  -- when the POS accepted the order
