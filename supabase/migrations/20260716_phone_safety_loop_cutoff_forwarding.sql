-- Phone-activation safety: per-merchant call cap, call-end telemetry,
-- carrier-forwarding verification, and activation funnel events.
-- Idempotent; authored only — apply via the usual migration process.

-- Per-merchant call cap override (minutes). NULL = use the env default
-- (MERIDIAN_VOICE_MAX_CALL_MIN, now 8). 0 = no cap for this merchant.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS max_call_minutes INTEGER;

-- The merchant's real store line (the number they forward FROM). Used by the
-- forwarding verification flow: we place a short test call to this line and
-- watch for it to arrive at the agent DID.
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS business_line_number TEXT;

-- Why each Vapi call ended — the instrument for "how many orders is the
-- call cap killing". One row per end-of-call-report (deduped on vapi_call_id).
CREATE TABLE IF NOT EXISTS voice_call_endings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id      TEXT NOT NULL,
    vapi_call_id     TEXT,
    ended_reason     TEXT,                 -- raw Vapi endedReason
    disposition      TEXT NOT NULL DEFAULT 'other'
        CHECK (disposition IN ('cutoff', 'caller_hangup', 'agent_hangup', 'silence', 'error', 'other')),
    duration_seconds INTEGER,
    had_order        BOOLEAN,              -- best-effort; NULL = undeterminable
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_voice_call_endings_merchant
    ON voice_call_endings(merchant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_call_endings_call
    ON voice_call_endings(vapi_call_id);

-- Carrier-forwarding verification attempts (setup wizard "Verify forwarding").
CREATE TABLE IF NOT EXISTS forwarding_verifications (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'verified', 'failed')),
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_forwarding_verifications_merchant
    ON forwarding_verifications(merchant_id, started_at DESC);

-- Activation funnel events fired by the forwarding wizard
-- (carrier_selected, codes_viewed, verify_started, verified, verify_failed)
-- so stalls in phone activation are visible.
CREATE TABLE IF NOT EXISTS phone_activation_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id TEXT NOT NULL,
    step        TEXT NOT NULL,
    meta        JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_phone_activation_events_merchant
    ON phone_activation_events(merchant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_phone_activation_events_step
    ON phone_activation_events(step);

-- RLS: service-role-only, same posture as the other phone_agent tables.
ALTER TABLE voice_call_endings ENABLE ROW LEVEL SECURITY;
ALTER TABLE forwarding_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_activation_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'voice_call_endings'
          AND policyname = 'Service role full access on voice_call_endings'
    ) THEN
        CREATE POLICY "Service role full access on voice_call_endings"
            ON voice_call_endings FOR ALL USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'forwarding_verifications'
          AND policyname = 'Service role full access on forwarding_verifications'
    ) THEN
        CREATE POLICY "Service role full access on forwarding_verifications"
            ON forwarding_verifications FOR ALL USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'phone_activation_events'
          AND policyname = 'Service role full access on phone_activation_events'
    ) THEN
        CREATE POLICY "Service role full access on phone_activation_events"
            ON phone_activation_events FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;
