-- 053_chatbot_config.sql — Owner-customizable customer-facing chatbot (Workstream 1d)
--
-- One config row per org. The owner customizes business name/tone, allowed
-- topics, canned answers, and an escalation-to-human toggle. The send endpoint
-- (src/api/routes/chatbot.py) routes LLM calls through the existing LiteLLM
-- gateway (src/ai/llm_layer.py) and honors these settings + the shared rpm
-- guards.
--
-- ADDITIVE + REVERSIBLE. Rollback at the bottom.

create table if not exists chatbot_config (
  id uuid primary key default gen_random_uuid(),
  org_id text not null unique,       -- one config per org
  enabled boolean not null default false,
  business_name text not null default '',
  tone text not null default 'friendly'
    check (tone in ('friendly', 'professional', 'casual', 'formal')),
  greeting text not null default '',
  allowed_topics jsonb not null default '[]'::jsonb,   -- ["hours","menu","reservations"]
  canned_answers jsonb not null default '[]'::jsonb,   -- [{"q":"...","a":"..."}]
  escalation_to_human boolean not null default false,
  escalation_contact text not null default '',         -- phone/email shown on escalation
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_chatbot_config_org on chatbot_config(org_id);

-- ── Optional transcript log (for the merchant to review conversations) ───────
create table if not exists chatbot_messages (
  id uuid primary key default gen_random_uuid(),
  org_id text not null,
  session_id text not null,          -- opaque per-visitor conversation id
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  escalated boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_chatbot_messages_org
  on chatbot_messages(org_id, created_at desc);
create index if not exists idx_chatbot_messages_session
  on chatbot_messages(session_id, created_at asc);

-- ── RLS ────────────────────────────────────────────────────────────────────
-- Config is owner/member readable; the public send endpoint reads config via
-- the service role (bypasses RLS) so the widget on the merchant's own site can
-- fetch its bot without a user session. Writes (owner customization) go through
-- the service-role backend with an owner check.
alter table chatbot_config enable row level security;
alter table chatbot_messages enable row level security;

drop policy if exists "chatbot_config_member_read" on chatbot_config;
create policy "chatbot_config_member_read" on chatbot_config
  for select using (
    org_id in (select id from businesses where owner_user_id = auth.uid())
    or org_id in (
      select business_id from business_users
      where user_id = auth.uid() and is_active = true
    )
  );

drop policy if exists "chatbot_messages_member_read" on chatbot_messages;
create policy "chatbot_messages_member_read" on chatbot_messages
  for select using (
    org_id in (select id from businesses where owner_user_id = auth.uid())
    or org_id in (
      select business_id from business_users
      where user_id = auth.uid() and is_active = true
    )
  );

-- No authenticated write policies: owner customization + transcript writes go
-- through the service-role backend only.

-- ── ROLLBACK ───────────────────────────────────────────────────────────────
-- drop table if exists chatbot_messages;
-- drop table if exists chatbot_config;
