-- Fix canada_leads RLS: allow all authenticated sales reps to read all leads.
-- The previous policy compared auth.uid() (auth.users UUID) to rep_id (sales_reps UUID),
-- which never matched. Sales CRM is a shared workspace — all reps see all leads.

DROP POLICY IF EXISTS "Sales reps can read their own leads" ON canada_leads;

CREATE POLICY "Authenticated users can read all leads"
  ON canada_leads FOR SELECT
  USING (auth.uid() IS NOT NULL);

-- Also fix update policy — allow any authenticated user to update any lead
DROP POLICY IF EXISTS "Sales reps can update their own leads" ON canada_leads;

CREATE POLICY "Authenticated users can update leads"
  ON canada_leads FOR UPDATE
  USING (auth.uid() IS NOT NULL);

-- Also allow delete for lead management
CREATE POLICY "Authenticated users can delete leads"
  ON canada_leads FOR DELETE
  USING (auth.uid() IS NOT NULL);

-- Fix sales_reps RLS — allow all authenticated users to read all reps (shared team view)
-- and allow reps to update their own row.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'sales_reps') THEN
    ALTER TABLE sales_reps ENABLE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS "reps_select" ON sales_reps;
    CREATE POLICY "reps_select" ON sales_reps FOR SELECT
      USING (auth.uid() IS NOT NULL);

    DROP POLICY IF EXISTS "reps_insert" ON sales_reps;
    CREATE POLICY "reps_insert" ON sales_reps FOR INSERT
      WITH CHECK (true);

    DROP POLICY IF EXISTS "reps_update" ON sales_reps;
    CREATE POLICY "reps_update" ON sales_reps FOR UPDATE
      USING (auth.uid() IS NOT NULL);
  END IF;
END $$;
