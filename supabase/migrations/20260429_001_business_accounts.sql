-- Meridian POS Intelligence — Business Account Schema
-- Migration: 20260429_001_business_accounts
-- Creates multi-tenant business infrastructure with RLS isolation

-- ─── Businesses ─────────────────────────────────────────────
create table if not exists businesses (
  id text primary key default ('biz_' || replace(gen_random_uuid()::text, '-', '')),
  name text not null,
  owner_name text not null,
  email text not null unique,
  phone text,
  business_type text not null default 'restaurant',
  plan_tier text not null default 'trial' check (plan_tier in ('trial', 'starter', 'growth', 'enterprise')),
  status text not null default 'pending' check (status in ('pending', 'active', 'suspended', 'churned')),
  access_token text unique,
  token_status text not null default 'pending' check (token_status in ('pending', 'redeemed', 'expired')),
  token_expires_at timestamptz,
  max_locations integer not null default 1,
  pos_provider text,
  stripe_customer_id text,
  onboarded boolean not null default false,
  welcome_tour_shown boolean not null default false,
  created_at timestamptz not null default now(),
  activated_at timestamptz,
  owner_user_id uuid references auth.users(id)
);

create index if not exists idx_businesses_owner on businesses(owner_user_id);
create index if not exists idx_businesses_token on businesses(access_token) where token_status = 'pending';
create index if not exists idx_businesses_email on businesses(email);

-- ─── Business Users (staff within a business) ──────────────
create table if not exists business_users (
  id uuid primary key default gen_random_uuid(),
  business_id text not null references businesses(id) on delete cascade,
  user_id uuid references auth.users(id),
  email text not null,
  full_name text,
  role text not null default 'staff' check (role in ('owner', 'manager', 'staff')),
  location_id text,
  is_active boolean not null default true,
  last_login_at timestamptz,
  login_count integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_business_users_biz on business_users(business_id);
create index if not exists idx_business_users_user on business_users(user_id);
create unique index if not exists idx_business_users_email_biz on business_users(business_id, email);

-- ─── Business Locations ─────────────────────────────────────
create table if not exists business_locations (
  id text primary key default ('loc_' || replace(gen_random_uuid()::text, '-', '')),
  business_id text not null references businesses(id) on delete cascade,
  name text not null,
  address text,
  city text,
  state text,
  zip text,
  timezone text not null default 'America/New_York',
  is_primary boolean not null default false,
  pos_connection_id text,
  created_at timestamptz not null default now()
);

create index if not exists idx_locations_biz on business_locations(business_id);

-- ─── Customer Sessions ──────────────────────────────────────
create table if not exists customer_sessions (
  id uuid primary key default gen_random_uuid(),
  business_user_id uuid not null references business_users(id) on delete cascade,
  session_token text not null unique,
  device_info jsonb,
  ip_address inet,
  remember_me boolean not null default false,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create index if not exists idx_sessions_user on customer_sessions(business_user_id);
create index if not exists idx_sessions_token on customer_sessions(session_token) where revoked_at is null;

-- ─── Onboarding Progress ────────────────────────────────────
create table if not exists onboarding_progress (
  id uuid primary key default gen_random_uuid(),
  business_id text not null references businesses(id) on delete cascade,
  step_name text not null check (step_name in (
    'account_created', 'token_sent', 'token_redeemed', 'onboarding_call_scheduled',
    'pos_connected', 'historical_import_started', 'historical_import_complete',
    'first_insights_generated', 'marked_active'
  )),
  completed_at timestamptz not null default now(),
  completed_by text,
  notes text
);

create index if not exists idx_onboarding_biz on onboarding_progress(business_id);
create unique index if not exists idx_onboarding_step on onboarding_progress(business_id, step_name);

-- ─── Support Tickets ────────────────────────────────────────
create table if not exists support_tickets (
  id uuid primary key default gen_random_uuid(),
  business_id text not null references businesses(id) on delete cascade,
  submitted_by uuid references business_users(id),
  subject text not null,
  description text,
  severity text not null default 'medium' check (severity in ('critical', 'high', 'medium', 'low')),
  status text not null default 'open' check (status in ('open', 'in_progress', 'waiting_customer', 'resolved', 'closed')),
  assigned_to text,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_tickets_biz on support_tickets(business_id);
create index if not exists idx_tickets_status on support_tickets(status) where status in ('open', 'in_progress');

-- ─── Login Attempts (security audit log) ────────────────────
create table if not exists login_attempts (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  ip_address inet,
  user_agent text,
  success boolean not null,
  failure_reason text,
  created_at timestamptz not null default now()
);

create index if not exists idx_login_email_time on login_attempts(email, created_at desc);
create index if not exists idx_login_ip_time on login_attempts(ip_address, created_at desc);

-- ─── Access Tokens (for sales-generated invites) ────────────
create table if not exists access_tokens (
  id uuid primary key default gen_random_uuid(),
  business_id text not null references businesses(id) on delete cascade,
  token text not null unique default ('mtk_' || encode(gen_random_bytes(16), 'hex')),
  created_by text,
  redeemed boolean not null default false,
  redeemed_at timestamptz,
  redeemed_by uuid references auth.users(id),
  expires_at timestamptz not null default (now() + interval '30 days'),
  created_at timestamptz not null default now()
);

create index if not exists idx_access_tokens_token on access_tokens(token) where redeemed = false;

-- ─── Row Level Security ─────────────────────────────────────

alter table businesses enable row level security;
alter table business_users enable row level security;
alter table business_locations enable row level security;
alter table customer_sessions enable row level security;
alter table onboarding_progress enable row level security;
alter table support_tickets enable row level security;

-- Business owners can see their own business
create policy "business_owner_select" on businesses
  for select using (owner_user_id = auth.uid());

create policy "business_owner_update" on businesses
  for update using (owner_user_id = auth.uid());

-- Business users can see their own business data
create policy "business_users_select" on business_users
  for select using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
    or user_id = auth.uid()
  );

create policy "business_users_insert" on business_users
  for insert with check (
    business_id in (select id from businesses where owner_user_id = auth.uid())
  );

-- Locations visible to business members
create policy "locations_select" on business_locations
  for select using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
    or business_id in (select business_id from business_users where user_id = auth.uid())
  );

-- Sessions: users can only see their own
create policy "sessions_own" on customer_sessions
  for select using (
    business_user_id in (select id from business_users where user_id = auth.uid())
  );

-- Onboarding: visible to business owner
create policy "onboarding_select" on onboarding_progress
  for select using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
  );

