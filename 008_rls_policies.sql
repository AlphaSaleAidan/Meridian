-- ============================================================
-- PART 8: ROW-LEVEL SECURITY (RLS) POLICIES
-- Ensures complete data isolation between merchants
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE money_left_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_profiles ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- HELPER FUNCTION: Get current user's org_id
-- ============================================================
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
    SELECT org_id FROM users WHERE id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER STABLE;

-- ============================================================
-- HELPER FUNCTION: Get current user's role
-- ============================================================
CREATE OR REPLACE FUNCTION get_user_role()
RETURNS user_role AS $$
    SELECT role FROM users WHERE id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER STABLE;

-- ============================================================
-- POLICIES: Users can only see data for their own organization
-- ============================================================

-- Organizations
CREATE POLICY "Users can view own org"
    ON organizations FOR SELECT
    USING (id = get_user_org_id());

CREATE POLICY "Owners can update own org"
    ON organizations FOR UPDATE
    USING (id = get_user_org_id() AND get_user_role() = 'owner');

-- Locations
CREATE POLICY "Users can view own locations"
    ON locations FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners/managers can manage locations"
    ON locations FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() IN ('owner', 'manager'));

-- Users
CREATE POLICY "Users can view team members in own org"
    ON users FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners can manage users"
    ON users FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() = 'owner');

CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (id = auth.uid());

-- Subscriptions
CREATE POLICY "Users can view own subscription"
    ON subscriptions FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners can manage subscription"
    ON subscriptions FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() = 'owner');

-- POS Connections
CREATE POLICY "Users can view own POS connections"
    ON pos_connections FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners/managers can manage POS connections"
    ON pos_connections FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() IN ('owner', 'manager'));

-- Products
CREATE POLICY "Users can view own products"
    ON products FOR SELECT
    USING (org_id = get_user_org_id());

-- Product Categories
CREATE POLICY "Users can view own categories"
    ON product_categories FOR SELECT
    USING (org_id = get_user_org_id());

-- Transactions (hypertable)
CREATE POLICY "Users can view own transactions"
    ON transactions FOR SELECT
    USING (org_id = get_user_org_id());

-- Transaction Items (hypertable)
CREATE POLICY "Users can view own transaction items"
    ON transaction_items FOR SELECT
    USING (org_id = get_user_org_id());

-- Inventory Snapshots
CREATE POLICY "Users can view own inventory"
    ON inventory_snapshots FOR SELECT
    USING (org_id = get_user_org_id());

-- Suppliers
CREATE POLICY "Users can view own suppliers"
    ON suppliers FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners/managers can manage suppliers"
    ON suppliers FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() IN ('owner', 'manager'));

-- Scheduled Events
CREATE POLICY "Users can view own events"
    ON scheduled_events FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners/managers can manage events"
    ON scheduled_events FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() IN ('owner', 'manager'));

-- Notifications
CREATE POLICY "Users can view own notifications"
    ON notifications FOR SELECT
    USING (user_id = auth.uid());

-- Notification Rules
CREATE POLICY "Users can view org notification rules"
    ON notification_rules FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Owners can manage notification rules"
    ON notification_rules FOR ALL
    USING (org_id = get_user_org_id() AND get_user_role() = 'owner');

-- Insights
CREATE POLICY "Users can view own insights"
    ON insights FOR SELECT
    USING (org_id = get_user_org_id());

-- Money Left Scores
CREATE POLICY "Users can view own scores"
    ON money_left_scores FOR SELECT
    USING (org_id = get_user_org_id());

-- Forecasts
CREATE POLICY "Users can view own forecasts"
    ON forecasts FOR SELECT
    USING (org_id = get_user_org_id());

-- Chat Conversations
CREATE POLICY "Users can view own conversations"
    ON chat_conversations FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can create conversations"
    ON chat_conversations FOR INSERT
    WITH CHECK (user_id = auth.uid() AND org_id = get_user_org_id());

-- Chat Messages
CREATE POLICY "Users can view messages in own conversations"
    ON chat_messages FOR SELECT
    USING (org_id = get_user_org_id());

-- Weekly Reports
CREATE POLICY "Users can view own reports"
    ON weekly_reports FOR SELECT
    USING (org_id = get_user_org_id());

-- Benchmark Profiles (users can see own, anonymized data is separate)
CREATE POLICY "Users can view own benchmark profile"
    ON benchmark_profiles FOR SELECT
    USING (org_id = get_user_org_id());

-- ============================================================
-- NOTE: industry_aggregates and benchmark_snapshots do NOT have
-- RLS because they contain only anonymized, aggregated data.
-- They're accessed via API functions that check subscription tier.
-- ============================================================
