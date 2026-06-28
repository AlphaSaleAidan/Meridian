-- 035_phone_call_insights.sql
-- Per-call quality scores for the phone agent's self-training loop.
--
-- The real-call training loop (scripts/phone_realcall_train.py) mines completed
-- calls from phone_call_logs, runs an LLM judge over each transcript, and writes
-- one insight row per call here: a 0-10 quality score, failure tags from a fixed
-- taxonomy, a one-line critique, and a concrete "fix" suggestion. The merchant
-- dashboard's Phone section reads this to show an agent-quality trend, and the
-- distill step aggregates the worst real calls into regression scenarios for the
-- offline harness. Brain changes are NEVER auto-deployed — proposals only.
--
-- Additive + idempotent. Backend-owned (service role); no user-JWT access,
-- matching quote_requests (034) and the other phone tables.

CREATE TABLE IF NOT EXISTS phone_call_insights (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid         TEXT NOT NULL,                 -- FK-ish to phone_call_logs.call_sid (no hard FK: logs table is ad-hoc)
    merchant_id      TEXT NOT NULL,
    score            INT  NOT NULL CHECK (score >= 0 AND score <= 10),
    tags             TEXT[] NOT NULL DEFAULT '{}',  -- failure tags from the fixed taxonomy
    critique         TEXT DEFAULT '',               -- one specific sentence
    fix              TEXT DEFAULT '',               -- one concrete rule that would have prevented the issue
    order_placed     BOOLEAN DEFAULT FALSE,         -- did this call result in a submitted order
    duration_seconds INT,
    judge_model      TEXT DEFAULT '',               -- which model produced the score (provenance)
    judged_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- one insight per call; re-judging upserts on this key
    CONSTRAINT phone_call_insights_call_sid_uniq UNIQUE (call_sid)
);

-- Dashboard reads newest-first, scoped per merchant; trend queries scan by date.
CREATE INDEX IF NOT EXISTS idx_phone_call_insights_merchant
    ON phone_call_insights (merchant_id, judged_at DESC);

-- Backend accesses this table with the service role only; deny user-JWT access.
ALTER TABLE phone_call_insights ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "phone_call_insights_service_all" ON phone_call_insights
        FOR ALL USING (auth.role() = 'service_role')
        WITH CHECK (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON phone_call_insights TO service_role;
