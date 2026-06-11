-- ============================================================
-- PART 11: COMMISSION SCHEMA ALIGNMENT + IDEMPOTENCY
-- ============================================================
-- Applied to live 2026-06-11. The live DB never received PART 10
-- (010_sales_rep_commissions.sql): calculate_commission() did not
-- exist, and commissions / payouts / rep_client_assignments existed
-- in older shapes (all 0 rows, old columns referenced by no code).
-- This migration aligns the live schema to what the backend uses
-- and adds the idempotency guarantees:
--
--  * UNIQUE (source_type, source_reference) on commissions —
--    webhook redelivery cannot double-pay a rep.
--  * calculate_commission() is idempotent: duplicate deliveries
--    return the existing commission id without re-counting totals.
--  * Commission rate falls back to sales_reps.commission_rate when
--    the assignment has no snapshot rate.
--
-- NOTE: rows with NULL source_reference (manual entries) never
-- collide — Postgres treats NULLs as distinct in UNIQUE.
-- ============================================================

-- Enums (PART 10 never ran, so these don't exist yet)
DO $$ BEGIN
    CREATE TYPE commission_status AS ENUM ('pending', 'earned', 'paid', 'disputed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE payout_status AS ENUM ('pending', 'completed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- sales_reps: earnings counters the payout service reads
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS total_earned DECIMAL(12, 2) NOT NULL DEFAULT 0.00;
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS total_paid   DECIMAL(12, 2) NOT NULL DEFAULT 0.00;
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS metadata     JSONB DEFAULT '{}';

-- rep_client_assignments: per-assignment rate snapshot (nullable;
-- function falls back to sales_reps.commission_rate)
ALTER TABLE rep_client_assignments ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5, 2);
DO $$ BEGIN
    ALTER TABLE rep_client_assignments ADD CONSTRAINT uq_rep_client UNIQUE (rep_id, org_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- commissions: legacy empty table in a shape no code references —
-- recreate in the shape the backend + RPC use (RESTRICT drop: fails
-- loudly if anything turns out to depend on it)
DROP TABLE commissions;
CREATE TABLE commissions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rep_id              UUID NOT NULL REFERENCES sales_reps(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    assignment_id       UUID REFERENCES rep_client_assignments(id),

    source_type         TEXT NOT NULL DEFAULT 'square_payment',
    source_reference    TEXT,           -- Square payment ID or invoice reference

    gross_amount        DECIMAL(12, 2) NOT NULL,
    commission_rate     DECIMAL(5, 2) NOT NULL,
    commission_amount   DECIMAL(12, 2) NOT NULL,

    status              commission_status NOT NULL DEFAULT 'earned',
    payout_id           UUID REFERENCES payouts(id),

    period_start        TIMESTAMPTZ,
    period_end          TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_commissions_source UNIQUE (source_type, source_reference)
);

CREATE INDEX idx_commissions_rep ON commissions(rep_id);
CREATE INDEX idx_commissions_org ON commissions(org_id);
CREATE INDEX idx_commissions_status ON commissions(status);
CREATE INDEX idx_commissions_payout ON commissions(payout_id);
CREATE INDEX idx_commissions_created ON commissions(created_at);

-- Backend accesses commissions via service role only; deny direct
-- user-JWT access.
ALTER TABLE commissions ENABLE ROW LEVEL SECURITY;

-- payouts: columns the payout service expects (older live shape kept)
ALTER TABLE payouts ADD COLUMN IF NOT EXISTS status payout_status NOT NULL DEFAULT 'pending';
ALTER TABLE payouts ADD COLUMN IF NOT EXISTS method TEXT DEFAULT 'manual';
ALTER TABLE payouts ADD COLUMN IF NOT EXISTS commission_count INTEGER DEFAULT 0;
ALTER TABLE payouts ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE payouts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ============================================================
-- FUNCTION: Calculate commission on a Meridian subscription payment
-- (idempotent). Duplicate deliveries of the same
-- (source_type, source_reference) return the existing commission id
-- and do NOT update rep totals again.
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
    v_rate DECIMAL(5, 2);
    v_commission_id UUID;
BEGIN
    -- Active rep assignment for this org; rate snapshot falls back
    -- to the rep's current rate when the assignment has none.
    SELECT rca.id AS assignment_id, rca.rep_id,
           COALESCE(rca.commission_rate, sr.commission_rate) AS rate
    INTO v_assignment
    FROM rep_client_assignments rca
    JOIN sales_reps sr ON sr.id = rca.rep_id
    WHERE rca.org_id = p_org_id
      AND rca.is_active = TRUE
      AND sr.is_active = TRUE
    LIMIT 1;

    IF v_assignment IS NULL OR v_assignment.rate IS NULL THEN
        RETURN NULL;  -- No rep assigned (or no usable rate), no commission
    END IF;

    v_rate := v_assignment.rate;

    -- Create commission record (no-op on duplicate source)
    INSERT INTO commissions (
        rep_id, org_id, assignment_id,
        source_type, source_reference,
        gross_amount, commission_rate, commission_amount,
        status, period_start, period_end
    ) VALUES (
        v_assignment.rep_id, p_org_id, v_assignment.assignment_id,
        p_source_type, p_source_reference,
        p_gross_amount, v_rate,
        ROUND(p_gross_amount * v_rate / 100, 2),
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
    SET total_earned = total_earned + ROUND(p_gross_amount * v_rate / 100, 2),
        updated_at = NOW()
    WHERE id = v_assignment.rep_id;

    RETURN v_commission_id;
END;
$$ LANGUAGE plpgsql;
