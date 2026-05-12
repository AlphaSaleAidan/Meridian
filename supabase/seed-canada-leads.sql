-- Canada leads table schema + RLS policies
-- Safe to re-run: uses IF NOT EXISTS guards

CREATE TABLE IF NOT EXISTS canada_leads (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  business_name TEXT NOT NULL,
  contact_name TEXT NOT NULL,
  contact_email TEXT NOT NULL DEFAULT '',
  contact_phone TEXT NOT NULL DEFAULT '',
  vertical TEXT NOT NULL DEFAULT '',
  stage TEXT NOT NULL DEFAULT 'prospecting',
  monthly_value INTEGER NOT NULL DEFAULT 0,
  commission_rate INTEGER NOT NULL DEFAULT 70,
  expected_close_date TEXT,
  notes TEXT DEFAULT '',
  source TEXT DEFAULT '',
  city TEXT DEFAULT '',
  province TEXT DEFAULT '',
  is_demo BOOLEAN DEFAULT false,
  created_at TEXT DEFAULT now()::text,
  updated_at TEXT DEFAULT now()::text
);

-- Enable RLS
ALTER TABLE canada_leads ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read/write canada_leads
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'canada_leads' AND policyname = 'canada_leads_read'
  ) THEN
    CREATE POLICY "canada_leads_read" ON canada_leads FOR SELECT USING (auth.role() = 'authenticated');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'canada_leads' AND policyname = 'canada_leads_write'
  ) THEN
    CREATE POLICY "canada_leads_write" ON canada_leads FOR ALL USING (auth.role() = 'authenticated');
  END IF;
END $$;
