-- 076: retire the call-time overage on existing merchants' billing contracts.
--
-- 2026-08-07 (Aidan): calls are hard-capped at MERIDIAN_VOICE_MAX_CALL_MIN
-- instead of billing per minute past the included block, so the standard
-- product charges nothing for call duration. Merchants provisioned before this
-- still carry call_overage_cents_per_min = 45 in merchant_billing_terms, which
-- src/billing/fee_reconciliation.py now (correctly) reports as drift:
-- contracted 45, applied 0.
--
-- This brings those contracts in line WITHOUT destroying history. Per the
-- supersede-not-update doctrine of 20260716_merchant_billing_terms.sql, each
-- active row is CLOSED (superseded_at set) and a replacement inserted with the
-- overage zeroed. The old row remains as the audit trail of what was
-- contracted. A blanket UPDATE would be shorter and is deliberately NOT used —
-- it would rewrite the contract history in place.
--
-- SCOPE: only rows at the retired STANDARD rate (45) are migrated. A merchant
-- on a deliberately negotiated non-standard rate is left untouched and raised
-- as a NOTICE, because zeroing a bespoke deal is not this migration's call.
--
-- Idempotent: re-running finds no active rows at the retired rate.

BEGIN;

-- The retired standard rate. Kept as a CTE-free temp table so the set of rows
-- is fixed BEFORE the supersede below changes what counts as "active".
CREATE TEMP TABLE _legacy_overage_terms ON COMMIT DROP AS
SELECT *
  FROM merchant_billing_terms
 WHERE superseded_at IS NULL
   AND call_overage_cents_per_min = 45;

-- Surface (but do not touch) any active contract on a non-standard rate.
DO $$
DECLARE
  bespoke_count integer;
  migrating_count integer;
BEGIN
  SELECT count(*) INTO bespoke_count
    FROM merchant_billing_terms
   WHERE superseded_at IS NULL
     AND call_overage_cents_per_min IS NOT NULL
     AND call_overage_cents_per_min NOT IN (0, 45);

  SELECT count(*) INTO migrating_count FROM _legacy_overage_terms;

  RAISE NOTICE '076: superseding % contract(s) at the retired 45c/min rate', migrating_count;

  IF bespoke_count > 0 THEN
    RAISE NOTICE '076: LEFT UNTOUCHED — % active contract(s) carry a non-standard '
                 'call_overage_cents_per_min (not 0 and not 45). Review these by hand: '
                 'they will continue to appear as reconciler drift until someone decides '
                 'whether the negotiated rate still stands.', bespoke_count;
  END IF;
END $$;

-- 1. Close the active rows. Must run BEFORE the insert: the partial unique
--    index (uq_merchant_billing_terms_active) permits exactly one active row
--    per merchant, so inserting first would violate it.
UPDATE merchant_billing_terms t
   SET superseded_at = now()
  FROM _legacy_overage_terms l
 WHERE t.id = l.id;

-- 2. Insert the replacement contracts — identical in every field except the
--    zeroed overage, a fresh effective_at, and the provenance of this change.
INSERT INTO merchant_billing_terms (
  merchant_id,
  source_lead_id,
  source_market,
  plan_tier,
  monthly_fee_cents,
  order_fee_cents,
  call_overage_cents_per_min,
  included_call_min,
  effective_at,
  created_by,
  override_reason
)
SELECT
  l.merchant_id,
  l.source_lead_id,
  l.source_market,
  l.plan_tier,
  l.monthly_fee_cents,
  l.order_fee_cents,
  0,                      -- call time is no longer billed
  l.included_call_min,    -- retained: still meaningful if a rate is reinstated
  now(),
  'migration_076_retire_call_overage',
  'Call-time overage retired 2026-08-07 — calls are hard-capped instead of '
  'billed per minute. Supersedes the prior 45c/min contract.'
  FROM _legacy_overage_terms l;

-- 3. Invariants. Fail the transaction rather than leave billing half-migrated.
DO $$
DECLARE
  still_legacy integer;
  dup_active integer;
BEGIN
  SELECT count(*) INTO still_legacy
    FROM merchant_billing_terms
   WHERE superseded_at IS NULL
     AND call_overage_cents_per_min = 45;
  IF still_legacy > 0 THEN
    RAISE EXCEPTION '076: % active contract(s) still at 45c/min after migration', still_legacy;
  END IF;

  -- The partial unique index already guarantees this; assert it anyway, since
  -- a second active row per merchant would mean two live billing contracts.
  SELECT count(*) INTO dup_active FROM (
    SELECT merchant_id
      FROM merchant_billing_terms
     WHERE superseded_at IS NULL
     GROUP BY merchant_id
    HAVING count(*) > 1
  ) d;
  IF dup_active > 0 THEN
    RAISE EXCEPTION '076: % merchant(s) left with more than one active contract', dup_active;
  END IF;
END $$;

COMMIT;
