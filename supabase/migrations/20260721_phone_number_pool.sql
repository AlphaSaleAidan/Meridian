-- Pre-provisioned phone-number inventory ("buy 10 to have ready").
--
-- Provisioning was buy-one-per-merchant on demand — a live Telnyx purchase +
-- Vapi import at signup, with the latency and failure surface that implies.
-- This table holds numbers bought AND Vapi-bound ahead of time so onboarding
-- claims a ready-to-ring number instantly instead of buying live.
--
-- All Telnyx (no Twilio). Each row is one DID: bought at Telnyx (provider_sid =
-- number order id) and imported into Vapi (vapi_phone_number_id) with our
-- webhook, so it answers as the agent the moment it's assigned.

CREATE TABLE IF NOT EXISTS phone_number_pool (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL DEFAULT 'telnyx',
    phone_number text NOT NULL UNIQUE,
    provider_sid text,              -- Telnyx number-order id (for release)
    vapi_phone_number_id text,      -- Vapi phone-number id (bound to our webhook)
    country text NOT NULL DEFAULT 'CA',
    status text NOT NULL DEFAULT 'available',   -- available | assigned | released
    assigned_merchant_id text,
    assigned_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Fast "give me a free one" claim.
CREATE INDEX IF NOT EXISTS phone_number_pool_available_idx
    ON phone_number_pool (created_at)
    WHERE status = 'available';

-- Internal inventory: service-role only. No tenant reads/writes.
ALTER TABLE phone_number_pool ENABLE ROW LEVEL SECURITY;
