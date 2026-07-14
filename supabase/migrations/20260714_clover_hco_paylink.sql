-- Clover Hosted Checkout text-to-pay (per-merchant toggle, default OFF).
--
-- The old Clover payment-link path posted to /v3/merchants/{mid}/pay_links,
-- which does not exist in Clover's API — it never worked and silently fell
-- back to the Meridian checkout page. The real rail is Hosted Checkout
-- (POST /invoicingcheckoutservice/v1/checkouts), whose sessions expire 15
-- minutes after creation, so the session is created LAZILY when the customer
-- taps the branded /p short link, not at SMS-send time.
--
-- Additive + nullable: NULL payment_link_provider reads as 'stripe' in code,
-- so existing merchants see zero behavior change until a row opts in.

ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS payment_link_provider     text,
  ADD COLUMN IF NOT EXISTS clover_hco_webhook_secret text;

COMMENT ON COLUMN phone_agent_config.payment_link_provider IS
  'Text-to-pay rail for phone orders: stripe (default when NULL) | clover (Hosted Checkout via lazy /p short link).';
COMMENT ON COLUMN phone_agent_config.clover_hco_webhook_secret IS
  'Per-merchant HMAC signing secret for the Clover Hosted Checkout payment webhook (merchant generates it in Clover dashboard: Settings > Ecommerce > Hosted Checkout, pasting our /api/clover/hco/webhook URL). NULL = webhook rejected 401 for this merchant.';

-- checkout_sessions: what the lazy flow needs at tap time.
--   payload    — the ready-to-POST HCO body (customer + shoppingCart with tax
--                computed into line items) + the clover merchant id hint. The
--                merchant access token is deliberately NOT stored here; the
--                /p handler re-resolves it from the encrypted pos_connections
--                row on every (re)creation.
--   expires_at — expiry of the CURRENT HCO session (provider_ref/checkout_url);
--                past it, /p transparently creates a fresh session.
ALTER TABLE checkout_sessions
  ADD COLUMN IF NOT EXISTS payload    jsonb,
  ADD COLUMN IF NOT EXISTS expires_at timestamptz;

COMMENT ON COLUMN checkout_sessions.payload IS
  'Provider-specific lazy-creation payload (clover: {hco_request, clover_merchant_id}). Never contains access tokens.';
COMMENT ON COLUMN checkout_sessions.expires_at IS
  'Expiry of the currently-stored provider session (clover HCO: ~15 min after creation). /p re-creates past this.';
