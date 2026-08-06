-- Order-accuracy findings for the phone agent (wrong-order detector).
--
-- Additive: one row per judged call, written by scripts/phone_order_accuracy.py.
-- Records whether the order the agent SUBMITTED matches what the caller actually
-- asked for on the call. Detection + human review only — nothing here ever edits
-- an order, and no code path reads this table to change agent behaviour.
--
-- Mirrors phone_call_logs conventions: merchant_id is TEXT (the phone agent logs
-- a bare 'demo' for the demo merchant), call_sid is the natural key.

CREATE TABLE IF NOT EXISTS phone_order_accuracy (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid          TEXT NOT NULL UNIQUE,
    merchant_id       TEXT NOT NULL,
    -- true  = captured order matches the transcript
    -- false = mis-capture (see discrepancies)
    -- null  = judge could not decide (treated as "not flagged", never blocks)
    order_matches     BOOLEAN,
    confidence        REAL,
    severity          TEXT NOT NULL DEFAULT 'none',
    -- [{"type":"wrong_quantity","item":"latte","expected":"2 large","captured":"1 medium","detail":"..."}]
    discrepancies     JSONB NOT NULL DEFAULT '[]',
    summary           TEXT,
    order_total       NUMERIC(10,2),
    duration_seconds  INTEGER,
    judge_model       TEXT,
    reviewed          BOOLEAN NOT NULL DEFAULT false,
    checked_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT phone_order_accuracy_severity_valid
        CHECK (severity IN ('none', 'low', 'medium', 'high'))
);

CREATE INDEX IF NOT EXISTS idx_order_accuracy_merchant
    ON phone_order_accuracy(merchant_id);
CREATE INDEX IF NOT EXISTS idx_order_accuracy_checked
    ON phone_order_accuracy(checked_at DESC);
-- The review queue: flagged calls, newest first.
CREATE INDEX IF NOT EXISTS idx_order_accuracy_flagged
    ON phone_order_accuracy(merchant_id, checked_at DESC)
    WHERE order_matches IS FALSE;

ALTER TABLE phone_order_accuracy ENABLE ROW LEVEL SECURITY;

-- Service role only. The dashboard reads through the API (service auth), never
-- directly with an anon/authenticated key.
CREATE POLICY phone_order_accuracy_service
    ON phone_order_accuracy FOR ALL TO service_role
    USING (true) WITH CHECK (true);

REVOKE SELECT ON phone_order_accuracy FROM anon, authenticated;
