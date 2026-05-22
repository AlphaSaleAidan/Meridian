-- schedule_staff: staff roster per merchant
create table if not exists schedule_staff (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  portal_context text not null default 'us',
  name text not null,
  role text not null default 'any',
  color text not null default '#17C5B0',
  hourly_rate integer not null default 0,
  availability jsonb not null default '{}',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_schedule_staff_merchant on schedule_staff(merchant_id) where active = true;

-- schedule_shifts: individual shift assignments
create table if not exists schedule_shifts (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  portal_context text not null default 'us',
  staff_member_id uuid references schedule_staff(id) on delete set null,
  week_start_date date not null,
  day_of_week smallint not null check (day_of_week between 0 and 6),
  shift_date date not null,
  start_time time not null,
  end_time time not null,
  role text not null default 'any',
  break_minutes smallint not null default 0,
  notes text not null default '',
  status text not null default 'draft' check (status in ('draft', 'published', 'cancelled')),
  is_recommended boolean not null default false,
  recommendation_reason text,
  priority text check (priority in ('critical', 'recommended', 'optional')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_schedule_shifts_merchant_week on schedule_shifts(merchant_id, week_start_date);
create index idx_schedule_shifts_staff on schedule_shifts(staff_member_id) where staff_member_id is not null;

-- published_schedules: record of when a week was published
create table if not exists published_schedules (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null,
  week_start_date date not null,
  published_by text,
  published_at timestamptz not null default now(),
  notified_count integer not null default 0,
  unique(merchant_id, week_start_date)
);

-- RLS
alter table schedule_staff enable row level security;
alter table schedule_shifts enable row level security;
alter table published_schedules enable row level security;

-- Service role full access
create policy "schedule_staff_service" on schedule_staff for all using (true) with check (true);
create policy "schedule_shifts_service" on schedule_shifts for all using (true) with check (true);
create policy "published_schedules_service" on published_schedules for all using (true) with check (true);
