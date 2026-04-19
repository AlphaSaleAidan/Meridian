-- ============================================================
-- PART 9: FUNCTIONS, TRIGGERS & UTILITY
-- ============================================================

-- ============================================================
-- AUTO-UPDATE updated_at TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_locations_updated_at
    BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_pos_connections_updated_at
    BEFORE UPDATE ON pos_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_product_categories_updated_at
    BEFORE UPDATE ON product_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_suppliers_updated_at
    BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_scheduled_events_updated_at
    BEFORE UPDATE ON scheduled_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_notification_rules_updated_at
    BEFORE UPDATE ON notification_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_insights_updated_at
    BEFORE UPDATE ON insights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_benchmark_profiles_updated_at
    BEFORE UPDATE ON benchmark_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- FUNCTION: Get dashboard summary for an org
-- Used by the main dashboard to get all KPIs in one call
-- ============================================================
CREATE OR REPLACE FUNCTION get_dashboard_summary(
    p_org_id UUID,
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_revenue_cents', COALESCE(SUM(total_revenue_cents), 0),
        'transaction_count', COALESCE(SUM(transaction_count), 0),
        'avg_ticket_cents', COALESCE(AVG(avg_ticket_cents)::INTEGER, 0),
        'total_customers', COALESCE(SUM(total_customers), 0),
        'unique_employees', COALESCE(MAX(unique_employees), 0),
        'refund_total_cents', COALESCE(SUM(refund_total_cents), 0),
        'refund_count', COALESCE(SUM(refund_count), 0)
    ) INTO result
    FROM daily_revenue
    WHERE org_id = p_org_id
        AND day_bucket >= p_start_date
        AND day_bucket <= p_end_date;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================
