-- 031_camera_live_view.sql
-- On-demand live-view plumbing per camera (Cloudflare Stream WHIP/WHEP).
--
-- When a merchant opens a camera's live view, the backend ensures a Cloudflare
-- Live Input exists (stored here) and stamps live_requested_at. The edge agent
-- polls live-state and WHIP-publishes only while a recent request is active —
-- so we pay Cloudflare only while someone is actually watching (zero idle).

ALTER TABLE vision_cameras
    ADD COLUMN IF NOT EXISTS live_input_uid    TEXT,    -- Cloudflare Live Input uid
    ADD COLUMN IF NOT EXISTS live_whip_url     TEXT,    -- edge publishes RTSP→here (WHIP)
    ADD COLUMN IF NOT EXISTS live_whep_url     TEXT,    -- browser plays from here (WHEP)
    ADD COLUMN IF NOT EXISTS live_requested_at TIMESTAMPTZ;  -- last viewer "keep streaming" ping

COMMENT ON COLUMN vision_cameras.live_requested_at IS
    'Set to now() each time a viewer requests/keeps the live stream. The edge publishes only while this is recent (on-demand → no idle cost).';
