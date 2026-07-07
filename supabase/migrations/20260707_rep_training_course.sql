-- Meridian — Rep Training Course: progress, quiz results, Code of Conduct
-- signatures, and the lead-creation training lock.
--
-- Reps authenticate with Supabase auth but their sales_reps row is matched by
-- EMAIL, not auth.uid() (see 20260511_fix_canada_leads_rls.sql — auth.uid()
-- never equals sales_reps.id). All row ownership here is therefore keyed on
-- lower(auth.jwt()->>'email').
--
-- APPLY NOTE (read before running against prod):
--   The final policy swap locks lead creation for every rep who has not
--   completed the course. If reps are actively selling when this lands,
--   either have them complete the course first or run the grandfather block
--   at the bottom to seed completion for existing reps.

-- ─── Per-module progress ─────────────────────────────────────
create table if not exists rep_training_progress (
  id uuid primary key default gen_random_uuid(),
  rep_id uuid references sales_reps(id) on delete cascade,
  rep_email text not null check (rep_email = lower(rep_email)),
  module_id text not null,
  video_watched boolean not null default false,
  video_watched_at timestamptz,
  attempts integer not null default 0,
  best_score integer,
  quiz_total integer not null default 10,
  passed boolean not null default false,
  passed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (rep_email, module_id)
);

alter table rep_training_progress enable row level security;

create policy "reps read own training progress"
  on rep_training_progress for select
  using (rep_email = lower(auth.jwt() ->> 'email'));

create policy "reps insert own training progress"
  on rep_training_progress for insert
  with check (rep_email = lower(auth.jwt() ->> 'email'));

create policy "reps update own training progress"
  on rep_training_progress for update
  using (rep_email = lower(auth.jwt() ->> 'email'))
  with check (rep_email = lower(auth.jwt() ->> 'email'));

grant select, insert, update on rep_training_progress to authenticated;

-- ─── Code of Conduct signatures (immutable: no update/delete) ─
create table if not exists rep_conduct_signatures (
  id uuid primary key default gen_random_uuid(),
  rep_id uuid references sales_reps(id) on delete cascade,
  rep_email text not null check (rep_email = lower(rep_email)),
  signed_name text not null check (length(trim(signed_name)) >= 2),
  conduct_version text not null,
  signed_at timestamptz not null default now(),
  unique (rep_email, conduct_version)
);

alter table rep_conduct_signatures enable row level security;

create policy "reps read own conduct signature"
  on rep_conduct_signatures for select
  using (rep_email = lower(auth.jwt() ->> 'email'));

create policy "reps insert own conduct signature"
  on rep_conduct_signatures for insert
  with check (rep_email = lower(auth.jwt() ->> 'email'));

grant select, insert on rep_conduct_signatures to authenticated;

-- ─── Course-complete check ───────────────────────────────────
-- Complete = all five modules passed AND the Code of Conduct signed (any
-- version — re-signing is forced from the app when the version bumps, but an
-- old signature must not retroactively lock a rep out of lead creation).
create or replace function rep_training_complete(p_email text default null)
returns boolean
language sql stable security definer
set search_path = public
as $$
  with me as (
    select lower(coalesce(p_email, auth.jwt() ->> 'email')) as email
  )
  select
    (select count(distinct p.module_id)
       from rep_training_progress p, me
      where p.rep_email = me.email
        and p.passed
        and p.module_id in ('master', 'phone', 'pos', 'camera', 'csv')) = 5
    and exists (
      select 1 from rep_conduct_signatures s, me
       where s.rep_email = me.email
    );
$$;

grant execute on function rep_training_complete(text) to authenticated;

-- ─── Lead-creation lock ──────────────────────────────────────
-- Replaces the wide-open "with check (true)" insert policy from
-- 20260507_canada_leads.sql. Admins (admin_users membership via is_admin(),
-- 20260429_003) bypass; everyone else must have completed the course.
drop policy if exists "Sales reps can insert leads" on canada_leads;
drop policy if exists "Trained reps and admins can insert leads" on canada_leads;

create policy "Trained reps and admins can insert leads"
  on canada_leads for insert
  with check (is_admin() or rep_training_complete());

-- ─── OPTIONAL GRANDFATHER (leave commented unless Aidan says so) ──
-- Seeds full completion for every rep that existed before this migration so
-- active sellers aren't locked out mid-launch. New reps still take the course.
--
-- insert into rep_training_progress
--   (rep_id, rep_email, module_id, video_watched, video_watched_at,
--    attempts, best_score, passed, passed_at)
-- select r.id, lower(r.email), m.module_id, true, now(), 0, null, true, now()
-- from sales_reps r
-- cross join (values ('master'), ('phone'), ('pos'), ('camera'), ('csv')) as m(module_id)
-- on conflict (rep_email, module_id) do nothing;
--
-- insert into rep_conduct_signatures (rep_id, rep_email, signed_name, conduct_version)
-- select r.id, lower(r.email), r.name || ' (grandfathered)', '1.0'
-- from sales_reps r
-- on conflict (rep_email, conduct_version) do nothing;
