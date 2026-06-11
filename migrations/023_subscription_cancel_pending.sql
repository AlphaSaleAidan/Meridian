-- Add 'cancel_pending' subscription status value
-- Used by billing_service.cancel_subscription when the Square-side
-- subscription cancel fails: the local row is marked cancel_pending
-- (instead of canceled) so the Square subscription keeps billing
-- visibly until an operator resolves it.
-- (Same pattern as supabase/migrations/20260519_fix_subscription_enums.sql)

ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'cancel_pending';
