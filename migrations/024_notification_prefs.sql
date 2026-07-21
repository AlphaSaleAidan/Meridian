-- Merchant notification preferences (Settings → Notifications tab).
-- Keyed by the merchant's org id WITHOUT an FK: Canada merchants live in
-- businesses, US-era orgs in organizations (entity-model split, audit
-- 2026-07-20), so no single parent table exists to reference.
CREATE TABLE IF NOT EXISTS notification_prefs (
    org_id uuid PRIMARY KEY,
    prefs jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Backend-only access (service role bypasses RLS). RLS on with no policies
-- locks out anon/authenticated PostgREST access entirely.
ALTER TABLE notification_prefs ENABLE ROW LEVEL SECURITY;
