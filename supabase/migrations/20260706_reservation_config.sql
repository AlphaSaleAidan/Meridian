-- "Connect your reservation system" questionnaire storage:
-- {on_website: bool, website_url: text}. Read by the phone agent prompt.
ALTER TABLE phone_agent_config ADD COLUMN IF NOT EXISTS reservation_config JSONB;
