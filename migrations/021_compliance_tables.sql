-- 021_compliance_tables.sql
-- Meridian Compliance System: PIPEDA/CASL/privacy compliance tables
-- Run in Supabase SQL editor

-- ═══════════════════════════════════════════════════════════════
-- 1. compliance_documents — versioned legal document storage
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS compliance_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type   TEXT NOT NULL,               -- e.g. 'terms_of_service', 'privacy_policy', 'camera_disclosure'
    version         TEXT NOT NULL,               -- semver: '1.0', '1.1', etc.
    content         TEXT NOT NULL,               -- full document content (markdown or HTML)
    content_hash    TEXT NOT NULL,               -- SHA-256 of content for integrity verification
    jurisdiction    TEXT NOT NULL DEFAULT 'CA',   -- 'CA', 'US', 'QC' (Quebec special rules), 'ALL'
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current      BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_type, version)
);

ALTER TABLE compliance_documents ENABLE ROW LEVEL SECURITY;

-- Anyone can read current documents (they're public legal docs)
CREATE POLICY "compliance_documents_read" ON compliance_documents
    FOR SELECT USING (true);

-- Only service role can insert/update
CREATE POLICY "compliance_documents_admin_write" ON compliance_documents
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_compliance_docs_type_current
    ON compliance_documents (document_type, is_current)
    WHERE is_current = true;


-- ═══════════════════════════════════════════════════════════════
-- 2. compliance_acceptances — user acceptance records
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS compliance_acceptances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,
    user_type           TEXT NOT NULL,           -- 'customer', 'sales_rep', 'admin'
    document_type       TEXT NOT NULL,
    document_version    TEXT NOT NULL,
    accepted_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address          INET,
    user_agent          TEXT,
    portal_context      TEXT,                    -- 'canada', 'us', 'admin'
    acceptance_hash     TEXT NOT NULL,           -- SHA-256 proof: hash(user_id + document_type + version + timestamp)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, document_type, document_version)
);

ALTER TABLE compliance_acceptances ENABLE ROW LEVEL SECURITY;

-- Users can see their own acceptances
CREATE POLICY "compliance_acceptances_own_read" ON compliance_acceptances
    FOR SELECT USING (auth.uid() = user_id);

-- Admins (service role) can see all
CREATE POLICY "compliance_acceptances_admin_read" ON compliance_acceptances
    FOR SELECT USING (auth.role() = 'service_role');

-- Service role can insert on behalf of users
CREATE POLICY "compliance_acceptances_insert" ON compliance_acceptances
    FOR INSERT WITH CHECK (auth.role() = 'service_role' OR auth.uid() = user_id);

CREATE INDEX idx_compliance_acceptances_user
    ON compliance_acceptances (user_id);

CREATE INDEX idx_compliance_acceptances_document
    ON compliance_acceptances (document_type, document_version);


-- ═══════════════════════════════════════════════════════════════
-- 3. casl_consent_records — CASL email consent tracking
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS casl_consent_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT NOT NULL UNIQUE,
    user_id             UUID,
    consent_status      TEXT NOT NULL DEFAULT 'never'
                        CHECK (consent_status IN ('express', 'implied', 'withdrawn', 'never')),
    consent_basis       TEXT,                    -- 'signup_checkbox', 'existing_business_relationship', 'manual_opt_in'
    consent_given_at    TIMESTAMPTZ,
    consent_method      TEXT,                    -- 'web_form', 'verbal', 'written', 'api'
    consent_ip          INET,
    consent_form_url    TEXT,
    unsubscribed_at     TIMESTAMPTZ,
    unsubscribe_method  TEXT,                    -- 'email_link', 'manual', 'api', 'privacy_request'
    consent_evidence    JSONB DEFAULT '{}',      -- checkbox text, screenshot ref, form data
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE casl_consent_records ENABLE ROW LEVEL SECURITY;

-- Admin only (service role)
CREATE POLICY "casl_consent_admin_only" ON casl_consent_records
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_casl_consent_email ON casl_consent_records (email);
CREATE INDEX idx_casl_consent_status ON casl_consent_records (consent_status);
CREATE INDEX idx_casl_consent_user ON casl_consent_records (user_id) WHERE user_id IS NOT NULL;


