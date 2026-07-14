-- 038: notifications.org_id uuid → text, FK repointed organizations → businesses.
--
-- The notifications feature has been inert since inception: the table's org_id
-- is uuid with FK notifications_org_id_fkey → organizations(id), but every
-- writer and reader in the app uses businesses.id, which is TEXT ('biz_<hex>'):
--   - onboarding.py  (welcome / credentials-email notifications)
--   - oauth.py / clover_oauth.py  ("Square/Clover Connected!" on POS connect)
--   - webhooks.py    (alert notifications)
--   - dashboard.py   GET /api/dashboard/notifications (the merchant bell)
-- Result: every insert and filtered select 400s ('invalid input syntax for
-- type uuid'), the table has 0 rows, and the merchant notification bell has
-- always been empty. Verified live 2026-07-13 in Railway logs.
--
-- The table is empty, so the type change rewrites nothing.

ALTER TABLE notifications
  DROP CONSTRAINT IF EXISTS notifications_org_id_fkey;

ALTER TABLE notifications
  ALTER COLUMN org_id TYPE text USING org_id::text;

-- Notifications belong to a business (the app's org), not an organizations row.
ALTER TABLE notifications
  ADD CONSTRAINT notifications_org_id_fkey
  FOREIGN KEY (org_id) REFERENCES businesses(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_notifications_org_created
  ON notifications (org_id, created_at DESC);

COMMENT ON COLUMN notifications.org_id IS
  'businesses.id (text, biz_<hex>) — the app''s org id. Was uuid → organizations(id), which no code path ever wrote; repointed by migration 038.';
