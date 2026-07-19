-- 060: identity_org_memberships — the same-email Multi-Location Hub link table.
--
-- WORKSTREAM 5 (Multi-Location Hub, Command tier). Spec:
--   docs/multi-location-hub-journey.md
--
-- Problem it solves: today an owner == one org. `businesses.owner_user_id`
-- points one identity at one org, and `business_users` scatters staff
-- membership across orgs with no single authoritative "which orgs does this
-- identity operate?" list. The hub needs ONE identity to belong to MANY orgs
-- and to switch between them without re-login.
--
-- `business_users` already technically supports many rows per user, but it is
-- staff-scoped (per-location roles, invited staff) and does NOT record the
-- owner relationship (that lives on businesses.owner_user_id) nor a hub-level
-- "connected into my command view" fact. This table is the hub's authoritative
-- identity->org edge: one row per (identity, org) the hub aggregates/switches
-- across, carrying the hub role and whether the identity is the org owner.
--
-- Additive + idempotent. Numbering: 060+ (050-059 reserved for sibling branch
-- feat/team-management).

-- ─── Table ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS identity_org_memberships (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- the authenticated identity (auth.users). ALWAYS derived from the session
  -- JWT server-side, NEVER from a request body (org_id-body-bypass history:
  -- PR #354).
  user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  -- the org / location. businesses.id is text (uuid-shaped, 'biz_...') — match
  -- the type to avoid casts.
  org_id        text NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  -- the identity's hub role in THIS org. Governs who may push config down.
  role          text NOT NULL DEFAULT 'viewer'
                  CHECK (role IN ('owner', 'admin', 'manager', 'viewer')),
  -- convenience flag: true when businesses.owner_user_id == user_id at connect
  -- time. Owners/admins may push config down; viewers may only read.
  is_owner      boolean NOT NULL DEFAULT false,
  connected_at  timestamptz NOT NULL DEFAULT now(),
  -- soft-unlink: a removed link stays for audit but is_active=false hides it
  -- from the hub.
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE identity_org_memberships IS
  'Same-email Multi-Location Hub: one identity -> many orgs. Authoritative identity->org edge the hub aggregates and switches across. Written server-side only after membership is proven (owner_user_id or active business_users). See docs/multi-location-hub-journey.md.';
COMMENT ON COLUMN identity_org_memberships.user_id IS
  'auth.users identity. ALWAYS from the session JWT, never the request body.';
COMMENT ON COLUMN identity_org_memberships.role IS
  'Hub role in this org (owner|admin|manager|viewer). owner/admin may push config down; viewer is read-only in the hub.';
COMMENT ON COLUMN identity_org_memberships.is_owner IS
  'True if businesses.owner_user_id == user_id when the link was made.';

-- One membership per identity per org.
CREATE UNIQUE INDEX IF NOT EXISTS uq_identity_org_memberships
  ON identity_org_memberships (user_id, org_id);

CREATE INDEX IF NOT EXISTS idx_identity_org_memberships_user
  ON identity_org_memberships (user_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_identity_org_memberships_org
  ON identity_org_memberships (org_id) WHERE is_active;

-- ─── Row Level Security (from day one) ──────────────────────
-- An identity may READ only its own membership rows. It may NEVER read another
-- identity's memberships, and it may NEVER write memberships from the browser —
-- links are created by the backend service role only AFTER it independently
-- verifies (owner_user_id OR active business_users) that the identity controls
-- the org. This closes the org_id-body-bypass class of bug: even a forged
-- INSERT with someone else's org would be denied to the anon/authenticated
-- role, and the service-role write path proves membership first.
ALTER TABLE identity_org_memberships ENABLE ROW LEVEL SECURITY;

-- SELECT: only your own rows.
DROP POLICY IF EXISTS identity_org_memberships_select_own ON identity_org_memberships;
CREATE POLICY identity_org_memberships_select_own
  ON identity_org_memberships
  FOR SELECT
  USING (user_id = auth.uid());

-- No INSERT/UPDATE/DELETE policy for anon/authenticated on purpose: the
-- service role (which bypasses RLS) is the ONLY writer, and it verifies
-- membership before inserting. An ordinary logged-in user cannot self-grant a
-- membership to an org they don't control.
