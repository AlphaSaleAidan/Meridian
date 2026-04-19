-- ============================================================
-- PART 6: BENCHMARKING & ANONYMIZED DATA WAREHOUSE
-- The sellable data asset
-- ============================================================

-- ============================================================
-- BENCHMARK PROFILES (anonymized merchant profiles for comparison)
-- ============================================================
CREATE TABLE benchmark_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    -- Anonymized classification (for matching)
    vertical        business_vertical NOT NULL,
    region          TEXT NOT NULL,  -- city or metro area
    revenue_band    TEXT NOT NULL,  -- 'under_50k', '50k_100k', '100k_250k', '250k_500k', '500k_plus'
    employee_count_band TEXT,       -- '1_5', '6_15', '16_50', '50_plus'
    -- Opt-in for benchmarking
    opted_in        BOOLEAN DEFAULT TRUE,
    opted_in_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_benchmark_profiles_match ON benchmark_profiles(vertical, region, revenue_band)
    WHERE opted_in = TRUE;

-- ============================================================
-- BENCHMARK SNAPSHOTS (weekly anonymized aggregates per merchant)
-- ============================================================
CREATE TABLE benchmark_snapshots (
    id              UUID DEFAULT uuid_generate_v4(),
    benchmark_profile_id UUID NOT NULL,
    -- Anonymized KPIs (no merchant-identifiable data)
    avg_ticket_cents    INTEGER,
    transactions_per_day DECIMAL(8, 2),
    revenue_per_day_cents INTEGER,
    top_category_pct    DECIMAL(5, 2),  -- % of revenue from top category
    product_count       INTEGER,
    avg_margin_pct      DECIMAL(5, 2),
    peak_hour           INTEGER,  -- 0-23
    busiest_day         day_of_week,
    inventory_turn_rate DECIMAL(6, 2),
    waste_pct           DECIMAL(5, 2),
    -- Period
    snapshot_week       DATE NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, snapshot_week)
);

SELECT create_hypertable('benchmark_snapshots', 'snapshot_week',
    chunk_time_interval => INTERVAL '3 months',
    if_not_exists => TRUE
);

CREATE INDEX idx_benchmark_snapshots_profile ON benchmark_snapshots(benchmark_profile_id, snapshot_week DESC);

-- ============================================================
-- AGGREGATED INDUSTRY DATA (the warehouse - fully anonymized)
-- This is the SELLABLE ASSET
-- ============================================================
CREATE TABLE industry_aggregates (
    id              UUID DEFAULT uuid_generate_v4(),
    -- Dimensions
    vertical        business_vertical NOT NULL,
    region          TEXT NOT NULL,
    revenue_band    TEXT NOT NULL,
    -- Time
    period_type     TEXT NOT NULL,  -- 'weekly', 'monthly', 'quarterly'
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    -- Aggregate metrics
    sample_size     INTEGER NOT NULL,  -- number of merchants in this bucket
    -- Revenue metrics
    avg_daily_revenue_cents INTEGER,
    median_daily_revenue_cents INTEGER,
    p25_daily_revenue_cents INTEGER,
    p75_daily_revenue_cents INTEGER,
    -- Transaction metrics
    avg_ticket_cents INTEGER,
    avg_transactions_per_day DECIMAL(8, 2),
    -- Product metrics
    avg_product_count INTEGER,
    avg_active_products INTEGER,
    top_performing_categories JSONB DEFAULT '[]',
    -- Operational metrics
    avg_peak_hour INTEGER,
    avg_margin_pct DECIMAL(5, 2),
    avg_waste_pct DECIMAL(5, 2),
    avg_inventory_turn DECIMAL(6, 2),
    -- Trends
    revenue_trend_pct DECIMAL(5, 2),  -- vs. previous period
    transaction_trend_pct DECIMAL(5, 2),
    -- Metadata
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, period_start)
);

SELECT create_hypertable('industry_aggregates', 'period_start',
    chunk_time_interval => INTERVAL '3 months',
    if_not_exists => TRUE
);

CREATE INDEX idx_industry_agg_lookup ON industry_aggregates(vertical, region, revenue_band, period_start DESC);
CREATE INDEX idx_industry_agg_period ON industry_aggregates(period_type, period_start DESC);

-- ============================================================
-- DATA EXPORT LOGS (track what's been exported/sold)
-- ============================================================
CREATE TABLE data_export_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    export_type     TEXT NOT NULL,  -- 'api_access', 'report', 'dataset'
    requested_by    TEXT,  -- company name or API key
    -- What was exported
    verticals       business_vertical[] DEFAULT '{}',
    regions         TEXT[] DEFAULT '{}',
    period_start    DATE,
    period_end      DATE,
    record_count    INTEGER,
    -- Billing
    billed_amount_cents INTEGER,
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
