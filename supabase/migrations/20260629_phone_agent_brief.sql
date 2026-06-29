-- Migration: 20260629_phone_agent_brief.sql
-- Adds per-restaurant personalization brief fields to phone_agent_config.
--
-- Additive + idempotent: ADD COLUMN IF NOT EXISTS means this is safe to run
-- multiple times and does not touch existing rows or columns.
--
-- DO NOT apply to production — reviewed PR only.

ALTER TABLE phone_agent_config
  ADD COLUMN IF NOT EXISTS website_url        TEXT,
  ADD COLUMN IF NOT EXISTS restaurant_brief   TEXT,
  ADD COLUMN IF NOT EXISTS brief_updated_at   TIMESTAMPTZ;

COMMENT ON COLUMN phone_agent_config.website_url IS
  'Public URL of the restaurant website. Used by POST /api/phone/build-brief/{merchant_id} '
  'to fetch content for the personalization brief.';

COMMENT ON COLUMN phone_agent_config.restaurant_brief IS
  'AI-generated ≤120-word prose brief about the restaurant, built from website + menu '
  '(and optionally reviews in a future phase). Injected into the phone agent system prompt '
  'for tone, warmth, and item recommendations. '
  'Generated on demand via POST /api/phone/build-brief/{merchant_id}. '
  'Empty string = no brief = prompt is byte-for-byte unchanged (no regression).';

COMMENT ON COLUMN phone_agent_config.brief_updated_at IS
  'Timestamp of the last successful brief generation. NULL = never generated.';