-- FUNCTION: Get product leaderboard
-- ============================================================
CREATE OR REPLACE FUNCTION get_product_leaderboard(
    p_org_id UUID,
    p_days INTEGER DEFAULT 30,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    product_id UUID,
    product_name TEXT,
    total_revenue_cents BIGINT,
    total_quantity NUMERIC,
    times_sold BIGINT,
    avg_price_cents INTEGER,
    margin_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dpp.product_id,
        p.name AS product_name,
        SUM(dpp.total_revenue_cents)::BIGINT,
        SUM(dpp.total_quantity),
        SUM(dpp.times_sold)::BIGINT,
        AVG(dpp.avg_unit_price_cents)::INTEGER,
        CASE
            WHEN SUM(dpp.total_revenue_cents) > 0 AND SUM(dpp.total_cost_cents) > 0
            THEN ROUND(
                (1 - SUM(dpp.total_cost_cents)::NUMERIC / SUM(dpp.total_revenue_cents)::NUMERIC) * 100,
                1
            )
            ELSE NULL
        END
    FROM daily_product_performance dpp
    JOIN products p ON p.id = dpp.product_id
    WHERE dpp.org_id = p_org_id
        AND dpp.day_bucket >= CURRENT_DATE - (p_days || ' days')::INTERVAL
    GROUP BY dpp.product_id, p.name
    ORDER BY SUM(dpp.total_revenue_cents) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================
-- FUNCTION: Get hourly heatmap data
-- ============================================================
CREATE OR REPLACE FUNCTION get_hourly_heatmap(
    p_org_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    day_of_week INTEGER,
    hour_of_day INTEGER,
    avg_revenue_cents NUMERIC,
    avg_transaction_count NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        EXTRACT(DOW FROM hour_bucket)::INTEGER AS day_of_week,
        EXTRACT(HOUR FROM hour_bucket)::INTEGER AS hour_of_day,
        ROUND(AVG(total_revenue_cents), 0) AS avg_revenue_cents,
        ROUND(AVG(transaction_count), 1) AS avg_transaction_count
    FROM hourly_revenue
    WHERE org_id = p_org_id
        AND hour_bucket >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY
        EXTRACT(DOW FROM hour_bucket),
        EXTRACT(HOUR FROM hour_bucket)
    ORDER BY day_of_week, hour_of_day;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================
-- FUNCTION: Get benchmark comparison
-- Returns how a merchant compares to peers
-- ============================================================
CREATE OR REPLACE FUNCTION get_benchmark_comparison(
    p_org_id UUID
)
RETURNS JSONB AS $$
DECLARE
    merchant_profile benchmark_profiles;
    result JSONB;
BEGIN
    -- Get merchant's benchmark profile
    SELECT * INTO merchant_profile
    FROM benchmark_profiles
    WHERE org_id = p_org_id
    LIMIT 1;

    IF merchant_profile IS NULL THEN
        RETURN '{"error": "No benchmark profile found"}'::JSONB;
    END IF;

    -- Get latest industry aggregate for their peer group
    SELECT jsonb_build_object(
        'peer_group', jsonb_build_object(
            'vertical', ia.vertical,
            'region', ia.region,
            'revenue_band', ia.revenue_band,
            'sample_size', ia.sample_size
        ),
        'benchmarks', jsonb_build_object(
            'avg_ticket_cents', ia.avg_ticket_cents,
            'avg_transactions_per_day', ia.avg_transactions_per_day,
            'avg_daily_revenue_cents', ia.avg_daily_revenue_cents,
            'avg_margin_pct', ia.avg_margin_pct,
            'avg_waste_pct', ia.avg_waste_pct
        ),
        'period', jsonb_build_object(
            'start', ia.period_start,
            'end', ia.period_end
        )
    ) INTO result
    FROM industry_aggregates ia
    WHERE ia.vertical = merchant_profile.vertical
        AND ia.region = merchant_profile.region
        AND ia.revenue_band = merchant_profile.revenue_band
        AND ia.period_type = 'monthly'
    ORDER BY ia.period_start DESC
    LIMIT 1;

    RETURN COALESCE(result, '{"error": "No benchmark data available yet"}'::JSONB);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================
-- FUNCTION: Create new organization with defaults
-- Called during onboarding after user signs up
-- ============================================================
CREATE OR REPLACE FUNCTION create_organization(
    p_user_id UUID,
    p_org_name TEXT,
    p_vertical business_vertical,
    p_email TEXT,
    p_first_name TEXT,
    p_last_name TEXT
)
RETURNS UUID AS $$
DECLARE
    new_org_id UUID;
    new_location_id UUID;
BEGIN
    -- Create org
    INSERT INTO organizations (name, slug, vertical, email)
    VALUES (
        p_org_name,
        LOWER(REGEXP_REPLACE(p_org_name, '[^a-zA-Z0-9]', '-', 'g')),
        p_vertical,
        p_email
    )
    RETURNING id INTO new_org_id;

    -- Create default primary location
    INSERT INTO locations (org_id, name, is_primary)
    VALUES (new_org_id, 'Main Location', TRUE)
    RETURNING id INTO new_location_id;

    -- Link user to org as owner
    INSERT INTO users (id, org_id, role, first_name, last_name, email)
    VALUES (p_user_id, new_org_id, 'owner', p_first_name, p_last_name, p_email);

    -- Create trial subscription
    INSERT INTO subscriptions (org_id, tier, status, trial_starts_at, trial_ends_at)
    VALUES (
        new_org_id,
        'trial',
        'trialing',
        NOW(),
        NOW() + INTERVAL '30 days'
    );

    -- Create default notification rules
    INSERT INTO notification_rules (org_id, name, trigger_type, trigger_config, notify_roles, channels)
    VALUES
        (new_org_id, 'Delivery Reminder (24h)', 'delivery_reminder',
         '{"hours_before": 24}', '{owner,manager}', '{email}'),
        (new_org_id, 'Delivery Reminder (2h)', 'delivery_reminder',
         '{"hours_before": 2}', '{owner,manager}', '{sms}'),
        (new_org_id, 'Low Stock Alert', 'low_stock',
         '{"threshold_pct": 20}', '{owner,manager}', '{email,push}'),
        (new_org_id, 'Sales Anomaly', 'anomaly_detection',
         '{"deviation_pct": 25}', '{owner}', '{sms,email}'),
        (new_org_id, 'Weekly Report', 'weekly_report',
         '{"day": "monday", "hour": 7}', '{owner}', '{email}');

    -- Create benchmark profile
    INSERT INTO benchmark_profiles (org_id, vertical, region, revenue_band)
    VALUES (new_org_id, p_vertical, 'unknown', 'unknown');

    RETURN new_org_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- COMPRESSION POLICY for old time-series data
-- Saves storage costs on historical data
-- ============================================================
ALTER TABLE transactions SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'org_id',
    timescaledb.compress_orderby = 'transaction_at DESC'
);

SELECT add_compression_policy('transactions', INTERVAL '6 months');

ALTER TABLE transaction_items SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'org_id',
    timescaledb.compress_orderby = 'transaction_at DESC'
);

SELECT add_compression_policy('transaction_items', INTERVAL '6 months');

ALTER TABLE inventory_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'org_id',
    timescaledb.compress_orderby = 'snapshot_at DESC'
);

SELECT add_compression_policy('inventory_snapshots', INTERVAL '3 months');
