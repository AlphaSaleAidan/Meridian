-- 044: career_applications — durable homes for two answers that were being
-- silently dropped.
--
-- The Canada careers form (CanadaCareersPage.tsx) collects a "Commission sales
-- experience? (yes/no)" answer and a free-text "Referral Name". Neither had a
-- backend field or a column, so Pydantic discarded them and the answers were
-- lost end-to-end. The backend model (careers.py CareerApplication) now accepts
-- them (commission_experience / referral_name) and writes them here.
--
-- The SupabaseREST client drops unknown columns, so the write stayed
-- backward-compatible until this migration lands; after it applies the two
-- answers persist. Written only by the backend service role.

ALTER TABLE career_applications
  ADD COLUMN IF NOT EXISTS commission_experience TEXT DEFAULT '';

ALTER TABLE career_applications
  ADD COLUMN IF NOT EXISTS referral_name TEXT DEFAULT '';

COMMENT ON COLUMN career_applications.commission_experience IS
  'Applicant''s answer to "Commission sales experience?" (yes/no) — Canada careers form.';
COMMENT ON COLUMN career_applications.referral_name IS
  'Free-text name of the person who referred the applicant (distinct from referral_source, which is the channel: LinkedIn / Job Board / etc.).';
