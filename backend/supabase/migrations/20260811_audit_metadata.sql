-- Audit metadata for the Kotlin backend's tables: created_at / created_by /
-- modified_at / modified_by on every table its repositories write.
--
-- created_by defaults to the system actor sentinel (uuid-shaped, ends in 37)
-- so pre-existing rows and unattributed inserts (seeds, migrations, upserts
-- with no acting user) are backfilled/attributed to "system" rather than null.
-- modified_at / modified_by stay NULL until the first post-migration update —
-- the repositories stamp them on every UPDATE.

-- businesses: has created_at
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS modified_by TEXT;

-- business_users: has created_at
ALTER TABLE business_users ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037';
ALTER TABLE business_users ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE business_users ADD COLUMN IF NOT EXISTS modified_by TEXT;

-- admin_users: has created_at
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037';
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS modified_by TEXT;

-- sales_reps: has created_at
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037';
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS modified_by TEXT;

-- access_tokens: has created_at + created_by (nullable, no default — left as-is)
ALTER TABLE access_tokens ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE access_tokens ADD COLUMN IF NOT EXISTS modified_by TEXT;

-- onboarding_progress: has completed_at/completed_by but no created_* pair
ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037';
ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS modified_by TEXT;
