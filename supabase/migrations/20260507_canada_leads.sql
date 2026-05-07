create table if not exists canada_leads (
  id uuid primary key default gen_random_uuid(),
  business_name text not null,
  contact_name text not null,
  contact_email text not null,
  contact_phone text default '',
  vertical text default '',
  stage text not null default 'prospecting'
    check (stage in ('prospecting','contacted','demo_scheduled','proposal_sent','negotiation','closed_won','closed_lost')),
  monthly_value integer not null default 0,
  commission_rate integer not null default 35,
  expected_close_date date,
  notes text default '',
  source text default '',
  city text default '',
  province text default '',
  rep_id uuid references sales_reps(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_canada_leads_rep on canada_leads(rep_id);
create index if not exists idx_canada_leads_stage on canada_leads(stage);

alter table canada_leads enable row level security;

create policy "Sales reps can read their own leads"
  on canada_leads for select
  using (auth.uid()::text = rep_id::text or rep_id is null);

create policy "Sales reps can insert leads"
  on canada_leads for insert
  with check (true);

create policy "Sales reps can update their own leads"
  on canada_leads for update
  using (auth.uid()::text = rep_id::text or rep_id is null);
