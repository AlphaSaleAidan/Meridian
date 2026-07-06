-- Zero-hardware camera connect (Path A: phone/tablet as camera).
-- Additive + idempotent: labels how a camera connects and stores a per-camera
-- HMAC token hash so a browser can post frames without a full JWT round-trip.
--
-- source values:
--   'rtsp'          existing IP/ONVIF camera (default; unchanged behavior)
--   'browser'       a phone/tablet running the /cam PWA page (Path A)
--   'cloud:<vendor>'a cloud-camera OAuth pull (Path C, future)

ALTER TABLE vision_cameras
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'rtsp';

ALTER TABLE vision_cameras
  ADD COLUMN IF NOT EXISTS placement TEXT;

-- sha256 of the per-camera frame token (never store the raw token).
ALTER TABLE vision_cameras
  ADD COLUMN IF NOT EXISTS connect_token_hash TEXT;

COMMENT ON COLUMN vision_cameras.source IS
  'How this camera connects: rtsp | browser | cloud:<vendor>. Zero-hardware paths use browser/cloud.';
COMMENT ON COLUMN vision_cameras.connect_token_hash IS
  'sha256 of the per-camera frame-ingest token (Path A browser cameras). Raw token never stored.';
