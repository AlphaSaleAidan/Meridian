-- ============================================================
-- MERIDIAN SECURITY HARDENING MIGRATION
-- Date: 2026-05-14
-- Purpose: RLS enforcement, security_events table, auto-RLS trigger
--
-- IMPORTANT: Review before running in production.
-- Run the RLS audit query first to identify unprotected tables.
-- ============================================================

-- ── 1. Security Events Table ─────────────────────────────────

CREATE TABLE IF NOT EXISTS security_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  ip_address TEXT,
  user_agent TEXT,
  path TEXT,
  method TEXT,
  user_id UUID,
  merchant_id UUID,
  portal_context TEXT,
  details JSONB DEFAULT '{}',
  environment TEXT,
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMPTZ,
  resolved_by UUID
);

ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;

-- Only admins can read security events
CREATE POLICY "admin_sees_security_events"
ON security_events FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid()
    AND role IN ('admin', 'canada_manager')
  )
);

-- Backend service role can insert (via API audit logging)
CREATE POLICY "service_inserts_security_events"
ON security_events FOR INSERT
WITH CHECK (true);

-- Indexes for fast time-based queries
CREATE INDEX IF NOT EXISTS idx_security_events_ts_severity
ON security_events (timestamp DESC, severity);

CREATE INDEX IF NOT EXISTS idx_security_events_unresolved
ON security_events (resolved, timestamp DESC)
WHERE resolved = FALSE;

CREATE INDEX IF NOT EXISTS idx_security_events_type
ON security_events (event_type, timestamp DESC);


-- ── 2. Revoke anon access from sensitive tables ──────────────
-- (These may fail silently if table doesn't exist — that's fine)

DO $$
BEGIN
  EXECUTE 'REVOKE ALL ON pos_connections FROM anon';
EXCEPTION WHEN undefined_table THEN NULL;
END $$;

DO $$
BEGIN
  EXECUTE 'REVOKE ALL ON user_profiles FROM anon';
EXCEPTION WHEN undefined_table THEN NULL;
END $$;

DO $$
BEGIN
  EXECUTE 'REVOKE ALL ON payout_rate_history FROM anon';
EXCEPTION WHEN undefined_table THEN NULL;
END $$;

DO $$
BEGIN
  EXECUTE 'REVOKE ALL ON security_events FROM anon';
EXCEPTION WHEN undefined_table THEN NULL;
END $$;


-- ── 3. Auto-RLS Event Trigger ────────────────────────────────
-- Ensures any new table created gets RLS enabled automatically.

CREATE OR REPLACE FUNCTION enforce_rls_on_new_tables()
RETURNS event_trigger AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN
    SELECT * FROM pg_event_trigger_ddl_commands()
    WHERE command_tag = 'CREATE TABLE'
  LOOP
    EXECUTE format(
      'ALTER TABLE %s ENABLE ROW LEVEL SECURITY',
      obj.object_identity
    );
    RAISE NOTICE 'RLS auto-enabled on table: %', obj.object_identity;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

DROP EVENT TRIGGER IF EXISTS auto_enable_rls;

CREATE EVENT TRIGGER auto_enable_rls
  ON ddl_command_end
  WHEN TAG IN ('CREATE TABLE')
  EXECUTE FUNCTION enforce_rls_on_new_tables();


-- ── 4. RLS Audit Query ───────────────────────────────────────
-- Run this manually to find any remaining unprotected tables:
--
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY rowsecurity ASC, tablename;
--
-- Every table should show rowsecurity = TRUE.
