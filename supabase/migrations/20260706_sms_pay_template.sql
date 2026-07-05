-- Merchant-customized Text-to-Pay SMS body. Supports {name} {business}
-- {total} {link} placeholders; rendered with safe replace (never .format) by
-- services/phone_agent/sms_checkout._format_checkout_sms. NULL/empty falls
-- back to the default copy. Edited from Phone Orders → Settings.
ALTER TABLE phone_agent_config ADD COLUMN IF NOT EXISTS sms_pay_template TEXT;
