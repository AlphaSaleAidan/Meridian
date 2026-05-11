-- Cross-Reference Intelligence System — 4 new tables
-- Stores customer journeys (camera + POS fused), cross-reference insights,
-- zone-purchase correlations, and anonymous customer profiles.

-- 1. Customer Journeys — per-visit physical path + purchase correlation
CREATE TABLE IF NOT EXISTS customer_journeys (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    person_id       TEXT NOT NULL,
    entry_time      TIMESTAMPTZ NOT NULL,
    exit_time       TIMESTAMPTZ,
    zone_stops      JSONB DEFAULT '[]',
    cameras_seen    TEXT[] DEFAULT '{}',
    total_dwell_seconds FLOAT DEFAULT 0,
    transaction_id  TEXT,
    transaction_total_cents INTEGER,
    converted       BOOLEAN DEFAULT FALSE,
    zones_visited   TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cj_org_entry
    ON customer_journeys (org_id, entry_time DESC);

CREATE INDEX IF NOT EXISTS idx_cj_converted
    ON customer_journeys (org_id, converted)
    WHERE converted = TRUE;

CREATE INDEX IF NOT EXISTS idx_cj_person
    ON customer_journeys (person_id, entry_time DESC);

-- 2. Cross-Reference Insights — agent-generated findings
CREATE TABLE IF NOT EXISTS cross_reference_insights (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    agent_name      TEXT NOT NULL,
    insight_type    TEXT NOT NULL,
    detail          TEXT NOT NULL,
    data            JSONB DEFAULT '{}',
    severity        TEXT DEFAULT 'info',
    generated_at    TIMESTAMPTZ DEFAULT now(),
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cri_org_agent
    ON cross_reference_insights (org_id, agent_name, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cri_type
    ON cross_reference_insights (org_id, insight_type);

-- 3. Zone-Purchase Correlations — aggregated zone → revenue data
CREATE TABLE IF NOT EXISTS zone_purchase_correlation (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    zone_name       TEXT NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    total_visits    INTEGER DEFAULT 0,
    converted_visits INTEGER DEFAULT 0,
    conversion_rate FLOAT DEFAULT 0,
    avg_dwell_seconds FLOAT DEFAULT 0,
    total_revenue_cents INTEGER DEFAULT 0,
    avg_basket_cents INTEGER DEFAULT 0,
    lift_vs_baseline FLOAT DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (org_id, zone_name, period_start)
);

CREATE INDEX IF NOT EXISTS idx_zpc_org_zone
    ON zone_purchase_correlation (org_id, zone_name, period_start DESC);

-- 4. Anonymous Customer Profiles — aggregated per-person behavior (no PII)
CREATE TABLE IF NOT EXISTS anonymous_customer_profiles (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    person_id       TEXT NOT NULL,
    first_seen      TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ,
    total_visits    INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    total_spend_cents INTEGER DEFAULT 0,
    avg_dwell_seconds FLOAT DEFAULT 0,
    favorite_zones  TEXT[] DEFAULT '{}',
    typical_path    TEXT[] DEFAULT '{}',
    gestures_observed TEXT[] DEFAULT '{}',
    segment         TEXT DEFAULT 'unknown',
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (org_id, person_id)
);

CREATE INDEX IF NOT EXISTS idx_acp_org_segment
    ON anonymous_customer_profiles (org_id, segment);

CREATE INDEX IF NOT EXISTS idx_acp_person
    ON anonymous_customer_profiles (org_id, person_id);

-- Row-Level Security
ALTER TABLE customer_journeys ENABLE ROW LEVEL SECURITY;
ALTER TABLE cross_reference_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE zone_purchase_correlation ENABLE ROW LEVEL SECURITY;
ALTER TABLE anonymous_customer_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_isolation_cj" ON customer_journeys
    USING (org_id = current_setting('app.current_org_id', true));

CREATE POLICY "org_isolation_cri" ON cross_reference_insights
    USING (org_id = current_setting('app.current_org_id', true));

CREATE POLICY "org_isolation_zpc" ON zone_purchase_correlation
    USING (org_id = current_setting('app.current_org_id', true));

CREATE POLICY "org_isolation_acp" ON anonymous_customer_profiles
    USING (org_id = current_setting('app.current_org_id', true));

COMMENT ON TABLE customer_journeys IS
    'Per-visit physical path through store zones, correlated with POS transaction.';
COMMENT ON TABLE cross_reference_insights IS
    'AI-generated insights from cross-referencing camera and POS data.';
COMMENT ON TABLE zone_purchase_correlation IS
    'Aggregated zone-level conversion and revenue metrics per period.';
COMMENT ON TABLE anonymous_customer_profiles IS
    'Aggregated behavioral profile per anonymous person_id (no PII stored).';
