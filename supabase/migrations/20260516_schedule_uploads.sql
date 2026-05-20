-- Meridian POS Intelligence — Schedule Uploads
-- Migration: 20260516_schedule_uploads
-- Creates the schedules storage bucket and schedule_uploads table

-- ─── Storage bucket for schedule uploads ───────────────────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'schedules',
  'schedules',
  false,
  10485760, -- 10 MB
  array['image/jpeg', 'image/png', 'image/heic', 'image/webp', 'application/pdf']
)
on conflict (id) do nothing;

-- ─── RLS policies for the schedules bucket ─────────────────

-- Business owners can upload schedule files scoped to their org_id prefix
create policy "schedule_upload_owner"
  on storage.objects for insert
  with check (
    bucket_id = 'schedules'
    and (storage.foldername(name))[1] in (
      select id from businesses where owner_user_id = auth.uid()
    )
  );

-- Business owners can read their own schedule files
create policy "schedule_read_owner"
  on storage.objects for select
  using (
    bucket_id = 'schedules'
    and (storage.foldername(name))[1] in (
      select id from businesses where owner_user_id = auth.uid()
    )
  );

-- Business owners can delete their own schedule files
create policy "schedule_delete_owner"
  on storage.objects for delete
  using (
    bucket_id = 'schedules'
    and (storage.foldername(name))[1] in (
      select id from businesses where owner_user_id = auth.uid()
    )
  );

-- ─── Scheduled Events table ────────────────────────────────
create table if not exists schedule_uploads (
  id uuid primary key default gen_random_uuid(),
  org_id text not null references businesses(id) on delete cascade,
  event_type text not null default 'schedule_upload',
  title text not null,
  notes text,
  file_path text,
  status text not null default 'pending_processing'
    check (status in ('pending_processing', 'processing', 'completed', 'failed')),
  created_at timestamptz not null default now()
);

create index if not exists idx_schedule_uploads_org on schedule_uploads(org_id);
create index if not exists idx_schedule_uploads_status on schedule_uploads(status)
  where status in ('pending_processing', 'processing');

-- ─── RLS for schedule_uploads ──────────────────────────────
alter table schedule_uploads enable row level security;

create policy "schedule_uploads_select_owner"
  on schedule_uploads for select
  using (org_id in (select id from businesses where owner_user_id = auth.uid()));

create policy "schedule_uploads_insert_owner"
  on schedule_uploads for insert
  with check (org_id in (select id from businesses where owner_user_id = auth.uid()));

create policy "schedule_uploads_update_owner"
  on schedule_uploads for update
  using (org_id in (select id from businesses where owner_user_id = auth.uid()));
