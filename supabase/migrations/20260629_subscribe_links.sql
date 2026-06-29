-- subscribe_links — stable QR / short-link → Stripe subscription checkout
--
-- Purpose: A rep or the backend generates a subscribe link once; the URL/QR
-- never expires because GET /subscribe/{token} creates a FRESH Stripe
-- Checkout Session on each scan (the token itself is the stable artefact).
--
-- Relation to per-order fee:
--   subscribe_links → Stripe direct charge, mode=subscription (THIS table).
--   checkout_sessions → Stripe Connect destination charge (per-order $1.50 fee).
--   These are completely separate flows; no transfer_data / application_fee here.
--
-- RLS: service-role only — this table is written by the backend, never directly
-- by an end-user JWT.  Public GET /subscribe/{token} is a backend route that
-- reads via service-role; no anon/authenticated policy needed.
--
-- Idempotent: safe to apply more than once (IF NOT EXISTS guards throughout).
--
-- DO NOT apply to prod directly — the main session applies migrations.

-- ── Table ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS subscribe_links (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    token                text         UNIQUE NOT NULL,
    org_id               text,
    lead_id              text,
    monthly_amount_cents int          NOT NULL,
    currency             text         NOT NULL DEFAULT 'cad',
    business_name        text,
    setup_fee_cents      int          DEFAULT 0,
    first_month_free     bool         DEFAULT false,
    status               text         DEFAULT 'active',   -- active | disabled
    stripe_session_id    text,                             -- last created session
    created_at           timestamptz  DEFAULT now()
);

-- ── Indexes ────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS subscribe_links_token_idx
    ON subscribe_links (token);

CREATE INDEX IF NOT EXISTS subscribe_links_org_id_idx
    ON subscribe_links (org_id)
    WHERE org_id IS NOT NULL;

-- ── RLS ────────────────────────────────────────────────────────────────────
-- Enable RLS; service-role bypasses it automatically.
-- No anon / authenticated policies: all access is via the backend service key.

ALTER TABLE subscribe_links ENABLE ROW LEVEL SECURITY;

-- Explicit service-role policy (belt-and-suspenders; service-role always bypasses RLS
-- but being explicit prevents accidental wide-open policies being added later).
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'subscribe_links'
          AND policyname = 'service_role_all'
    ) THEN
        CREATE POLICY "service_role_all"
            ON subscribe_links
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;
