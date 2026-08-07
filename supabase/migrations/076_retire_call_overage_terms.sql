-- 076: retire the call-time overage on existing merchants' billing contracts.
--
-- 2026-08-07 (Aidan): calls are hard-capped at MERIDIAN_VOICE_MAX_CALL_MIN
-- instead of billing per minute past the included block, so the standard
-- product charges nothing for call duration. Merchants provisioned before this
-- carry call_overage_cents_per_min = 45 in merchant_billing_terms, which
-- src/billing/fee_reconciliation.py would then (correctly) report as drift:
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
-- EXECUTION: deliberately ONE self-contained DO block, not a BEGIN/COMMIT
-- script with a temp table. This project applies DDL through the Supabase
-- management API (POST /v1/projects/{ref}/database/query), which does not
-- guarantee that a multi-statement client transaction is preserved — a temp
-- table declared ON COMMIT DROP could vanish mid-run. A DO block is a single
-- statement that runs atomically under psql, the management API, or any
-- migration runner, and the per-row supersede→insert ordering below is what
-- keeps the partial unique index satisfied at every step.
--
-- Idempotent: re-running matches no rows and writes nothing.

DO $$
DECLARE
  r               merchant_billing_terms%ROWTYPE;
  migrated_count  integer := 0;
  bespoke_count   integer;
  still_legacy    integer;
  dup_active      integer;
BEGIN
  -- Supersede + replace one merchant at a time. Per row the UPDATE runs before
  -- the INSERT, so uq_merchant_billing_terms_active (one active row per
  -- merchant) is never transiently violated.
  FOR r IN
    SELECT *
      FROM merchant_billing_terms
     WHERE superseded_at IS NULL
       AND call_overage_cents_per_min = 45
     ORDER BY merchant_id
  LOOP
    UPDATE merchant_billing_terms
       SET superseded_at = now()
     WHERE id = r.id;

    INSERT INTO merchant_billing_terms (
      merchant_id, source_lead_id, source_market, plan_tier,
      monthly_fee_cents, order_fee_cents, call_overage_cents_per_min,
      included_call_min, effective_at, created_by, override_reason
    ) VALUES (
      r.merchant_id, r.source_lead_id, r.source_market, r.plan_tier,
      r.monthly_fee_cents, r.order_fee_cents,
      0,                    -- call time is no longer billed
      r.included_call_min,  -- retained: still meaningful if a rate is reinstated
      now(),
      'migration_076_retire_call_overage',
      'Call-time overage retired 2026-08-07 — calls are hard-capped instead of '
      'billed per minute. Supersedes the prior 45c/min contract.'
    );

    migrated_count := migrated_count + 1;
  END LOOP;

  RAISE NOTICE '076: superseded % contract(s) at the retired 45c/min rate', migrated_count;

  -- Surface (but do not touch) any active contract on a non-standard rate.
  SELECT count(*) INTO bespoke_count
    FROM merchant_billing_terms
   WHERE superseded_at IS NULL
     AND call_overage_cents_per_min IS NOT NULL
     AND call_overage_cents_per_min NOT IN (0, 45);

  IF bespoke_count > 0 THEN
    RAISE NOTICE '076: LEFT UNTOUCHED — % active contract(s) carry a non-standard '
                 'call_overage_cents_per_min (not 0 and not 45). Review these by hand: '
                 'they will keep appearing as reconciler drift until someone decides '
                 'whether the negotiated rate still stands.', bespoke_count;
  END IF;

  -- Invariants. Raise rather than leave billing half-migrated: the exception
  -- rolls the whole DO block back.
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
