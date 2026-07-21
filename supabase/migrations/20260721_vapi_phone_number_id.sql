-- Vapi phone-number binding id.
--
-- When a provisioned Twilio DID is imported into Vapi (so inbound calls fire
-- assistant-request → the live agent), Vapi returns a phone-number id. Store it
-- so a later swap / disconnect can release the Vapi binding too, not just the
-- Twilio number. NULL for legacy rows and for merchants provisioned while
-- VAPI_PRIVATE_KEY is unset (binding disabled → falls back to prior behavior).

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS vapi_phone_number_id text;
