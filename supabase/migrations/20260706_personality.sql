-- Agent personality (formality/upsell/humor/custom lines/brand keywords) —
-- previously UI-only theater; now persisted and rendered into the live prompt.
ALTER TABLE phone_agent_config ADD COLUMN IF NOT EXISTS personality JSONB;
