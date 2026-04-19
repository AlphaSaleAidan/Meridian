-- ============================================================
-- PART 2: CORE TABLES
-- ============================================================

-- ============================================================
-- ORGANIZATIONS (the merchant business)
-- ============================================================
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    vertical        business_vertical NOT NULL DEFAULT 'other',
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT,
    country         TEXT DEFAULT 'US',
    timezone        TEXT DEFAULT 'America/Los_Angeles',
    phone           TEXT,
    email           TEXT,
    website         TEXT,
    logo_url        TEXT,
    business_hours  JSONB DEFAULT '{}',  -- {"monday": {"open": "09:00", "close": "21:00"}, ...}
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organizations_vertical ON organizations(vertical);
CREATE INDEX idx_organizations_city_state ON organizations(city, state);
CREATE INDEX idx_organizations_slug ON organizations(slug);

-- ============================================================
-- LOCATIONS (multi-location support for Tier 3)
-- ============================================================
CREATE TABLE locations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    is_primary      BOOLEAN DEFAULT FALSE,
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT,
    latitude        DECIMAL(10, 8),
    longitude       DECIMAL(11, 8),
    phone           TEXT,
    business_hours  JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_locations_org ON locations(org_id);
CREATE INDEX idx_locations_geo ON locations(latitude, longitude);

-- ============================================================
-- USERS (Supabase auth users linked to orgs)
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role            user_role NOT NULL DEFAULT 'viewer',
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    avatar_url      TEXT,
    notification_preferences JSONB DEFAULT '{
        "sms": true,
        "email": true,
        "push": true,
        "weekly_report": true,
        "daily_digest": false,
        "alert_delivery": true,
        "alert_inventory": true,
        "alert_anomaly": true
    }',
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(org_id, role);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================
CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    tier                subscription_tier NOT NULL DEFAULT 'trial',
    status              subscription_status NOT NULL DEFAULT 'trialing',
    stripe_customer_id  TEXT,
    stripe_subscription_id TEXT,
    trial_starts_at     TIMESTAMPTZ,
    trial_ends_at       TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end  TIMESTAMPTZ,
    monthly_price_cents INTEGER,  -- stored in cents
    canceled_at         TIMESTAMPTZ,
    cancel_reason       TEXT,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id)  -- one active subscription per org
);

CREATE INDEX idx_subscriptions_org ON subscriptions(org_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_customer_id);

-- ============================================================
-- POS CONNECTIONS
-- ============================================================
CREATE TABLE pos_connections (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    location_id         UUID REFERENCES locations(id) ON DELETE SET NULL,
    provider            pos_provider NOT NULL,
    status              pos_connection_status NOT NULL DEFAULT 'pending',
    -- OAuth tokens (encrypted at rest via Supabase Vault in production)
    access_token_enc    TEXT,
    refresh_token_enc   TEXT,
    token_expires_at    TIMESTAMPTZ,
    -- Provider-specific IDs
    external_merchant_id TEXT,
    external_location_id TEXT,
    -- Sync state
    last_sync_at        TIMESTAMPTZ,
    last_sync_status    TEXT,
    sync_cursor         TEXT,  -- pagination cursor for incremental sync
    historical_import_complete BOOLEAN DEFAULT FALSE,
    historical_import_started_at TIMESTAMPTZ,
    historical_import_completed_at TIMESTAMPTZ,
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pos_connections_org ON pos_connections(org_id);
CREATE INDEX idx_pos_connections_provider ON pos_connections(provider, status);
CREATE INDEX idx_pos_connections_sync ON pos_connections(last_sync_at);
