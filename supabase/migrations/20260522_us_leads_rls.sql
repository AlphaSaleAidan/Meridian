-- RLS policies for us_leads table (executed 2026-05-22)
-- Mirrors the canada portal's leads table RLS pattern

-- Enable RLS (already enabled, but idempotent)
ALTER TABLE us_leads ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read all US leads
CREATE POLICY IF NOT EXISTS "Authenticated users can read US leads"
  ON us_leads FOR SELECT
  TO authenticated
  USING (true);

-- Authenticated users can insert US leads
CREATE POLICY IF NOT EXISTS "Authenticated users can insert US leads"
  ON us_leads FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Authenticated users can update US leads
CREATE POLICY IF NOT EXISTS "Authenticated users can update US leads"
  ON us_leads FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Authenticated users can delete US leads
CREATE POLICY IF NOT EXISTS "Authenticated users can delete US leads"
  ON us_leads FOR DELETE
  TO authenticated
  USING (true);