-- ═══════════════════════════════════════════════════════════════
-- 4. privacy_requests — individual rights requests (PIPEDA)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS privacy_requests (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type            TEXT NOT NULL
                            CHECK (request_type IN (
                                'access', 'correction', 'deletion',
                                'portability', 'objection', 'withdraw_consent'
                            )),
    requester_email         TEXT NOT NULL,
    requester_name          TEXT,
    user_id                 UUID,                -- may be NULL if requester has no account
    portal_context          TEXT,
    received_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deadline_at             TIMESTAMPTZ GENERATED ALWAYS AS (received_at + INTERVAL '30 days') STORED,
    status                  TEXT NOT NULL DEFAULT 'received'
                            CHECK (status IN (
                                'received', 'verified', 'in_progress',
                                'completed', 'rejected', 'expired'
                            )),
    assigned_to             TEXT,                -- admin email handling the request
    completed_at            TIMESTAMPTZ,
    request_description     TEXT,
    response_sent_at        TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No RLS — accessed via service key only
ALTER TABLE privacy_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "privacy_requests_service_only" ON privacy_requests
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_privacy_requests_email ON privacy_requests (requester_email);
CREATE INDEX idx_privacy_requests_status ON privacy_requests (status);
CREATE INDEX idx_privacy_requests_deadline ON privacy_requests (deadline_at)
    WHERE status NOT IN ('completed', 'rejected');


-- ═══════════════════════════════════════════════════════════════
-- 5. breach_log — incident tracking
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS breach_log (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discovered_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    incident_description            TEXT NOT NULL,
    data_types_involved             TEXT[] DEFAULT '{}',
    estimated_individuals_affected  INTEGER DEFAULT 0,
    containment_steps               TEXT,
    rrosh_assessment                TEXT,        -- Real Risk of Significant Harm assessment
    rrosh_conclusion                BOOLEAN,     -- true = meets RROSH threshold, must notify
    opc_notified_at                 TIMESTAMPTZ, -- Office of the Privacy Commissioner
    cai_notified_at                 TIMESTAMPTZ, -- Commission d'acces a l'information (Quebec)
    individuals_notified_at         TIMESTAMPTZ,
    severity                        TEXT NOT NULL DEFAULT 'medium'
                                    CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status                          TEXT NOT NULL DEFAULT 'investigating'
                                    CHECK (status IN (
                                        'investigating', 'contained', 'notifying',
                                        'remediation', 'resolved', 'closed'
                                    )),
    root_cause                      TEXT,
    remediation_steps               TEXT,
    resolved_at                     TIMESTAMPTZ,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE breach_log ENABLE ROW LEVEL SECURITY;

-- Admin only
CREATE POLICY "breach_log_admin_only" ON breach_log
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_breach_log_status ON breach_log (status);
CREATE INDEX idx_breach_log_severity ON breach_log (severity);


-- ═══════════════════════════════════════════════════════════════
-- 6. data_inventory — PIPEDA-required data catalog
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS data_inventory (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_category       TEXT NOT NULL,           -- e.g. 'customer_pii', 'camera_analytics', 'payment_data'
    description         TEXT,
    data_types          TEXT[] DEFAULT '{}',      -- e.g. '{email, name, phone}'
    source              TEXT,                    -- 'user_input', 'pos_sync', 'camera_feed', 'third_party'
    purpose             TEXT,                    -- PIPEDA requires stated purpose
    legal_basis         TEXT,                    -- 'consent', 'contract', 'legitimate_interest'
    retention_period    TEXT,                    -- e.g. '2 years', 'until account deletion'
    location            TEXT,                    -- 'supabase_ca', 'vercel_us', 'digitalocean_tor'
    cross_border        BOOLEAN DEFAULT false,   -- data transferred outside Canada?
    sub_processors      TEXT[] DEFAULT '{}',      -- e.g. '{Supabase, Vercel, Square}'
    sensitivity         TEXT NOT NULL DEFAULT 'standard'
                        CHECK (sensitivity IN ('public', 'standard', 'sensitive', 'highly_sensitive')),
    last_reviewed       DATE,
    next_review         DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE data_inventory ENABLE ROW LEVEL SECURITY;

-- Admin only
CREATE POLICY "data_inventory_admin_only" ON data_inventory
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX idx_data_inventory_category ON data_inventory (data_category);
CREATE INDEX idx_data_inventory_sensitivity ON data_inventory (sensitivity);
CREATE INDEX idx_data_inventory_review ON data_inventory (next_review)
    WHERE next_review IS NOT NULL;
