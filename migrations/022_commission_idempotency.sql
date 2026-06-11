-- ============================================================
-- PART 11: COMMISSION IDEMPOTENCY
-- ============================================================
-- Webhook deliveries and RPC retries can fire more than once
-- for the same payment. Without a uniqueness guarantee on the
-- payment source, each retry creates a duplicate commission row
-- and double-counts rep earnings.
--
-- Adds UNIQUE (source_type, source_reference) to commissions
-- and makes calculate_commission() idempotent: a duplicate call
-- returns the existing commission id without re-counting totals.
--
-- NOTE: rows with NULL source_reference (manual entries) never
-- collide — Postgres treats NULLs as distinct in UNIQUE.
-- If duplicates already exist, dedupe before applying:
--   SELECT source_type, source_reference, COUNT(*)
--   FROM commissions WHERE source_reference IS NOT NULL
--   GROUP BY 1, 2 HAVING COUNT(*) > 1;
-- ============================================================

ALTER TABLE commissions
    ADD CONSTRAINT uq_commissions_source UNIQUE (source_type, source_reference);

-- ============================================================
-- FUNCTION: Calculate commission on inbound payment (idempotent)
-- Replaces the version from PART 10. Duplicate deliveries of the
-- same (source_type, source_reference) return the existing
-- commission id and do NOT update rep totals again.
-- ============================================================
CREATE OR REPLACE FUNCTION calculate_commission(
    p_org_id UUID,
    p_gross_amount DECIMAL,
    p_source_type TEXT DEFAULT 'square_payment',
    p_source_reference TEXT DEFAULT NULL,
    p_period_start TIMESTAMPTZ DEFAULT NULL,
    p_period_end TIMESTAMPTZ DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_assignment RECORD;
    v_commission_id UUID;
BEGIN
    -- Find the active rep assignment for this org
    SELECT rca.*, sr.id as sr_id
    INTO v_assignment
    FROM rep_client_assignments rca
    JOIN sales_reps sr ON sr.id = rca.rep_id
    WHERE rca.org_id = p_org_id
      AND rca.is_active = TRUE
      AND sr.is_active = TRUE
    LIMIT 1;

    IF v_assignment IS NULL THEN
        RETURN NULL;  -- No rep assigned, no commission
    END IF;

    -- Create commission record (no-op on duplicate source)
    INSERT INTO commissions (
        rep_id, org_id, assignment_id,
        source_type, source_reference,
        gross_amount, commission_rate, commission_amount,
        status, period_start, period_end
    ) VALUES (
        v_assignment.rep_id, p_org_id, v_assignment.id,
        p_source_type, p_source_reference,
        p_gross_amount, v_assignment.commission_rate,
        ROUND(p_gross_amount * v_assignment.commission_rate / 100, 2),
        'earned',
        p_period_start, p_period_end
    )
    ON CONFLICT ON CONSTRAINT uq_commissions_source DO NOTHING
    RETURNING id INTO v_commission_id;

    IF v_commission_id IS NULL THEN
        -- Duplicate delivery: return the existing commission,
        -- skip the totals update (already counted).
        SELECT id INTO v_commission_id
        FROM commissions
        WHERE source_type = p_source_type
          AND source_reference = p_source_reference;
        RETURN v_commission_id;
    END IF;

    -- Update rep totals
    UPDATE sales_reps
    SET total_earned = total_earned + ROUND(p_gross_amount * v_assignment.commission_rate / 100, 2),
        updated_at = NOW()
    WHERE id = v_assignment.rep_id;

    RETURN v_commission_id;
END;
$$ LANGUAGE plpgsql;
