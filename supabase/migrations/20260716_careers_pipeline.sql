-- ============================================================================
-- Careers recruiting pipeline on career_applications.
--
-- Applications now live in a staged pipeline (applied → screened → interview →
-- offer → hired | rejected) instead of upserting an inactive sales_reps row at
-- application time. The sales_reps row is created/activated ONLY at
-- stage='hired', with manager_id = recruiter_id — the org tree grows from
-- recruiting (src/api/routes/careers_pipeline.py).
--
-- Idempotent. NOT applied automatically.
--
-- Backward compat: rows created by the old flow keep their legacy `status`
-- column; `stage` is backfilled from it below so existing pending applicants
-- appear at the top of the pipeline instead of being orphaned.
-- ============================================================================

ALTER TABLE career_applications ADD COLUMN IF NOT EXISTS stage TEXT NOT NULL DEFAULT 'applied';
ALTER TABLE career_applications ADD COLUMN IF NOT EXISTS recruiter_id UUID;
ALTER TABLE career_applications ADD COLUMN IF NOT EXISTS stage_history JSONB NOT NULL DEFAULT '[]';

DO $$ BEGIN
  ALTER TABLE career_applications ADD CONSTRAINT career_applications_stage_check CHECK (stage IN (
    'applied', 'screened', 'interview', 'offer', 'hired', 'rejected'
  ));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE career_applications ADD CONSTRAINT career_applications_recruiter_fk
    FOREIGN KEY (recruiter_id) REFERENCES sales_reps(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_career_apps_stage ON career_applications(stage);
CREATE INDEX IF NOT EXISTS idx_career_apps_recruiter ON career_applications(recruiter_id);

-- Backfill stage from the legacy status column (one-time; idempotent because it
-- only touches rows still sitting at the default stage).
UPDATE career_applications
   SET stage = CASE lower(coalesce(status, 'pending'))
                 WHEN 'approved' THEN 'hired'
                 WHEN 'rejected' THEN 'rejected'
                 ELSE 'applied'
               END
 WHERE stage = 'applied'
   AND lower(coalesce(status, 'pending')) IN ('approved', 'rejected');
