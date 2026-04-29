-- Meridian POS Intelligence — Deal Flow Functions
-- Migration: 20260429_002_deal_flow
-- Sales provisioning, token validation, and business creation

-- ─── Validate token (callable pre-auth via anon key) ───────
create or replace function validate_access_token(input_token text)
returns jsonb as $$
  select jsonb_build_object(
    'valid', true,
    'business_id', b.id,
    'business_name', b.name,
    'owner_name', b.owner_name,
    'email', b.email,
    'business_type', b.business_type
  )
  from access_tokens t
  join businesses b on b.id = t.business_id
  where t.token = input_token
    and t.redeemed = false
    and t.expires_at > now();
$$ language sql stable security definer;

-- ─── Updated redeem — also sets owner_user_id ──────────────
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
  set token_status = 'redeemed', activated_at = now(), status = 'active',
      owner_user_id = redeeming_user_id
  where id = token_record.business_id;

  insert into onboarding_progress (business_id, step_name, completed_by)
  values (token_record.business_id, 'token_redeemed', redeeming_user_id::text)
  on conflict (business_id, step_name) do nothing;

  return token_record.business_id;
end;
$$ language plpgsql security definer;

-- ─── Create business for direct signup (no token) ──────────
create or replace function create_business_for_user(
  user_id uuid,
  biz_name text,
  biz_owner_name text,
  biz_email text
)
returns text as $$
declare
  new_biz_id text;
begin
  insert into businesses (name, owner_name, email, owner_user_id, status)
  values (biz_name, biz_owner_name, biz_email, user_id, 'active')
  returning id into new_biz_id;

  insert into onboarding_progress (business_id, step_name, completed_by)
  values (new_biz_id, 'account_created', user_id::text);

  return new_biz_id;
end;
$$ language plpgsql security definer;

-- ─── Sales team provisioning ───────────────────────────────
-- Run from Supabase SQL Editor:
--   SELECT provision_business('Coffee House', 'Jane Doe', 'jane@coffee.com');
--   SELECT provision_business('Pizza Palace', 'Bob R.', 'bob@pizza.com', 'restaurant', 'starter');
create or replace function provision_business(
  biz_name text,
  biz_owner_name text,
  biz_email text,
  biz_type text default 'coffee_shop',
  biz_plan text default 'trial'
)
returns jsonb as $$
declare
  new_biz_id text;
  new_token text;
begin
  insert into businesses (name, owner_name, email, business_type, plan_tier)
  values (biz_name, biz_owner_name, biz_email, biz_type, biz_plan)
  returning id into new_biz_id;

  insert into access_tokens (business_id, created_by)
  values (new_biz_id, 'sales_team')
  returning token into new_token;

  insert into onboarding_progress (business_id, step_name, completed_by)
  values (new_biz_id, 'account_created', 'sales_team');

  insert into onboarding_progress (business_id, step_name, completed_by)
  values (new_biz_id, 'token_sent', 'sales_team');

  return jsonb_build_object(
    'business_id', new_biz_id,
    'token', new_token,
    'activation_url', 'https://meridian-dun-nu.vercel.app/portal?token=' || new_token
  );
end;
$$ language plpgsql security definer;

-- ─── RLS: allow business insert for authenticated users ────
do $$ begin
  if not exists (
    select 1 from pg_policies where policyname = 'business_insert_own' and tablename = 'businesses'
  ) then
    create policy "business_insert_own" on businesses
      for insert with check (owner_user_id = auth.uid());
  end if;
end $$;

-- ─── Grants ────────────────────────────────────────────────
grant execute on function validate_access_token(text) to anon, authenticated;
grant execute on function redeem_access_token(text, uuid) to anon, authenticated;
grant execute on function create_business_for_user(uuid, text, text, text) to anon, authenticated;
grant execute on function provision_business(text, text, text, text, text) to authenticated;
