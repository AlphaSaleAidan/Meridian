-- Cline Self-Healing Agent + Karpathy Reasoning Framework
-- Tables: agent_reasoning_chains, cline_conversations, cline_messages,
--         cline_errors, merchant_health
-- RLS: org_id (business_id) scoped. IT dashboard uses service role to bypass.

-- ═══════════════════════════════════════════════════════════
-- Agent reasoning chains — 5-phase Karpathy loop audit trail
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS agent_reasoning_chains (
    id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    business_id       UUID NOT NULL,
    agent_name        TEXT NOT NULL,
    domain            TEXT NOT NULL,
    trigger           TEXT NOT NULL DEFAULT 'scheduled'
                      CHECK (trigger IN ('scheduled', 'manual', 'anomaly', 'webhook', 'error_detected')),
    phases            JSONB NOT NULL DEFAULT '[]',
    final_confidence  REAL CHECK (final_confidence BETWEEN 0 AND 1),
    confidence_level  TEXT CHECK (confidence_level IN ('HIGH', 'MEDIUM', 'LOW')),
    verdict           TEXT CHECK (verdict IN ('actionable', 'monitoring', 'no_action', 'insufficient_data')),
    impact_cents      INTEGER DEFAULT 0,
    caveats           TEXT[] DEFAULT '{}',
    total_duration_ms INTEGER DEFAULT 0,
    started_at        TIMESTAMPTZ NOT NULL,
    completed_at      TIMESTAMPTZ,
    error             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_arc_business
    ON agent_reasoning_chains (business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_arc_agent
    ON agent_reasoning_chains (agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_arc_actionable
    ON agent_reasoning_chains (verdict) WHERE verdict = 'actionable';

-- ═══════════════════════════════════════════════════════════
-- Cline conversations — agent interaction sessions
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS cline_conversations (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    business_id     UUID NOT NULL,
    chain_id        UUID REFERENCES agent_reasoning_chains(id) ON DELETE SET NULL,
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'failed')),
    context         JSONB NOT NULL DEFAULT '{}',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cc_business
    ON cline_conversations (business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cc_chain
    ON cline_conversations (chain_id);

-- ═══════════════════════════════════════════════════════════
-- Cline messages — individual reasoning steps / chat messages
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS cline_messages (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES cline_conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('agent', 'system', 'data', 'user')),
    phase           TEXT CHECK (phase IN ('think', 'hypothesize', 'experiment', 'synthesize', 'reflect')),
    content         TEXT NOT NULL,
    data            JSONB,
    token_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cm_conv
    ON cline_messages (conversation_id, created_at);

-- ═══════════════════════════════════════════════════════════
-- Cline errors — captured system errors with context
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS cline_errors (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES cline_conversations(id) ON DELETE SET NULL,
    chain_id        UUID REFERENCES agent_reasoning_chains(id) ON DELETE SET NULL,
    agent_name      TEXT NOT NULL,
    business_id     UUID NOT NULL,
    phase           TEXT CHECK (phase IN ('think', 'hypothesize', 'experiment', 'synthesize', 'reflect')),
    error_type      TEXT NOT NULL CHECK (error_type IN ('data_error', 'logic_error', 'timeout', 'api_error')),
    message         TEXT NOT NULL,
    stack_trace     TEXT,
    context         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ce_business
    ON cline_errors (business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ce_agent
    ON cline_errors (agent_name, created_at DESC);

-- ═══════════════════════════════════════════════════════════
-- Merchant health — aggregate health scores per domain
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS merchant_health (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    business_id     UUID NOT NULL,
    score           SMALLINT NOT NULL CHECK (score BETWEEN 0 AND 100),
    category        TEXT NOT NULL
                    CHECK (category IN ('revenue', 'operations', 'customers', 'staff', 'inventory', 'overall')),
    factors         JSONB NOT NULL DEFAULT '{}',
    trend           TEXT CHECK (trend IN ('improving', 'stable', 'declining')),
    measured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mh_business
    ON merchant_health (business_id, category, measured_at DESC);

-- ═══════════════════════════════════════════════════════════
-- Row Level Security — business_id scoped
-- ═══════════════════════════════════════════════════════════
ALTER TABLE agent_reasoning_chains ENABLE ROW LEVEL SECURITY;
ALTER TABLE cline_conversations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE cline_messages         ENABLE ROW LEVEL SECURITY;
ALTER TABLE cline_errors           ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchant_health        ENABLE ROW LEVEL SECURITY;

-- Org-scoped read: authenticated users see only their org's data
CREATE POLICY arc_org_read ON agent_reasoning_chains
    FOR SELECT USING (business_id = auth.uid()::uuid);
CREATE POLICY cc_org_read ON cline_conversations
    FOR SELECT USING (business_id = auth.uid()::uuid);
CREATE POLICY cm_org_read ON cline_messages
    FOR SELECT USING (
        conversation_id IN (
            SELECT id FROM cline_conversations WHERE business_id = auth.uid()::uuid
        )
    );
CREATE POLICY ce_org_read ON cline_errors
    FOR SELECT USING (business_id = auth.uid()::uuid);
CREATE POLICY mh_org_read ON merchant_health
    FOR SELECT USING (business_id = auth.uid()::uuid);

-- Service role bypass for IT dashboard and background workers
CREATE POLICY arc_service ON agent_reasoning_chains
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY cc_service ON cline_conversations
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY cm_service ON cline_messages
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY ce_service ON cline_errors
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY mh_service ON merchant_health
    FOR ALL USING (auth.role() = 'service_role');
