-- Store the provider id/sid of the merchant's purchased phone number so a
-- later "swap number" can release it at the provider (Telnyx phone-number /
-- number-order id, or Twilio IncomingPhoneNumber SID). Written by
-- POST /api/phone/provision-number at purchase time. Nullable: legacy rows
-- provisioned before this column simply skip the release step on swap.
ALTER TABLE phone_agent_config ADD COLUMN IF NOT EXISTS phone_number_sid TEXT;
