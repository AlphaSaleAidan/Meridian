-- Camera-connect: EXISTING-camera connection paths (vendor-cloud + LAN connector).
-- Additive + idempotent. Safe to run against a live vision_cameras table.
--
-- Adds:
--   vision_cameras.source            how the camera connects: 'rtsp' (legacy manual),
--                                    'onvif' (LAN connector auto-discovery),
--                                    'cloud:<vendor>' (vendor-cloud, e.g. 'cloud:tuya'),
--                                    'browser' (phone-as-camera fallback).
--   vision_cameras.connect_token_hash  optional per-camera relay token hash (audit).
--   camera_sites                     a site groups a merchant's cameras; the LAN connector
--                                    registers auto-discovered cameras under a site.

ALTER TABLE IF EXISTS vision_cameras
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'rtsp';

ALTER TABLE IF EXISTS vision_cameras
  ADD COLUMN IF NOT EXISTS connect_token_hash TEXT;

CREATE TABLE IF NOT EXISTS camera_sites (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL,
  name        TEXT NOT NULL DEFAULT 'Default site',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_camera_sites_org ON camera_sites (org_id);

-- RLS: tenant-scoped reads; writes go through the service-role client (connector +
-- vendor-cloud link both run server-side). Mirrors the vision_cameras posture.
ALTER TABLE camera_sites ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'camera_sites' AND policyname = 'camera_sites_org_read'
  ) THEN
    CREATE POLICY camera_sites_org_read ON camera_sites
      FOR SELECT USING (org_id::text = COALESCE(auth.jwt() ->> 'org_id', ''));
  END IF;
END $$;
