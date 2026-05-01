-- Vision Intelligence v2 — Palantir-grade analytics schema
-- 4 new tables: foot_traffic, customer_profiles, customer_visits, vision_insights

-- ── 1. Foot Traffic (15-min windows with full demographic + passerby breakdown) ──

CREATE TABLE IF NOT EXISTS foot_traffic (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    camera_id           UUID NOT NULL REFERENCES vision_cameras(id) ON DELETE CASCADE,
    window_start        TIMESTAMPTZ NOT NULL,
    window_end          TIMESTAMPTZ NOT NULL,
    passerby_count      INTEGER NOT NULL DEFAULT 0,
    window_shoppers     INTEGER NOT NULL DEFAULT 0,
    walk_ins            INTEGER NOT NULL DEFAULT 0,
    walk_outs           INTEGER NOT NULL DEFAULT 0,
    male_count          INTEGER NOT NULL DEFAULT 0,
    female_count        INTEGER NOT NULL DEFAULT 0,
    age_buckets         JSONB NOT NULL DEFAULT '{}',
    returning_count     INTEGER NOT NULL DEFAULT 0,
    new_face_count      INTEGER NOT NULL DEFAULT 0,
    non_customer_count  INTEGER NOT NULL DEFAULT 0,
    sentiment_summary   JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_foot_traffic_upsert
    ON foot_traffic(org_id, camera_id, window_start);
CREATE INDEX idx_foot_traffic_org_time
    ON foot_traffic(org_id, window_start DESC);


-- ── 2. Customer Profiles (anonymous until opt-in, 90-day auto-purge) ──

CREATE TABLE IF NOT EXISTS customer_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    embedding_hash      TEXT NOT NULL,
    visit_count         INTEGER NOT NULL DEFAULT 1,
    first_seen          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT now(),
    avg_dwell_sec       FLOAT NOT NULL DEFAULT 0,
    favorite_zone       TEXT NOT NULL DEFAULT '',
    visit_pattern       TEXT NOT NULL DEFAULT '',
    gender              TEXT NOT NULL DEFAULT '',
    age_range           TEXT NOT NULL DEFAULT '',
    avg_sentiment       TEXT NOT NULL DEFAULT '',
    total_pos_spend_cents INTEGER NOT NULL DEFAULT 0,
    predicted_ltv       INTEGER NOT NULL DEFAULT 0,
    is_opted_in         BOOLEAN NOT NULL DEFAULT FALSE,
    tags                TEXT[] NOT NULL DEFAULT '{}',
    linked_customer_id  UUID,
    expires_at          TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '90 days'),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_customer_profiles_org
    ON customer_profiles(org_id);
CREATE UNIQUE INDEX idx_customer_profiles_hash
    ON customer_profiles(org_id, embedding_hash);
CREATE INDEX idx_customer_profiles_last_seen
    ON customer_profiles(org_id, last_seen DESC);
CREATE INDEX idx_customer_profiles_ltv
    ON customer_profiles(org_id, predicted_ltv DESC);
CREATE INDEX idx_customer_profiles_expires
    ON customer_profiles(expires_at);


-- ── 3. Customer Visits (per-visit record with emotion + POS match) ──

CREATE TABLE IF NOT EXISTS customer_visits (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    profile_id          UUID REFERENCES customer_profiles(id) ON DELETE SET NULL,
    entered_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    exited_at           TIMESTAMPTZ,
    dwell_seconds       INTEGER,
    zones_visited       TEXT[] NOT NULL DEFAULT '{}',
    emotion_entry       TEXT NOT NULL DEFAULT '',
    emotion_exit        TEXT NOT NULL DEFAULT '',
    pos_transaction_id  UUID,
    was_window_shopper  BOOLEAN NOT NULL DEFAULT FALSE,
    converted_later     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_customer_visits_org
    ON customer_visits(org_id, entered_at DESC);
CREATE INDEX idx_customer_visits_profile
    ON customer_visits(profile_id, entered_at DESC);


-- ── 4. Vision Insights (AI-generated, upsert per org+type+period) ──

CREATE TABLE IF NOT EXISTS vision_insights (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type                TEXT NOT NULL,
    title               TEXT NOT NULL,
    body                TEXT NOT NULL,
    data                JSONB NOT NULL DEFAULT '{}',
    confidence          FLOAT NOT NULL DEFAULT 0.5,
    period              TEXT NOT NULL DEFAULT '7d',
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_vision_insights_upsert
    ON vision_insights(org_id, type, period);
CREATE INDEX idx_vision_insights_org
    ON vision_insights(org_id, generated_at DESC);


-- ══════════════════════════════════════════════════════════════
--  ROW LEVEL SECURITY
-- ══════════════════════════════════════════════════════════════

ALTER TABLE foot_traffic ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_insights ENABLE ROW LEVEL SECURITY;

-- Org-scoped read policies
CREATE POLICY foot_traffic_org_read ON foot_traffic
    FOR SELECT USING (org_id = auth.uid()::uuid);
CREATE POLICY customer_profiles_org_read ON customer_profiles
    FOR SELECT USING (org_id = auth.uid()::uuid);
CREATE POLICY customer_visits_org_read ON customer_visits
    FOR SELECT USING (org_id = auth.uid()::uuid);
CREATE POLICY vision_insights_org_read ON vision_insights
    FOR SELECT USING (org_id = auth.uid()::uuid);

-- Service role bypass (for edge ingest + insight generation)
CREATE POLICY foot_traffic_service ON foot_traffic
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY customer_profiles_service ON customer_profiles
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY customer_visits_service ON customer_visits
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY vision_insights_service ON vision_insights
    FOR ALL USING (auth.role() = 'service_role');


-- ══════════════════════════════════════════════════════════════
--  AUTO-CLEANUP: expired profiles + visits (run via pg_cron)
-- ══════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION cleanup_expired_profiles()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete visits for expired profiles
    DELETE FROM customer_visits
    WHERE profile_id IN (
        SELECT id FROM customer_profiles WHERE expires_at < now()
    );

    -- Delete expired profiles
    WITH deleted AS (
        DELETE FROM customer_profiles
        WHERE expires_at < now() AND is_opted_in = FALSE
        RETURNING id
    )
    SELECT count(*) INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Right-to-forget: delete all data for a specific embedding
CREATE OR REPLACE FUNCTION forget_customer(target_org UUID, target_hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    DELETE FROM customer_visits
    WHERE profile_id IN (
        SELECT id FROM customer_profiles
        WHERE org_id = target_org AND embedding_hash = target_hash
    );

    DELETE FROM customer_profiles
    WHERE org_id = target_org AND embedding_hash = target_hash;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
