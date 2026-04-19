-- ============================================================
-- PART 7: CONTINUOUS AGGREGATES (TimescaleDB)
-- Pre-computed rollups for fast dashboard queries
-- ============================================================

-- ============================================================
-- HOURLY REVENUE AGGREGATE
-- Powers: hourly heatmaps, peak hour analysis
-- ============================================================
CREATE MATERIALIZED VIEW hourly_revenue
WITH (timescaledb.continuous) AS
SELECT
    org_id,
    location_id,
    time_bucket('1 hour', transaction_at) AS hour_bucket,
    COUNT(*) AS transaction_count,
    SUM(total_cents) AS total_revenue_cents,
    SUM(tax_cents) AS total_tax_cents,
    SUM(tip_cents) AS total_tip_cents,
    SUM(discount_cents) AS total_discount_cents,
    AVG(total_cents)::INTEGER AS avg_ticket_cents,
    MAX(total_cents) AS max_ticket_cents,
    COUNT(DISTINCT employee_external_id) AS unique_employees,
    SUM(customer_count) AS total_customers,
    -- Payment method breakdown
    COUNT(*) FILTER (WHERE payment_method = 'cash') AS cash_count,
    COUNT(*) FILTER (WHERE payment_method = 'credit_card') AS credit_count,
    COUNT(*) FILTER (WHERE payment_method = 'debit_card') AS debit_count,
    COUNT(*) FILTER (WHERE payment_method = 'mobile_pay') AS mobile_count,
    -- Transaction type breakdown
    COUNT(*) FILTER (WHERE type = 'sale') AS sale_count,
    COUNT(*) FILTER (WHERE type = 'refund') AS refund_count,
    COUNT(*) FILTER (WHERE type = 'void') AS void_count
FROM transactions
GROUP BY org_id, location_id, time_bucket('1 hour', transaction_at);

-- Refresh policy: every hour, covering last 3 hours
SELECT add_continuous_aggregate_policy('hourly_revenue',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- ============================================================
-- DAILY REVENUE AGGREGATE
-- Powers: daily dashboard, week-over-week comparisons
-- ============================================================
CREATE MATERIALIZED VIEW daily_revenue
WITH (timescaledb.continuous) AS
SELECT
    org_id,
    location_id,
    time_bucket('1 day', transaction_at) AS day_bucket,
    COUNT(*) AS transaction_count,
    SUM(total_cents) AS total_revenue_cents,
    SUM(tax_cents) AS total_tax_cents,
    SUM(tip_cents) AS total_tip_cents,
    SUM(discount_cents) AS total_discount_cents,
    AVG(total_cents)::INTEGER AS avg_ticket_cents,
    COUNT(DISTINCT employee_external_id) AS unique_employees,
    SUM(customer_count) AS total_customers,
    SUM(CASE WHEN type = 'refund' THEN total_cents ELSE 0 END) AS refund_total_cents,
    COUNT(*) FILTER (WHERE type = 'refund') AS refund_count
FROM transactions
GROUP BY org_id, location_id, time_bucket('1 day', transaction_at);

SELECT add_continuous_aggregate_policy('daily_revenue',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

-- ============================================================
-- DAILY PRODUCT PERFORMANCE
-- Powers: product scorecards, menu optimization
-- ============================================================
CREATE MATERIALIZED VIEW daily_product_performance
WITH (timescaledb.continuous) AS
SELECT
    ti.org_id,
    ti.product_id,
    time_bucket('1 day', ti.transaction_at) AS day_bucket,
    COUNT(*) AS times_sold,
    SUM(ti.quantity) AS total_quantity,
    SUM(ti.total_cents) AS total_revenue_cents,
    SUM(ti.discount_cents) AS total_discount_cents,
    SUM(ti.cost_cents * ti.quantity)::INTEGER AS total_cost_cents,
    AVG(ti.unit_price_cents)::INTEGER AS avg_unit_price_cents
FROM transaction_items ti
GROUP BY ti.org_id, ti.product_id, time_bucket('1 day', ti.transaction_at);

SELECT add_continuous_aggregate_policy('daily_product_performance',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

-- ============================================================
-- WEEKLY REVENUE AGGREGATE
-- Powers: weekly reports, trend analysis
-- ============================================================
CREATE MATERIALIZED VIEW weekly_revenue
WITH (timescaledb.continuous) AS
SELECT
    org_id,
    location_id,
    time_bucket('7 days', transaction_at) AS week_bucket,
    COUNT(*) AS transaction_count,
    SUM(total_cents) AS total_revenue_cents,
    AVG(total_cents)::INTEGER AS avg_ticket_cents,
    SUM(customer_count) AS total_customers
FROM transactions
GROUP BY org_id, location_id, time_bucket('7 days', transaction_at);

SELECT add_continuous_aggregate_policy('weekly_revenue',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '7 days',
    schedule_interval => INTERVAL '1 day'
);
