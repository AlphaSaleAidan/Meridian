-- Recruiters table for dynamic recruiter cards on careers pages
-- Region-scoped so US and Canada can have separate recruiters

CREATE TABLE IF NOT EXISTS recruiters (
  id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name            TEXT NOT NULL,
  title           TEXT NOT NULL,
  company         TEXT NOT NULL DEFAULT '',
  bio             TEXT DEFAULT '',
  linkedin_url    TEXT DEFAULT '',
  email           TEXT DEFAULT '',
  photo_url       TEXT DEFAULT NULL,
  region          TEXT NOT NULL DEFAULT 'us',
  active          BOOLEAN NOT NULL DEFAULT true,
  display_order   INTEGER NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recruiters_region ON recruiters(region);
CREATE INDEX IF NOT EXISTS idx_recruiters_active ON recruiters(active);

ALTER TABLE recruiters ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access on recruiters"
  ON recruiters
  FOR SELECT
  USING (active = true);

CREATE POLICY "Service role full access on recruiters"
  ON recruiters
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Seed Enoch Cheung as the first Canada recruiter
INSERT INTO recruiters (id, name, title, company, bio, linkedin_url, email, region, active, display_order)
VALUES (
  'recruiter-enoch-cheung',
  'Enoch Cheung',
  'Canadian Regional Director, Meridian',
  'Nexus Consulting',
  'Leading Meridian''s expansion across Canadian markets.',
  '', -- TODO: replace with real LinkedIn URL
  '', -- TODO: replace with real email
  'canada',
  true,
  1
)
ON CONFLICT (id) DO NOTHING;