-- Tickets: visible to business members
create policy "tickets_select" on support_tickets
  for select using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
    or business_id in (select business_id from business_users where user_id = auth.uid())
  );

create policy "tickets_insert" on support_tickets
  for insert with check (
    business_id in (select id from businesses where owner_user_id = auth.uid())
    or business_id in (select business_id from business_users where user_id = auth.uid())
  );

-- ─── Functions ──────────────────────────────────────────────

-- Rate limit check: returns true if too many failed attempts
create or replace function check_login_rate_limit(check_email text, check_ip inet)
returns boolean as $$
  select count(*) >= 5
  from login_attempts
  where (email = check_email or ip_address = check_ip)
    and success = false
    and created_at > now() - interval '15 minutes';
$$ language sql stable security definer;

-- Redeem access token: validates and marks as used
create or replace function redeem_access_token(input_token text, redeeming_user_id uuid)
returns text as $$
declare
  token_record record;
begin
  select * into token_record
  from access_tokens
  where token = input_token
    and redeemed = false
    and expires_at > now();

  if not found then
    return null;
  end if;

  update access_tokens
  set redeemed = true, redeemed_at = now(), redeemed_by = redeeming_user_id
  where id = token_record.id;

  update businesses
  set token_status = 'redeemed', activated_at = now(), status = 'active'
  where id = token_record.business_id;

  insert into onboarding_progress (business_id, step_name, completed_by)
  values (token_record.business_id, 'token_redeemed', redeeming_user_id::text);

  return token_record.business_id;
end;
$$ language plpgsql security definer;
