-- 034_quote_requests.sql
-- Public "Schedule a Quote" lead capture.
--
-- The founder retired the self-serve SaaS pricing tiers on the public marketing
-- pages (no real differentiators) in favour of a lightweight lead-capture flow:
-- a prospect on the US/CAD landing page asks for a sales call inside a 48h
-- window, and sales follows up. The public endpoint POST /api/quote-request
-- inserts one row here and emails the founders.
--
-- This table is written EXCLUSIVELY by the service-role backend (the endpoint
-- has no auth — it is anonymous lead capture — but it always runs server-side
-- with the service role). No user/JWT role ever touches it, so RLS is on with a
-- service-role-only policy and the grant goes to service_role alone. This
-- mirrors the backend-owned tables webhook_events (032) and the commissions
-- table.
--
-- ADDITIVE + idempotent: safe to run more than once; touches nothing else.

CREATE TABLE IF NOT EXISTS quote_requests (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name        TEXT NOT NULL,
    business_name    TEXT NOT NULL,
    email            TEXT NOT NULL,
    phone            TEXT NOT NULL,
    preferred_date   TEXT,            -- prospect-chosen call date (today/tomorrow), free text
    preferred_window TEXT,            -- e.g. 'morning' | 'afternoon' | 'evening', free text
    notes            TEXT,            -- optional "anything we should know"
    source           TEXT,            -- 'us-landing' | 'canada-landing' | ...
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sales triages newest-first; cheap ordering without a scan.
CREATE INDEX IF NOT EXISTS idx_quote_requests_created_at
    ON quote_requests (created_at DESC);

-- Backend accesses this table with the service role only; deny user-JWT access.
ALTER TABLE quote_requests ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "quote_requests_service_all" ON quote_requests
        FOR ALL USING (auth.role() = 'service_role')
        WITH CHECK (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- service_role gets full DML; `authenticated` gets nothing (backend-owned).
GRANT SELECT, INSERT, UPDATE, DELETE ON quote_requests TO service_role;
