-- 030_camera_feature_toggles.sql
-- Per-camera tracking-feature toggles + live-view opt-in.
--
-- Merchants control which analyses the edge agent runs on each camera, and
-- whether live viewing (WebRTC) is enabled. The edge agent reads `features` from
-- the camera config and skips disabled analyses; the portal renders toggles.
--
-- Defaults are privacy-conservative: only anonymous person detection + zones on;
-- demographics / VIP face-matching / depth / live-view are OFF until the merchant
-- opts in (live-view transmits video off-site, unlike the analytics path).

ALTER TABLE vision_cameras
    ADD COLUMN IF NOT EXISTS features JSONB NOT NULL DEFAULT
    '{"detection":true,"zones":true,"demographics":false,"vip":false,"depth":false,"live_view":false}'::jsonb;

COMMENT ON COLUMN vision_cameras.features IS
    'Per-camera feature toggles the edge agent honors: detection, zones, demographics, vip, depth, live_view. Privacy-sensitive ones default off.';
