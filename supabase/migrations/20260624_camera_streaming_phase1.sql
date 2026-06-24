-- Camera Streaming + Overlays — Phase 1: data model, tenancy, P0 fix, retention settings
-- Tenancy ground truth (verified against prod kbuzufjxwflrutowwnfl, 2026-06-24):
--   * vision_cameras.org_id is TEXT = businesses.id (the 20260501 organizations/UUID
--     variant did NOT win; 20260516's businesses variant is live, but with org_id TEXT).
--   * membership = business_users(business_id TEXT, user_id UUID, is_active BOOL).
--   * locations.org_id is UUID = organizations.id (a SEPARATE tenant model) — so the
--     surveillance retention columns simply attach to locations; no tenancy change there.
-- Streaming tables therefore use org_id TEXT -> businesses(id) to match the camera domain,
-- and reuse the existing vision_cameras table rather than create a 3rd cameras table.
-- Idempotent. Reviewed via PR; apply to prod only on explicit go.

-- Reusable membership predicate (a business the current user actively belongs to)
-- expressed inline per policy (Postgres has no parametric policy macros).

-- ============================================================
-- 0. P0 FIX — close the cross-tenant hole on the existing vision_* tables
--    (they currently carry only "FOR ALL USING (true)" — anon/authenticated can read
--    every tenant's data). service_role bypasses RLS, so the FastAPI path is unaffected.
-- ============================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['vision_cameras','vision_traffic','vision_visitors','vision_visits'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    -- drop the permissive holes (names from 20260516)
    EXECUTE format('DROP POLICY IF EXISTS "Service role full access on %s" ON %I', t, t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_member_isolation', t);
    -- members of the owning business can read; writes stay server-side (service_role).
    EXECUTE format($p$
      CREATE POLICY %I ON %I FOR SELECT TO authenticated
      USING (org_id IN (SELECT business_id FROM business_users
                        WHERE user_id = auth.uid() AND is_active IS TRUE))
    $p$, t || '_member_isolation', t);
  END LOOP;
END $$;

-- ============================================================
-- 1. camera_sites — a physical site grouping cameras (tenant-scoped)
-- ============================================================
CREATE TABLE IF NOT EXISTS camera_sites (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_camera_sites_org ON camera_sites(org_id);

-- reuse vision_cameras as the camera record; just group it under a site
ALTER TABLE vision_cameras ADD COLUMN IF NOT EXISTS site_id UUID REFERENCES camera_sites(id) ON DELETE SET NULL;

-- ============================================================
-- 2. camera_streams — per-camera live-stream state (gateway publishes here)
-- ============================================================
CREATE TABLE IF NOT EXISTS camera_streams (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  camera_id   UUID NOT NULL REFERENCES vision_cameras(id) ON DELETE CASCADE,
  stream_name TEXT NOT NULL,                       -- MediaMTX path
  protocol    TEXT NOT NULL DEFAULT 'webrtc' CHECK (protocol IN ('webrtc','hls','rtsp')),
  status      TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle','live','error')),
  whep_url    TEXT,
  hls_url     TEXT,
  last_seen   TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_camera_streams_org ON camera_streams(org_id);
CREATE INDEX IF NOT EXISTS idx_camera_streams_camera ON camera_streams(camera_id);

-- ============================================================
-- 3. stream_tokens — short-lived (<=60s) single-camera view JWTs (audit record)
-- ============================================================
CREATE TABLE IF NOT EXISTS stream_tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  camera_id   UUID NOT NULL REFERENCES vision_cameras(id) ON DELETE CASCADE,
  token_hash  TEXT NOT NULL,                       -- store a hash, never the raw token
  issued_to   UUID,                                -- auth.uid() of the viewer
  expires_at  TIMESTAMPTZ NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stream_tokens_org ON stream_tokens(org_id);
CREATE INDEX IF NOT EXISTS idx_stream_tokens_expires ON stream_tokens(expires_at);

-- ============================================================
-- 4. user_overlay_prefs — per user + camera overlay-layer toggles
-- ============================================================
CREATE TABLE IF NOT EXISTS user_overlay_prefs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL,
  camera_id  UUID NOT NULL REFERENCES vision_cameras(id) ON DELETE CASCADE,
  layers     JSONB NOT NULL DEFAULT '{}',          -- {detections:true, zones:true, ...}
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, camera_id)
);
CREATE INDEX IF NOT EXISTS idx_user_overlay_prefs_org ON user_overlay_prefs(org_id);

-- ============================================================
-- 5. RLS for the new tables — same membership model as the camera domain
-- ============================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['camera_sites','camera_streams','stream_tokens'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_member_isolation', t);
    EXECUTE format($p$
      CREATE POLICY %I ON %I FOR SELECT TO authenticated
      USING (org_id IN (SELECT business_id FROM business_users
                        WHERE user_id = auth.uid() AND is_active IS TRUE))
    $p$, t || '_member_isolation', t);
  END LOOP;
END $$;

-- overlay prefs: a user sees/writes only their OWN prefs within a business they belong to
ALTER TABLE user_overlay_prefs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_overlay_prefs_owner ON user_overlay_prefs;
CREATE POLICY user_overlay_prefs_owner ON user_overlay_prefs FOR ALL TO authenticated
  USING (user_id = auth.uid()
         AND org_id IN (SELECT business_id FROM business_users
                        WHERE user_id = auth.uid() AND is_active IS TRUE))
  WITH CHECK (user_id = auth.uid()
         AND org_id IN (SELECT business_id FROM business_users
                        WHERE user_id = auth.uid() AND is_active IS TRUE));

-- ============================================================
-- 6. Per-location surveillance retention (province floor enforced in Phase 7)
--    locations.state holds the province; default to the strictest-unknown floor (60d).
-- ============================================================
ALTER TABLE locations ADD COLUMN IF NOT EXISTS surveillance_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE locations ADD COLUMN IF NOT EXISTS surveillance_retention_days INTEGER NOT NULL DEFAULT 60;
