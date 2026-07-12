-- 037: career_applications — durable record for careers-page applications.
--
-- POST /api/careers/apply (US) and /api/canada/careers/apply (CA) have always
-- attempted this insert best-effort, but the table was never created, so the
-- only record of an application was the notify email (and for CA, the pending
-- sales_reps row). This makes the write land.
--
-- Written only by the backend service role; no anon/authenticated access.

CREATE TABLE IF NOT EXISTS career_applications (
  id uuid PRIMARY KEY,
  country text NOT NULL DEFAULT 'US',
  name text NOT NULL,
  email text NOT NULL,
  phone text DEFAULT '',
  position text NOT NULL,
  city text DEFAULT '',
  state_province text DEFAULT '',
  experience text DEFAULT '',
  current_employer text DEFAULT '',
  linkedin_url text DEFAULT '',
  referral_source text DEFAULT '',
  availability text DEFAULT '',
  motivation text DEFAULT '',
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_career_applications_created
  ON career_applications (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_career_applications_email
  ON career_applications (email);

-- Service-role only: enable RLS and define no policies, so anon/authenticated
-- REST access is denied while the backend (service key) bypasses RLS.
ALTER TABLE career_applications ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE career_applications IS
  'Careers-page applications (US + CA). Written by the backend service role via /api/careers/apply; surfaced to humans via the notify email (and sales_reps pending rows for CA).';
