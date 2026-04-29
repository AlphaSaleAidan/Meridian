-- Meridian — Onboarding Gate + Admin Panel
-- Migration: 20260429_003_onboarding_admin

-- ─── POS connection columns ─────────────────────────────────
alter table businesses add column if not exists pos_api_key text;
alter table businesses add column if not exists pos_connected boolean not null default false;
alter table businesses add column if not exists pos_connected_at timestamptz;

-- ─── Admin users table ──────────────────────────────────────
create table if not exists admin_users (
  user_id uuid primary key references auth.users(id),
  email text not null,
  created_at timestamptz not null default now()
);

-- ─── Connect POS (customer-facing) ─────────────────────────
create or replace function connect_pos(p_provider text, p_api_key text)
returns void as $$
begin
  update businesses
  set pos_provider = p_provider,
      pos_api_key = p_api_key,
      pos_connected = true,
      pos_connected_at = now(),
      onboarded = true
  where owner_user_id = auth.uid();

  insert into onboarding_progress (business_id, step_name, completed_by)
  select id, 'pos_connected', auth.uid()::text
  from businesses where owner_user_id = auth.uid()
  on conflict (business_id, step_name) do nothing;
end;
$$ language plpgsql security definer;

-- ─── Admin check ────────────────────────────────────────────
create or replace function is_admin()
returns boolean as $$
  select exists (select 1 from admin_users where user_id = auth.uid());
$$ language sql stable security definer;

-- ─── Admin: list all businesses ─────────────────────────────
create or replace function admin_list_businesses()
returns jsonb as $$
begin
  if not (select is_admin()) then
    raise exception 'Not authorized';
  end if;

  return (
    select coalesce(jsonb_agg(jsonb_build_object(
      'id', b.id,
      'name', b.name,
      'owner_name', b.owner_name,
      'email', b.email,
      'business_type', b.business_type,
      'plan_tier', b.plan_tier,
      'status', b.status,
      'pos_provider', b.pos_provider,
      'pos_connected', b.pos_connected,
      'onboarded', b.onboarded,
      'created_at', b.created_at,
      'activated_at', b.activated_at
    ) order by b.created_at desc), '[]'::jsonb)
    from businesses b
  );
end;
$$ language plpgsql security definer;

-- ─── Admin: provision business (wraps existing function) ────
-- provision_business() already exists from migration 002

-- ─── Admin: generate new token for existing business ────────
create or replace function admin_generate_token(biz_id text)
returns jsonb as $$
declare
  new_token text;
begin
  if not (select is_admin()) then
    raise exception 'Not authorized';
  end if;

  insert into access_tokens (business_id, created_by)
  values (biz_id, 'admin')
  returning token into new_token;

  return jsonb_build_object(
    'token', new_token,
    'activation_url', 'https://meridian-dun-nu.vercel.app/portal?token=' || new_token
  );
end;
$$ language plpgsql security definer;

-- ─── Grants ─────────────────────────────────────────────────
grant execute on function connect_pos(text, text) to authenticated;
grant execute on function is_admin() to authenticated;
grant execute on function admin_list_businesses() to authenticated;
grant execute on function admin_generate_token(text) to authenticated;
