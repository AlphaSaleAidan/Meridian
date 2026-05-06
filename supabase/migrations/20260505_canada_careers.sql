-- Canada career applications table
-- Stores applications submitted via /canada/careers form

CREATE TABLE IF NOT EXISTS canada_career_applications (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL,
  phone       TEXT NOT NULL DEFAULT '',
  position    TEXT NOT NULL,
  city        TEXT NOT NULL DEFAULT '',
  province    TEXT NOT NULL DEFAULT '',
  experience  TEXT DEFAULT '',
  current_employer TEXT DEFAULT '',
  linkedin_url TEXT DEFAULT '',
  referral_source TEXT DEFAULT '',
  availability TEXT DEFAULT '',
  motivation  TEXT DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'pending',
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  notes       TEXT DEFAULT '',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_canada_careers_status ON canada_career_applications(status);
CREATE INDEX idx_canada_careers_email ON canada_career_applications(email);
CREATE INDEX idx_canada_careers_province ON canada_career_applications(province);

ALTER TABLE canada_career_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on canada_career_applications"
  ON canada_career_applications
  FOR ALL
  USING (true)
  WITH CHECK (true);
