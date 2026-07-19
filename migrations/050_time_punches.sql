-- 050_time_punches.sql — Time clock (clock-in / clock-out) for Team Management (Workstream 1b)
--
-- Records ACTUAL hours worked, shown side-by-side with SCHEDULED hours on the
-- schedule view. Owners/managers with the `edit_punches` permission can correct
-- a punch; every correction is audit-logged (edited_by + edit_reason on the row
-- PLUS an append-only time_punch_audit row).
--
-- org_id is the canonical business identifier (businesses.id — text, e.g. biz_…,
-- but also accepts a bare UUID like the rest of the app). employee_id references
-- the existing schedule_staff roster (uuid). Enforcement is server-side
-- (src/api/routes/time_clock.py + rbac.py) plus the RLS below.
--
-- ADDITIVE + REVERSIBLE. Rollback at the bottom.
--
-- NOTE: Apply with a Supabase snapshot in place (main session manages that).

create table if not exists time_punches (
  id uuid primary key default gen_random_uuid(),
  org_id text not null,
  employee_id uuid not null references schedule_staff(id) on delete cascade,
  clock_in_at timestamptz not null,
  clock_out_at timestamptz,          -- null while a shift is open (still clocked in)
  source text not null default 'manual'
    check (source in ('manual', 'kiosk', 'mobile', 'auto', 'import')),
  edited_by uuid,                    -- auth.users.id of the last corrector (null if untouched)
  edit_reason text,                  -- required when edited_by is set (app-enforced)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- A clock-out cannot precede the clock-in.
  constraint time_punches_interval_valid
    check (clock_out_at is null or clock_out_at >= clock_in_at)
);

create index if not exists idx_time_punches_org
  on time_punches(org_id, clock_in_at desc);
create index if not exists idx_time_punches_employee
  on time_punches(employee_id, clock_in_at desc);
-- At most one OPEN punch (clock_out_at is null) per employee — you can't be
-- clocked in twice at once.
create unique index if not exists idx_time_punches_one_open
  on time_punches(employee_id) where clock_out_at is null;

-- ── Append-only correction audit ───────────────────────────────────────────
create table if not exists time_punch_audit (
  id uuid primary key default gen_random_uuid(),
  punch_id uuid not null,            -- not FK: audit survives punch deletion
  org_id text not null,
  actor_user_id uuid,
  actor_email text,
  action text not null,              -- 'edit' | 'delete' | 'insert'
  edit_reason text,
  old_value jsonb,
  new_value jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_time_punch_audit_punch
  on time_punch_audit(punch_id, created_at desc);
create index if not exists idx_time_punch_audit_org
  on time_punch_audit(org_id, created_at desc);

-- ── RLS ────────────────────────────────────────────────────────────────────
-- The backend uses the service role (bypasses RLS) and enforces org-scope +
-- permission in src/api/rbac.py. These policies constrain any direct
-- ANON/AUTHENTICATED PostgREST access to fail closed to the owning org.
alter table time_punches enable row level security;
alter table time_punch_audit enable row level security;

-- Members of the org (owner or business_users row) may read their org's punches.
-- Cross-org reads are impossible (the subqueries only resolve the caller's own
-- org memberships).
drop policy if exists "time_punches_org_read" on time_punches;
create policy "time_punches_org_read" on time_punches
  for select using (
    org_id in (select id from businesses where owner_user_id = auth.uid())
    or org_id in (
      select business_id from business_users
      where user_id = auth.uid() and is_active = true
    )
  );

-- No authenticated INSERT/UPDATE/DELETE policies: mutations go through the
-- service-role backend only, which applies the RBAC permission check. This
-- prevents a logged-in employee from editing punches directly via PostgREST.

drop policy if exists "time_punch_audit_org_read" on time_punch_audit;
create policy "time_punch_audit_org_read" on time_punch_audit
  for select using (
    org_id in (select id from businesses where owner_user_id = auth.uid())
    or org_id in (
      select business_id from business_users
      where user_id = auth.uid() and is_active = true
    )
  );

-- ── ROLLBACK ───────────────────────────────────────────────────────────────
-- drop table if exists time_punch_audit;
-- drop table if exists time_punches;
