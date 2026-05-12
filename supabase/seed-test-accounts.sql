-- Portal context migration for sales_reps
-- Safe to re-run: uses IF NOT EXISTS + conditional updates

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
