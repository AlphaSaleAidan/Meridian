-- ============================================================
-- PART 10: SALES REP COMMISSIONS & PAYOUT TRACKING
-- ============================================================
-- Tracks sales reps, commission rates, earned commissions,
-- and manual payout records. Auto-calculates splits on
-- every inbound Square/Clover payment via webhook.
-- ============================================================

-- New enums
CREATE TYPE commission_status AS ENUM ('pending', 'earned', 'paid', 'disputed', 'cancelled');
CREATE TYPE payout_status AS ENUM ('pending', 'completed', 'cancelled');

-- ============================================================
-- SALES REPS (linked to portal users)
-- ============================================================
CREATE TABLE sales_reps (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT,
    commission_rate DECIMAL(5, 2) NOT NULL DEFAULT 30.00,  -- 30-60% set by admin
    recruiter       TEXT,                                    -- who recruited this rep
    is_active       BOOLEAN DEFAULT TRUE,
    total_earned    DECIMAL(12, 2) DEFAULT 0.00,
    total_paid      DECIMAL(12, 2) DEFAULT 0.00,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sales_reps_email ON sales_reps(email);
CREATE INDEX idx_sales_reps_active ON sales_reps(is_active);

-- ============================================================
-- REP-CLIENT ASSIGNMENTS (which rep sold which client)
-- ============================================================
CREATE TABLE rep_client_assignments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rep_id          UUID NOT NULL REFERENCES sales_reps(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    commission_rate DECIMAL(5, 2) NOT NULL,  -- rate at time of sale (snapshot)
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    UNIQUE(rep_id, org_id)
);

CREATE INDEX idx_rep_client_rep ON rep_client_assignments(rep_id);
CREATE INDEX idx_rep_client_org ON rep_client_assignments(org_id);

-- ============================================================
-- COMMISSIONS (earned on each inbound payment)
-- ============================================================
CREATE TABLE commissions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rep_id              UUID NOT NULL REFERENCES sales_reps(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    assignment_id       UUID REFERENCES rep_client_assignments(id),
    
    -- Payment source (Square transaction or subscription)
    source_type         TEXT NOT NULL DEFAULT 'square_payment',
    source_reference    TEXT,           -- Square payment ID or invoice reference
    
    -- Amounts
    gross_amount        DECIMAL(12, 2) NOT NULL,  -- total payment received from client
    commission_rate     DECIMAL(5, 2) NOT NULL,    -- rate applied (snapshot)
    commission_amount   DECIMAL(12, 2) NOT NULL,   -- rep's cut
    
    status              commission_status NOT NULL DEFAULT 'earned',
    payout_id           UUID,           -- linked when marked as paid
    
    period_start        TIMESTAMPTZ,
    period_end          TIMESTAMPTZ,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_commissions_rep ON commissions(rep_id);
CREATE INDEX idx_commissions_org ON commissions(org_id);
CREATE INDEX idx_commissions_status ON commissions(status);
CREATE INDEX idx_commissions_payout ON commissions(payout_id);
CREATE INDEX idx_commissions_created ON commissions(created_at);

-- ============================================================
-- PAYOUTS (manual disbursement records)
-- ============================================================
CREATE TABLE payouts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rep_id              UUID NOT NULL REFERENCES sales_reps(id) ON DELETE CASCADE,
    
    amount              DECIMAL(12, 2) NOT NULL,
    method              TEXT DEFAULT 'manual',  -- 'venmo', 'zelle', 'bank_transfer', 'cash', etc.
    status              payout_status NOT NULL DEFAULT 'pending',
    
    -- Breakdown
    commission_count    INTEGER DEFAULT 0,
    
    -- Processing
    completed_at        TIMESTAMPTZ,
    notes               TEXT,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payouts_rep ON payouts(rep_id);
CREATE INDEX idx_payouts_status ON payouts(status);

-- Add foreign key from commissions to payouts
ALTER TABLE commissions ADD CONSTRAINT fk_commissions_payout 
    FOREIGN KEY (payout_id) REFERENCES payouts(id);

-- ============================================================
-- FUNCTION: Calculate commission on inbound payment
-- Called by webhook handler when Square/Clover payment arrives
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
    
    -- Create commission record
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
    ) RETURNING id INTO v_commission_id;
    
    -- Update rep totals
    UPDATE sales_reps
    SET total_earned = total_earned + ROUND(p_gross_amount * v_assignment.commission_rate / 100, 2),
        updated_at = NOW()
    WHERE id = v_assignment.rep_id;
    
    RETURN v_commission_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION: Record a manual payout to a rep
-- Batches all unpaid earned commissions, marks them paid
-- ============================================================
CREATE OR REPLACE FUNCTION record_manual_payout(
    p_rep_id UUID,
    p_method TEXT DEFAULT 'manual',
    p_notes TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_total DECIMAL(12, 2);
    v_count INTEGER;
    v_payout_id UUID;
BEGIN
    -- Sum all unpaid earned commissions
    SELECT COALESCE(SUM(commission_amount), 0), COUNT(*)
    INTO v_total, v_count
    FROM commissions
    WHERE rep_id = p_rep_id
      AND status = 'earned'
      AND payout_id IS NULL;
    
    IF v_total <= 0 THEN
        RETURN NULL;
    END IF;
    
    -- Create payout record
    INSERT INTO payouts (rep_id, amount, method, commission_count, status, completed_at, notes)
    VALUES (p_rep_id, v_total, p_method, v_count, 'completed', NOW(), p_notes)
    RETURNING id INTO v_payout_id;
    
    -- Link commissions to this payout and mark paid
    UPDATE commissions
    SET payout_id = v_payout_id, status = 'paid', updated_at = NOW()
    WHERE rep_id = p_rep_id
      AND status = 'earned'
      AND payout_id IS NULL;
    
    -- Update rep's total_paid
    UPDATE sales_reps
    SET total_paid = total_paid + v_total,
        updated_at = NOW()
    WHERE id = p_rep_id;
    
    RETURN v_payout_id;
END;
$$ LANGUAGE plpgsql;
