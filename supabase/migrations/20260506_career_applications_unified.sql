-- Unified career applications table (US + Canada)
-- Replaces canada_career_applications with a country-aware table

CREATE TABLE IF NOT EXISTS career_applications (
  id              TEXT PRIMARY KEY,
  country         TEXT NOT NULL DEFAULT 'US',
  name            TEXT NOT NULL,
  email           TEXT NOT NULL,
  phone           TEXT NOT NULL DEFAULT '',
  position        TEXT NOT NULL,
  city            TEXT NOT NULL DEFAULT '',
  state_province  TEXT NOT NULL DEFAULT '',
  experience      TEXT DEFAULT '',
  current_employer TEXT DEFAULT '',
  linkedin_url    TEXT DEFAULT '',
  referral_source TEXT DEFAULT '',
  availability    TEXT DEFAULT '',
  motivation      TEXT DEFAULT '',
  status          TEXT NOT NULL DEFAULT 'pending',
  reviewed_by     TEXT,
  reviewed_at     TIMESTAMPTZ,
  notes           TEXT DEFAULT '',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_career_apps_status ON career_applications(status);
CREATE INDEX IF NOT EXISTS idx_career_apps_email ON career_applications(email);
CREATE INDEX IF NOT EXISTS idx_career_apps_country ON career_applications(country);
CREATE INDEX IF NOT EXISTS idx_career_apps_region ON career_applications(state_province);

ALTER TABLE career_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on career_applications"
  ON career_applications
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Migrate existing data from canada_career_applications if it exists
INSERT INTO career_applications (
  id, country, name, email, phone, position, city, state_province,
  experience, current_employer, linkedin_url, referral_source,
  availability, motivation, status, reviewed_by, reviewed_at, notes, created_at
)
SELECT
  id, 'CA', name, email, phone, position, city, province,
  experience, current_employer, linkedin_url, referral_source,
  availability, motivation, status, reviewed_by, reviewed_at, notes, created_at
FROM canada_career_applications
ON CONFLICT (id) DO NOTHING;
