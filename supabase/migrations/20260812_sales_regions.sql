-- Sales regions — isolated rep territories inside a portal.
--
-- A region is a named, walled-off group of reps (first tenant: 'odyssey',
-- Enoch Cheung's territory). region=NULL means the default/core team and is
-- the value every existing row keeps, so this migration changes no behavior
-- until a row is explicitly assigned a region.
--
-- Isolation is enforced in the backend plane (src/api/hierarchy.py
-- partition_by_region + the /team and /leaderboard routes): a region member
-- only ever sees roster rows from their own region, core reps never see
-- region rows, and region members are excluded from the portal leaderboard
-- (regions can opt out of leaderboards entirely — Odyssey does, for now).
-- Global allowlist admins keep full visibility for oversight.
--
-- Lead isolation needs no new plumbing: region reps are rooted under their
-- region lead in the 20260716 hierarchy tree, so the existing subtree
-- scoping (RLS + hierarchy.scope_lead_rows) already fences their deals.

ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS region TEXT;

COMMENT ON COLUMN sales_reps.region IS
  'Isolated territory slug (e.g. odyssey). NULL = default/core team. Region members see only their region''s roster and are excluded from the portal leaderboard.';

CREATE INDEX IF NOT EXISTS idx_sales_reps_region
  ON sales_reps (region) WHERE region IS NOT NULL;

-- Careers: applicants can request a region from the public careers form
-- (Region dropdown, Odyssey only for now). Empty/NULL = core team.
ALTER TABLE career_applications ADD COLUMN IF NOT EXISTS region TEXT;
