-- 024_phone_streaming_enabled.sql
-- Per-merchant opt-in for the pipecat streaming voice path (Nemotron ASR/TTS).
--
-- The turn-based Twilio-Gather path remains the default for every merchant.
-- A call only routes to the streaming Pipecat sidecar when BOTH the global
-- MEDIA_STREAMS_ENABLED env flag is on AND this column is true for the merchant,
-- so streaming can be rolled out one opt-in merchant at a time and instantly
-- rolled back per merchant by flipping this flag (or globally via the env flag).
--
-- Safe to apply anytime: additive, defaults to false (no behavior change).

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS streaming_enabled boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN phone_agent_config.streaming_enabled IS
    'Opt-in: route this merchant''s calls to the pipecat streaming voice pipeline '
    '(Nemotron ASR + Magpie TTS) instead of the turn-based path. Requires the '
    'server-side MEDIA_STREAMS_ENABLED flag to also be on. Default false.';
