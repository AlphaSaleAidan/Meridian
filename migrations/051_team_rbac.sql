-- 051_team_rbac.sql — Employee auth + 3-role RBAC for Team Management (Workstream 1c/1e)
--
-- Extends the EXISTING business_users membership table (20260429_001_business_accounts.sql)
-- rather than introducing a parallel table. business_users already carries
-- (id, business_id, user_id, email, full_name, role, is_active). We:
--   1. widen the role CHECK to the canonical 3 roles (owner/manager/employee)
--      while keeping the legacy 'staff' value valid so existing rows don't break,
--   2. add a structured `permissions` jsonb (nothing default-granted — managers
--      get exactly what the owner ticks; employees get an empty object),
--   3. add invite bookkeeping columns (invited_by / invited_at / invite_status),
--   4. add an append-only audit table for permission/role changes.
--
-- Enforcement is server-side (route guards in src/api/rbac.py) + RLS below.
-- org_id is ALWAYS the authenticated business_id — never trusted from a body.
--
-- ADDITIVE + REVERSIBLE. Rollback section at the bottom.
--
-- NOTE: Apply with a Supabase snapshot in place (main session manages that).
-- DO NOT apply directly to prod without coordination.

-- ── 1. Role vocabulary + permissions object ────────────────────────────────
-- Legacy rows used role in ('owner','manager','staff'). We introduce 'employee'
-- as the canonical third role but keep 'staff' accepted (treated as employee by
-- the app layer) so no historical row violates the constraint.
alter table business_users
  drop constraint if exists business_users_role_check;
alter table business_users
  add constraint business_users_role_check
  check (role in ('owner', 'manager', 'employee', 'staff'));

alter table business_users
  add column if not exists permissions jsonb not null default '{}'::jsonb;

alter table business_users
  add column if not exists invited_by uuid references auth.users(id);
alter table business_users
  add column if not exists invited_at timestamptz;
alter table business_users
  add column if not exists invite_status text not null default 'active'
    check (invite_status in ('pending', 'active', 'revoked'));

comment on column business_users.permissions is
  'Structured RBAC object: {"visibility": {"financials": bool, ...}, "actions": {"edit_schedule": bool, ...}}. Empty = nothing granted. Owners bypass this object entirely (full access).';

-- ── 2. Append-only audit of role/permission changes ────────────────────────
create table if not exists business_user_audit (
  id uuid primary key default gen_random_uuid(),
  business_id text not null references businesses(id) on delete cascade,
  target_user_id uuid,          -- the business_users.user_id whose access changed
  target_member_id uuid,        -- the business_users.id row
  actor_user_id uuid,           -- auth.users.id who made the change
  actor_email text,
  action text not null,         -- 'create' | 'role_change' | 'permissions_change' | 'deactivate' | 'reactivate' | 'invite_sent'
  old_value jsonb,
  new_value jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_business_user_audit_biz
  on business_user_audit(business_id, created_at desc);

-- ── 3. RLS ─────────────────────────────────────────────────────────────────
-- business_users RLS already exists (owner + self select, owner insert). We add
-- UPDATE/DELETE scoped to the owner, and self-visibility of one's own row, then
-- lock the audit table to owner-read + service-write.

alter table business_user_audit enable row level security;

-- The service role (backend) bypasses RLS. These policies constrain any
-- ANON/AUTHENTICATED direct PostgREST access to fail closed to the owning org.

drop policy if exists "business_users_owner_update" on business_users;
create policy "business_users_owner_update" on business_users
  for update using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
  )
  with check (
    business_id in (select id from businesses where owner_user_id = auth.uid())
  );

drop policy if exists "business_users_owner_delete" on business_users;
create policy "business_users_owner_delete" on business_users
  for delete using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
  );

-- Audit rows are readable only by the owning business owner; writes come from
-- the service role (which bypasses RLS). No authenticated INSERT policy => an
-- ordinary member cannot forge audit rows.
drop policy if exists "business_user_audit_owner_read" on business_user_audit;
create policy "business_user_audit_owner_read" on business_user_audit
  for select using (
    business_id in (select id from businesses where owner_user_id = auth.uid())
  );

-- ── ROLLBACK ───────────────────────────────────────────────────────────────
-- drop table if exists business_user_audit;
-- alter table business_users drop column if exists invite_status;
-- alter table business_users drop column if exists invited_at;
-- alter table business_users drop column if exists invited_by;
-- alter table business_users drop column if exists permissions;
-- alter table business_users drop constraint if exists business_users_role_check;
-- alter table business_users add constraint business_users_role_check
--   check (role in ('owner','manager','staff'));
-- drop policy if exists "business_users_owner_update" on business_users;
-- drop policy if exists "business_users_owner_delete" on business_users;
