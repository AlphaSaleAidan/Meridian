-- ============================================================================
-- Backfill two missing US applicants into sales_reps (Team > Applications).
-- Companion to 20260729_backfill_canada_applicants.sql — same blind window,
-- US portal side (us.py /team reads portal_context=in.(us,all)).
--
--  * Nate Wilkinson — pending US career application (2026-07-18), no rep row
--    was created because the pipeline-era apply flow stopped doing so.
--  * Haider Raza — real US rep signup (auth.users metadata role='sales_rep',
--    portal='us', registered 2026-06-16) that never produced a rep row.
--
-- Idempotent + additive: insert-only-if-absent by email; never touches an
-- existing sales_reps row. Safe to re-run. Authorized by the owner 2026-07-29
-- ("check the logged users for Careers that aren't appearing … and add them").
-- ============================================================================

INSERT INTO sales_reps (org_id, name, email, phone, commission_rate, is_active, portal_context, created_at)
SELECT '168b6df2-e9af-4b00-8fec-51e51149ff19'::uuid,
       ca.name, lower(ca.email), COALESCE(ca.phone, ''),
       0.70, false, 'us', ca.created_at
FROM career_applications ca
WHERE lower(ca.email) = 'natewilk@gmail.com'
  AND ca.status = 'pending'
  AND NOT EXISTS (SELECT 1 FROM sales_reps sr WHERE lower(sr.email) = lower(ca.email))
LIMIT 1;

INSERT INTO sales_reps (org_id, name, email, phone, commission_rate, is_active, portal_context, created_at)
SELECT '168b6df2-e9af-4b00-8fec-51e51149ff19'::uuid,
       COALESCE(u.raw_user_meta_data->>'full_name', u.email), lower(u.email), '',
       0.70, false, 'us', u.created_at
FROM auth.users u
WHERE lower(u.email) = 'haiderr099@gmail.com'
  AND NOT EXISTS (SELECT 1 FROM sales_reps sr WHERE lower(sr.email) = lower(u.email))
LIMIT 1;
