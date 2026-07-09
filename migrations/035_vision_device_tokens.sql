-- Per-org device tokens for the vision ingest / camera-connector path.
--
-- Why: metric ingest (POST /api/vision/ingest/*) is a HEADLESS DEVICE call — an
-- on-site PC/POS agent or the LAN connector, not a logged-in browser. Those
-- devices can't hold a Supabase user JWT. Before this, ingest was double-guarded
-- by require_org_access (JWT) AND a single global VISION_INGEST_TOKEN, so no
-- device could actually push data, and the one shared token let any device write
-- to any org. This table issues a UNIQUE token per org (optionally per site) whose
-- sha256 hash is stored here; the raw token lives only on the device.
--
-- Additive + idempotent. Service-role writes only (tokens are secrets).

CREATE TABLE IF NOT EXISTS vision_device_tokens (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       UUID NOT NULL,
  site_id      UUID,                         -- optional: bind a token to one camera_sites row
  token_hash   TEXT NOT NULL UNIQUE,         -- sha256(raw token); raw is never stored
  label        TEXT,                         -- human hint e.g. "Back-office PC", "Store #3 connector"
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ,
  revoked      BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_vision_device_tokens_hash ON vision_device_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_vision_device_tokens_org  ON vision_device_tokens (org_id);

-- RLS on: device tokens are secrets. No tenant SELECT policy — only the
-- service-role client (which bypasses RLS) reads/writes them. Mirrors the
-- vision_cameras / camera_sites posture.
ALTER TABLE vision_device_tokens ENABLE ROW LEVEL SECURITY;
