-- ============================================================================
-- Backfill pending Canada applicants into sales_reps (Team > Applications).
--
-- Between 2026-07-16 (careers pipeline) and 2026-07-29, applications stopped
-- creating the pending (inactive) sales_reps row at apply time, so applicants
-- from that window are invisible in the portal's Team > Applications tab —
-- they exist only in career_applications. This restores their visibility so
-- admins can approve them without anyone re-applying (approval creates the
-- auth user and emails credentials).
--
-- Idempotent + additive: insert-only-if-absent by (lowercased) email; never
-- touches an existing sales_reps row, active or pending. Safe to re-run.
-- Pairs with the careers.py change that re-creates this row at apply time.
--
-- Also removes the 2026-07-29 automated E2E test rows (clearly labeled
-- synthetic e2e-careers-test-* applications created while verifying this
-- flow, plus any pending sales_reps row the post-deploy verification made).
-- ============================================================================

INSERT INTO sales_reps (name, email, phone, commission_rate, is_active, portal_context, created_at)
SELECT DISTINCT ON (lower(ca.email))
       ca.name,
       lower(ca.email),
       COALESCE(ca.phone, ''),
       0.70,
       false,
       'canada',
       ca.created_at
FROM career_applications ca
WHERE ca.country = 'CA'
  AND ca.status = 'pending'
  AND ca.email IS NOT NULL AND ca.email <> ''
  AND lower(ca.email) NOT LIKE 'e2e-careers-test-%@meridian.tips'
  AND NOT EXISTS (
    SELECT 1 FROM sales_reps sr WHERE lower(sr.email) = lower(ca.email)
  )
ORDER BY lower(ca.email), ca.created_at ASC;

DELETE FROM career_applications
WHERE lower(email) LIKE 'e2e-careers-test-%@meridian.tips';

DELETE FROM sales_reps
WHERE lower(email) LIKE 'e2e-careers-test-%@meridian.tips'
  AND is_active = false;
