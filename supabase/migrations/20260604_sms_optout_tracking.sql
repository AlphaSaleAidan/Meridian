-- SMS opt-out tracking with marketing/transactional split per CASL.
--
-- CASL distinguishes Commercial Electronic Messages (CEMs) from
-- transactional/service messages. A customer sending STOP should kill
-- promotional follow-ups but NOT in-flight transactional messages — the
-- payment link for an order they just placed by phone is transaction
-- completion, not marketing. A global boolean opt-out would strand it.
--
-- Two flags, deliberately separate:
--   marketing_optout     — set true on STOP/STOPALL/UNSUBSCRIBE keywords.
--                          Blocks promotional/CEM sends (loyalty offers,
--                          "we miss you" nudges, etc.).
--   transactional_optout — set only on explicit hard-stop ("never text me
--                          for any reason"). Blocks even order-related
--                          messages. Rare; honoured because CASL allows
--                          it even though transactional carve-outs exist.

CREATE TABLE IF NOT EXISTS sms_optout_tracking (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id              TEXT NOT NULL,
    customer_phone           TEXT NOT NULL,
    marketing_optout         BOOLEAN NOT NULL DEFAULT false,
    transactional_optout     BOOLEAN NOT NULL DEFAULT false,
    marketing_optout_at      TIMESTAMPTZ,
    transactional_optout_at  TIMESTAMPTZ,
    last_inbound_at          TIMESTAMPTZ,
    notes                    TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT sms_optout_unique UNIQUE (merchant_id, customer_phone)
);

CREATE INDEX IF NOT EXISTS idx_sms_optout_lookup
    ON sms_optout_tracking (merchant_id, customer_phone);

-- Trigger to keep updated_at fresh.
CREATE OR REPLACE FUNCTION update_sms_optout_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sms_optout_updated_at ON sms_optout_tracking;
CREATE TRIGGER trg_sms_optout_updated_at
    BEFORE UPDATE ON sms_optout_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_sms_optout_updated_at();

ALTER TABLE sms_optout_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on sms_optout_tracking"
    ON sms_optout_tracking FOR ALL USING (true) WITH CHECK (true);
