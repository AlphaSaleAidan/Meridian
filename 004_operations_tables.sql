-- ============================================================
-- PART 4: OPERATIONS LAYER
-- Delivery schedules, events, notifications, suppliers
-- ============================================================

-- ============================================================
-- SUPPLIERS / VENDORS
-- ============================================================
CREATE TABLE suppliers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    contact_name    TEXT,
    contact_phone   TEXT,
    contact_email   TEXT,
    address         TEXT,
    category        TEXT,  -- "food", "beverage", "supplies", etc.
    account_number  TEXT,
    notes           TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_suppliers_org ON suppliers(org_id);

-- ============================================================
-- SCHEDULED EVENTS (deliveries, inspections, meetings, etc.)
-- ============================================================
CREATE TABLE scheduled_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    location_id     UUID REFERENCES locations(id) ON DELETE SET NULL,
    supplier_id     UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    -- Event details
    title           TEXT NOT NULL,
    description     TEXT,
    event_type      event_type NOT NULL DEFAULT 'custom',
    -- Schedule
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ,
    all_day         BOOLEAN DEFAULT FALSE,
    -- Recurrence
    recurrence      event_recurrence DEFAULT 'none',
    recurrence_day  day_of_week,
    recurrence_time TIME,
    recurrence_ends_at TIMESTAMPTZ,
    parent_event_id UUID REFERENCES scheduled_events(id) ON DELETE SET NULL,
    -- Assignments
    assigned_to     UUID[] DEFAULT '{}',  -- user IDs who should be notified
    -- Status
    is_confirmed    BOOLEAN DEFAULT FALSE,
    confirmed_by    UUID REFERENCES users(id),
    confirmed_at    TIMESTAMPTZ,
    -- AI context
    ai_recommendations JSONB DEFAULT '{}',  -- e.g., {"reduce_order": "40% excess projected"}
    -- Checklist (for inspections, etc.)
    checklist       JSONB DEFAULT '[]',  -- [{"item": "Clean walk-in", "done": false}]
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_org_time ON scheduled_events(org_id, starts_at);
CREATE INDEX idx_events_type ON scheduled_events(org_id, event_type);
CREATE INDEX idx_events_supplier ON scheduled_events(supplier_id);
CREATE INDEX idx_events_upcoming ON scheduled_events(org_id, starts_at)
    WHERE starts_at > NOW();

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Notification content
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    channel         notification_channel NOT NULL,
    priority        notification_priority DEFAULT 'normal',
    -- Source (what triggered this notification)
    source_type     TEXT,  -- 'event', 'insight', 'alert', 'report'
    source_id       UUID,  -- ID of the triggering entity
    -- Delivery
    status          notification_status NOT NULL DEFAULT 'pending',
    scheduled_for   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at         TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    -- External IDs
    twilio_sid      TEXT,
    sendgrid_id     TEXT,
    -- Escalation
    escalation_level INTEGER DEFAULT 0,
    escalated_to    UUID REFERENCES users(id),
    escalated_at    TIMESTAMPTZ,
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_org ON notifications(org_id, created_at DESC);
CREATE INDEX idx_notifications_status ON notifications(status, scheduled_for)
    WHERE status = 'pending';
CREATE INDEX idx_notifications_source ON notifications(source_type, source_id);

-- ============================================================
-- NOTIFICATION RULES
-- Custom rules for who gets notified for what
-- ============================================================
CREATE TABLE notification_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    -- Rule definition
    name            TEXT NOT NULL,
    trigger_type    TEXT NOT NULL,  -- 'delivery_reminder', 'low_stock', 'anomaly', etc.
    trigger_config  JSONB NOT NULL DEFAULT '{}',  -- {"hours_before": 24, "threshold": 10}
    -- Recipients
    notify_roles    user_role[] DEFAULT '{owner}',
    notify_users    UUID[] DEFAULT '{}',  -- specific user overrides
    -- Notification settings
    channels        notification_channel[] DEFAULT '{email}',
    priority        notification_priority DEFAULT 'normal',
    -- Escalation
    escalate_after_minutes INTEGER,  -- escalate if not acknowledged
    escalate_to_role user_role DEFAULT 'owner',
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notification_rules_org ON notification_rules(org_id);
CREATE INDEX idx_notification_rules_trigger ON notification_rules(org_id, trigger_type);
