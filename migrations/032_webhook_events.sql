-- 032_webhook_events.sql
-- Persistent, cross-worker webhook idempotency.
--
-- The Square webhook processor previously deduped redelivered events with an
-- in-process dict (`WebhookProcessor._seen_events`). That dict is lost on
-- restart and is NOT shared across the 4 uvicorn workers, so the same Square
-- event (Square retries until it gets a 200) could be processed by a second
-- worker — double-inserting orders / re-enriching payments.
--
-- This table is the durable source of truth: the webhook handler does an
-- atomic INSERT keyed on the provider's event id. A unique-violation (the row
-- already exists) == a duplicate delivery → the handler skips processing and
-- still returns 200. Survives restarts and is shared by all workers.
--
-- Backend-only: written exclusively by the service-role backend. No user/JWT
-- role ever touches it, so RLS is on with a service-role-only policy and the
-- grant goes to service_role alone (mirrors the commissions table, which is
-- likewise service-role-owned).
--
-- ADDITIVE + idempotent: safe to run more than once; touches nothing else.

CREATE TABLE IF NOT EXISTS webhook_events (
    event_id    TEXT PRIMARY KEY,                       -- provider's unique event id
    provider    TEXT NOT NULL DEFAULT 'square',         -- square | clover | toast | ...
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cheap retention sweeps ("delete rows older than N days") without scanning.
CREATE INDEX IF NOT EXISTS idx_webhook_events_received_at
    ON webhook_events (received_at);

-- Backend accesses this table with the service role only; deny user-JWT access.
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "webhook_events_service_all" ON webhook_events
        FOR ALL USING (auth.role() = 'service_role')
        WITH CHECK (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- service_role gets full DML; `authenticated` gets nothing (backend-owned).
GRANT SELECT, INSERT, UPDATE, DELETE ON webhook_events TO service_role;
