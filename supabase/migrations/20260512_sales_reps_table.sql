-- Ensure sales_reps table exists with all required columns.
-- This table may have been created ad-hoc via the frontend auth flow;
-- this migration ensures schema consistency for the careers → team pipeline.

CREATE TABLE IF NOT EXISTS sales_reps (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  email           TEXT NOT NULL,
  phone           TEXT DEFAULT '',
  commission_rate INTEGER NOT NULL DEFAULT 70,
  is_active       BOOLEAN NOT NULL DEFAULT false,
  total_earned    NUMERIC(12,2) NOT NULL DEFAULT 0,
  total_paid      NUMERIC(12,2) NOT NULL DEFAULT 0,
  location        TEXT DEFAULT 'Canada',
  portal_context  TEXT DEFAULT 'canada',
  recruiter       TEXT DEFAULT '',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_reps_email ON sales_reps(email);

-- RLS: backend uses service role (bypasses RLS), frontend uses anon key (needs policies)
ALTER TABLE sales_reps ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read (shared team view)
DO $$ BEGIN
  DROP POLICY IF EXISTS "reps_select" ON sales_reps;
  CREATE POLICY "reps_select" ON sales_reps FOR SELECT
    USING (auth.uid() IS NOT NULL);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- Allow inserts from service role (backend career applications)
DO $$ BEGIN
  DROP POLICY IF EXISTS "reps_insert" ON sales_reps;
  CREATE POLICY "reps_insert" ON sales_reps FOR INSERT
    WITH CHECK (true);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- Allow authenticated users to update (admin approval, self-edit)
DO $$ BEGIN
  DROP POLICY IF EXISTS "reps_update" ON sales_reps;
  CREATE POLICY "reps_update" ON sales_reps FOR UPDATE
    USING (auth.uid() IS NOT NULL);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- Allow admin deletes (reject applicant)
DO $$ BEGIN
  DROP POLICY IF EXISTS "reps_delete" ON sales_reps;
  CREATE POLICY "reps_delete" ON sales_reps FOR DELETE
    USING (auth.uid() IS NOT NULL);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
