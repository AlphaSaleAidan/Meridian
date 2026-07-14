-- 040: website orders — Stripe pay-first flow
--
-- Mobile/website orders are now paid through Stripe BEFORE the kitchen sees
-- them: the order is stored as status='awaiting_payment', the customer pays
-- via Stripe Checkout, and the Connect webhook flips status='paid' and only
-- then releases the POS/kitchen dispatch (ticket marked PAID ONLINE).
-- Code tolerates these columns being absent, so apply order doesn't matter.

ALTER TABLE website_orders
    ADD COLUMN IF NOT EXISTS stripe_session_id TEXT,  -- Checkout session / payment intent ref
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;     -- when Stripe confirmed payment
