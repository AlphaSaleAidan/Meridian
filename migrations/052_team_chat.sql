-- 052_team_chat.sql — Internal team chat for Team Management (Workstream 1d)
--
-- Org-scoped channels + messages. Members read/post to their OWN org only.
-- org_id is the canonical business identifier (businesses.id). Enforcement is
-- server-side (src/api/routes/team_chat.py + rbac.py) plus the RLS below, which
-- fails closed to the caller's own org memberships.
--
-- ADDITIVE + REVERSIBLE. Rollback at the bottom.

create table if not exists team_channels (
  id uuid primary key default gen_random_uuid(),
  org_id text not null,
  name text not null,
  description text not null default '',
  is_default boolean not null default false,
  created_by uuid,                   -- auth.users.id
  archived boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_team_channels_org
  on team_channels(org_id) where archived = false;
-- One channel name per org.
create unique index if not exists idx_team_channels_org_name
  on team_channels(org_id, lower(name));

create table if not exists team_messages (
  id uuid primary key default gen_random_uuid(),
  org_id text not null,              -- denormalized for cheap org-scoped RLS
  channel_id uuid not null references team_channels(id) on delete cascade,
  author_user_id uuid,               -- auth.users.id
  author_member_id uuid,             -- business_users.id (roster identity)
  author_name text not null default '',
  body text not null,
  deleted boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_team_messages_channel
  on team_messages(channel_id, created_at desc);
create index if not exists idx_team_messages_org
  on team_messages(org_id, created_at desc);

-- ── RLS ────────────────────────────────────────────────────────────────────
alter table team_channels enable row level security;
alter table team_messages enable row level security;

-- Membership helper predicate (inline): caller owns the org OR is an active
-- business_users member of it.
drop policy if exists "team_channels_member_read" on team_channels;
create policy "team_channels_member_read" on team_channels
  for select using (
    org_id in (select id from businesses where owner_user_id = auth.uid())
    or org_id in (
      select business_id from business_users
      where user_id = auth.uid() and is_active = true
    )
  );

drop policy if exists "team_messages_member_read" on team_messages;
create policy "team_messages_member_read" on team_messages
  for select using (
    org_id in (select id from businesses where owner_user_id = auth.uid())
    or org_id in (
      select business_id from business_users
      where user_id = auth.uid() and is_active = true
    )
  );

-- Members may post to their own org's channels (INSERT). The WITH CHECK ties the
-- row's org to a caller membership AND ties author_user_id to the caller so a
-- member cannot post as someone else or into another org.
drop policy if exists "team_messages_member_insert" on team_messages;
create policy "team_messages_member_insert" on team_messages
  for insert with check (
    author_user_id = auth.uid()
    and (
      org_id in (select id from businesses where owner_user_id = auth.uid())
      or org_id in (
        select business_id from business_users
        where user_id = auth.uid() and is_active = true
      )
    )
  );

-- No UPDATE/DELETE authenticated policies: message edits/soft-deletes go through
-- the service-role backend (author-or-owner check applied there).

-- ── ROLLBACK ───────────────────────────────────────────────────────────────
-- drop table if exists team_messages;
-- drop table if exists team_channels;
