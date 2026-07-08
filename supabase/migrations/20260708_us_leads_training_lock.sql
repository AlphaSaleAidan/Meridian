-- Meridian — US lead-creation training lock (parity with canada_leads).
--
-- Mirrors 20260707_rep_training_course.sql, which added the training gate to
-- canada_leads only. The training progress tables, rep_training_complete(), and
-- is_admin() are region-agnostic (reps are shared across US/Canada), so no new
-- functions are needed here — this migration only extends the same RESTRICTIVE
-- insert gate to us_leads.
--
-- us_leads currently has a permissive insert policy ("Authenticated users can
-- insert US leads" WITH CHECK (true), from 20260522_us_leads_rls.sql). Permissive
-- policies OR together, so the training gate must be RESTRICTIVE — it ANDs on top:
--   insert allowed iff (existing permissive) AND (is_admin() OR rep_training_complete()).
-- Admins bypass via is_admin().
--
-- APPLY NOTE: locks lead creation for every rep who has not completed the course.
-- If US reps are actively selling when this lands, either have them complete the
-- course first or run the grandfather block in 20260707_rep_training_course.sql
-- (it seeds completion for ALL existing sales_reps, US and Canada alike).

drop policy if exists "Training required to insert US leads" on us_leads;

create policy "Training required to insert US leads"
  on us_leads as restrictive for insert
  with check (is_admin() or rep_training_complete());
