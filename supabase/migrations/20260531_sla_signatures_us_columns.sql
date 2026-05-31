-- Add US-specific columns to sla_signatures so US deals don't have to overload
-- the province / monthly_price_cad_cents columns. Additive + backfill-safe.
--
-- Existing CA rows: country defaults to 'CA', state stays NULL, USD columns
-- stay NULL. CA data continues to live in province / monthly_price_cad_cents.
-- New US rows: country = 'US', state holds the US state, USD columns hold the
-- price. province / monthly_price_cad_cents stay NULL for US rows.

ALTER TABLE sla_signatures
  ADD COLUMN IF NOT EXISTS country text NOT NULL DEFAULT 'CA'
    CHECK (country IN ('CA', 'US'));

ALTER TABLE sla_signatures
  ADD COLUMN IF NOT EXISTS state text;

ALTER TABLE sla_signatures
  ADD COLUMN IF NOT EXISTS monthly_price_usd_cents integer;

ALTER TABLE sla_signatures
  ADD COLUMN IF NOT EXISTS setup_fee_usd_cents integer DEFAULT 0;

CREATE INDEX IF NOT EXISTS sla_signatures_country_idx ON sla_signatures(country);
