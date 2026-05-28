-- Add configurable tax rate to phone agent config
ALTER TABLE phone_agent_config
ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(5,4) DEFAULT 0.13;

COMMENT ON COLUMN phone_agent_config.tax_rate IS 'Tax rate for phone orders (e.g., 0.13 = 13%). Defaults to 13% (Ontario HST).';
