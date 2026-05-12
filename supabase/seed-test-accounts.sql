-- Test accounts for Canadian and US portal verification
-- Run after seed-canada-leads.sql
-- Safe to re-run: uses ON CONFLICT DO NOTHING

-- Ensure sales_reps has portal_context column
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'sales_reps' AND column_name = 'portal_context'
  ) THEN
    ALTER TABLE sales_reps ADD COLUMN portal_context TEXT DEFAULT 'all';
  END IF;
END $$;

-- Set portal_context for known admin accounts
UPDATE sales_reps SET portal_context = 'all'
WHERE email ILIKE '%aidan%' AND (portal_context IS NULL OR portal_context = '');

UPDATE sales_reps SET portal_context = 'canada'
WHERE email ILIKE '%enoch%' AND (portal_context IS NULL OR portal_context = '');

-- Note: Test account auth users must be created via Supabase Auth dashboard
-- or supabase.auth.admin.createUser() — cannot INSERT into auth.users directly.
--
-- After creating auth users, insert their sales_reps profiles:
--
-- INSERT INTO sales_reps (name, email, commission_rate, is_active, portal_context, total_earned, total_paid)
-- VALUES
--   ('Test Customer ON', 'test.customer.on@meridian.tips', 70, true, 'canada', 0, 0),
--   ('Test Customer QC', 'test.customer.qc@meridian.tips', 70, true, 'canada', 0, 0),
--   ('Test Demo CA', 'test.demo.ca@meridian.tips', 70, true, 'canada', 0, 0),
--   ('Test Customer US', 'test.customer.us@meridian.tips', 70, true, 'us', 0, 0)
-- ON CONFLICT (email) DO NOTHING;
