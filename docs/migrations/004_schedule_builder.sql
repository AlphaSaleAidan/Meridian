-- REQUIRES APPROVAL FROM AIDAN PIERCE BEFORE RUNNING IN PRODUCTION
--
-- Schedule Builder tables for Meridian merchant portal.
-- Supports both US and Canada portals via portal_context column.

-- ─── Staff Members ───────────────────────────────────────────
create table if not exists staff_members (
  id            uuid primary key default gen_random_uuid(),
  merchant_id   uuid not null references merchants(id) on delete cascade,
  portal_context text not null default 'us' check (portal_context in ('us', 'ca')),
  name          text not null,
  role          text not null,
  color         text not null default '#17C5B0',
  hourly_rate   integer default 0,  -- cents
  availability  jsonb not null default '{}'::jsonb,
  active        boolean not null default true,
  created_at    timestamptz not null default now()
);

create index idx_staff_members_merchant on staff_members(merchant_id);

alter table staff_members enable row level security;
create policy staff_members_merchant_access on staff_members
  using (merchant_id = current_setting('app.merchant_id')::uuid)
  with check (merchant_id = current_setting('app.merchant_id')::uuid);


-- ─── Schedule Shifts ─────────────────────────────────────────
create table if not exists schedule_shifts (
  id              uuid primary key default gen_random_uuid(),
  merchant_id     uuid not null references merchants(id) on delete cascade,
  portal_context  text not null default 'us' check (portal_context in ('us', 'ca')),
  staff_member_id uuid references staff_members(id) on delete set null,
  week_start_date date not null,
  day_of_week     integer not null check (day_of_week between 0 and 6),
  shift_date      date not null,
  start_time      time not null,
  end_time        time not null,
  role            text not null,
  break_minutes   integer not null default 0,
  notes           text not null default '',
  status          text not null default 'draft' check (status in ('draft', 'published', 'confirmed', 'no_show')),
  is_recommended  boolean not null default false,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index idx_schedule_shifts_merchant_week on schedule_shifts(merchant_id, week_start_date);
create index idx_schedule_shifts_staff on schedule_shifts(staff_member_id);

alter table schedule_shifts enable row level security;
create policy schedule_shifts_merchant_access on schedule_shifts
  using (merchant_id = current_setting('app.merchant_id')::uuid)
  with check (merchant_id = current_setting('app.merchant_id')::uuid);


-- ─── Published Schedules ─────────────────────────────────────
create table if not exists published_schedules (
  id              uuid primary key default gen_random_uuid(),
  merchant_id     uuid not null references merchants(id) on delete cascade,
  portal_context  text not null default 'us' check (portal_context in ('us', 'ca')),
  week_start_date date not null,
  published_at    timestamptz not null default now(),
  published_by    text not null default '',
  total_hours     numeric(8,2) not null default 0,
  total_labor_cost integer not null default 0,  -- cents
  status          text not null default 'draft' check (status in ('draft', 'published')),
  unique (merchant_id, week_start_date)
);

create index idx_published_schedules_merchant on published_schedules(merchant_id);

alter table published_schedules enable row level security;
create policy published_schedules_merchant_access on published_schedules
  using (merchant_id = current_setting('app.merchant_id')::uuid)
  with check (merchant_id = current_setting('app.merchant_id')::uuid);


-- ─── Holidays ────────────────────────────────────────────────
create table if not exists holidays (
  id                        uuid primary key default gen_random_uuid(),
  country_code              text not null check (country_code in ('US', 'CA')),
  province_or_state         text,
  holiday_date              date not null,
  holiday_name              text not null,
  holiday_type              text not null check (holiday_type in ('federal', 'provincial', 'observance', 'retail_peak')),
  expected_traffic_multiplier numeric(3,1) not null default 1.0,
  notes                     text not null default ''
);

create index idx_holidays_date on holidays(holiday_date);
create index idx_holidays_country on holidays(country_code);


-- ─── Seed: US Federal Holidays 2025–2026 ─────────────────────
insert into holidays (country_code, holiday_date, holiday_name, holiday_type, expected_traffic_multiplier, notes) values
  -- 2025
  ('US', '2025-01-01', 'New Year''s Day',     'federal', 0.6, 'Many businesses closed or reduced hours'),
  ('US', '2025-01-20', 'Martin Luther King Jr. Day', 'federal', 0.8, ''),
  ('US', '2025-02-17', 'Presidents'' Day',    'federal', 0.9, ''),
  ('US', '2025-05-26', 'Memorial Day',        'federal', 0.7, 'Start of summer season'),
  ('US', '2025-07-04', 'Independence Day',    'federal', 0.5, 'Most businesses closed'),
  ('US', '2025-09-01', 'Labor Day',           'federal', 0.7, 'End of summer season'),
  ('US', '2025-10-13', 'Columbus Day',        'federal', 0.9, ''),
  ('US', '2025-11-11', 'Veterans Day',        'federal', 0.9, ''),
  ('US', '2025-11-27', 'Thanksgiving Day',    'federal', 0.3, 'Most businesses closed'),
  ('US', '2025-12-25', 'Christmas Day',       'federal', 0.2, 'Most businesses closed'),
  -- 2026
  ('US', '2026-01-01', 'New Year''s Day',     'federal', 0.6, ''),
  ('US', '2026-01-19', 'Martin Luther King Jr. Day', 'federal', 0.8, ''),
  ('US', '2026-02-16', 'Presidents'' Day',    'federal', 0.9, ''),
  ('US', '2026-05-25', 'Memorial Day',        'federal', 0.7, ''),
  ('US', '2026-07-04', 'Independence Day',    'federal', 0.5, ''),
  ('US', '2026-09-07', 'Labor Day',           'federal', 0.7, ''),
  ('US', '2026-10-12', 'Columbus Day',        'federal', 0.9, ''),
  ('US', '2026-11-11', 'Veterans Day',        'federal', 0.9, ''),
  ('US', '2026-11-26', 'Thanksgiving Day',    'federal', 0.3, ''),
  ('US', '2026-12-25', 'Christmas Day',       'federal', 0.2, '');


-- ─── Seed: US Retail Peak Days 2025–2026 ─────────────────────
insert into holidays (country_code, holiday_date, holiday_name, holiday_type, expected_traffic_multiplier, notes) values
  -- 2025
  ('US', '2025-02-14', 'Valentine''s Day',    'retail_peak', 1.5, 'Gift & dining surge'),
  ('US', '2025-05-11', 'Mother''s Day',       'retail_peak', 2.5, 'Highest brunch/dining day'),
  ('US', '2025-06-15', 'Father''s Day',       'retail_peak', 1.3, ''),
  ('US', '2025-11-28', 'Black Friday',        'retail_peak', 2.5, 'Biggest retail day of year'),
  ('US', '2025-12-24', 'Christmas Eve',       'retail_peak', 1.8, 'Last-minute shopping rush'),
  ('US', '2025-12-31', 'New Year''s Eve',     'retail_peak', 1.8, 'Evening/night spike'),
  -- 2026
  ('US', '2026-02-14', 'Valentine''s Day',    'retail_peak', 1.5, ''),
  ('US', '2026-05-10', 'Mother''s Day',       'retail_peak', 2.5, ''),
  ('US', '2026-06-21', 'Father''s Day',       'retail_peak', 1.3, ''),
  ('US', '2026-11-27', 'Black Friday',        'retail_peak', 2.5, ''),
  ('US', '2026-12-24', 'Christmas Eve',       'retail_peak', 1.8, ''),
  ('US', '2026-12-31', 'New Year''s Eve',     'retail_peak', 1.8, '');


-- ─── Seed: Canadian Federal Holidays 2025–2026 ───────────────
insert into holidays (country_code, holiday_date, holiday_name, holiday_type, expected_traffic_multiplier, notes) values
  -- 2025
  ('CA', '2025-01-01', 'New Year''s Day',     'federal', 0.6, ''),
  ('CA', '2025-04-18', 'Good Friday',         'federal', 0.5, ''),
  ('CA', '2025-05-19', 'Victoria Day',        'federal', 0.7, 'May long weekend'),
  ('CA', '2025-07-01', 'Canada Day',          'federal', 0.5, ''),
  ('CA', '2025-09-01', 'Labour Day',          'federal', 0.7, ''),
  ('CA', '2025-10-13', 'Thanksgiving',        'federal', 0.4, '2nd Monday of October'),
  ('CA', '2025-11-11', 'Remembrance Day',     'federal', 0.8, ''),
  ('CA', '2025-12-25', 'Christmas Day',       'federal', 0.2, ''),
  ('CA', '2025-12-26', 'Boxing Day',          'federal', 2.0, 'Major retail day'),
  -- 2026
  ('CA', '2026-01-01', 'New Year''s Day',     'federal', 0.6, ''),
  ('CA', '2026-04-03', 'Good Friday',         'federal', 0.5, ''),
  ('CA', '2026-05-18', 'Victoria Day',        'federal', 0.7, ''),
  ('CA', '2026-07-01', 'Canada Day',          'federal', 0.5, ''),
  ('CA', '2026-09-07', 'Labour Day',          'federal', 0.7, ''),
  ('CA', '2026-10-12', 'Thanksgiving',        'federal', 0.4, ''),
  ('CA', '2026-11-11', 'Remembrance Day',     'federal', 0.8, ''),
  ('CA', '2026-12-25', 'Christmas Day',       'federal', 0.2, ''),
  ('CA', '2026-12-26', 'Boxing Day',          'federal', 2.0, '');


-- ─── Seed: Canadian Provincial Holidays 2025–2026 ────────────
insert into holidays (country_code, province_or_state, holiday_date, holiday_name, holiday_type, expected_traffic_multiplier, notes) values
  -- 2025 Family Day (3rd Monday of February)
  ('CA', 'ON', '2025-02-17', 'Family Day',          'provincial', 0.8, 'Ontario'),
  ('CA', 'BC', '2025-02-17', 'Family Day',          'provincial', 0.8, 'British Columbia'),
  ('CA', 'AB', '2025-02-17', 'Family Day',          'provincial', 0.8, 'Alberta'),
  ('CA', 'SK', '2025-02-17', 'Family Day',          'provincial', 0.8, 'Saskatchewan'),
  -- 2025 St-Jean-Baptiste (June 24)
  ('CA', 'QC', '2025-06-24', 'St-Jean-Baptiste Day','provincial', 0.6, 'Quebec national holiday'),
  -- 2025 Civic Holiday (1st Monday of August)
  ('CA', 'ON', '2025-08-04', 'Civic Holiday',       'provincial', 0.8, 'Ontario — varies by municipality'),
  ('CA', 'BC', '2025-08-04', 'BC Day',              'provincial', 0.8, 'British Columbia'),
  ('CA', 'AB', '2025-08-04', 'Heritage Day',        'provincial', 0.8, 'Alberta'),

  -- 2026 Family Day (3rd Monday of February)
  ('CA', 'ON', '2026-02-16', 'Family Day',          'provincial', 0.8, 'Ontario'),
  ('CA', 'BC', '2026-02-16', 'Family Day',          'provincial', 0.8, 'British Columbia'),
  ('CA', 'AB', '2026-02-16', 'Family Day',          'provincial', 0.8, 'Alberta'),
  ('CA', 'SK', '2026-02-16', 'Family Day',          'provincial', 0.8, 'Saskatchewan'),
  -- 2026 St-Jean-Baptiste
  ('CA', 'QC', '2026-06-24', 'St-Jean-Baptiste Day','provincial', 0.6, 'Quebec national holiday'),
  -- 2026 Civic Holiday (1st Monday of August)
  ('CA', 'ON', '2026-08-03', 'Civic Holiday',       'provincial', 0.8, 'Ontario'),
  ('CA', 'BC', '2026-08-03', 'BC Day',              'provincial', 0.8, 'British Columbia'),
  ('CA', 'AB', '2026-08-03', 'Heritage Day',        'provincial', 0.8, 'Alberta');
