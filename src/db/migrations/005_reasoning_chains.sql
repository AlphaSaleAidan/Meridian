-- Karpathy reasoning chains + Cline agent tables
-- Supports full audit trail for AI agent reasoning

-- Agent reasoning chains — the 5-phase Karpathy loop output
CREATE TABLE IF NOT EXISTS agent_reasoning_chains (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    business_id     UUID NOT NULL,
    agent_name      TEXT NOT NULL,
    domain          TEXT NOT NULL,
    trigger         TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled | manual | anomaly | webhook
    phases          JSONB NOT NULL DEFAULT '[]',
    final_confidence REAL CHECK (final_confidence BETWEEN 0 AND 1),
    confidence_level TEXT CHECK (confidence_level IN ('HIGH', 'MEDIUM', 'LOW')),
    verdict         TEXT CHECK (verdict IN ('actionable', 'monitoring', 'no_action', 'insufficient_data')),
    impact_cents    INTEGER DEFAULT 0,
    caveats         TEXT[] DEFAULT '{}',
    total_duration_ms INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reasoning_chains_business ON agent_reasoning_chains (business_id, created_at DESC);
CREATE INDEX idx_reasoning_chains_agent ON agent_reasoning_chains (agent_name, created_at DESC);
CREATE INDEX idx_reasoning_chains_verdict ON agent_reasoning_chains (verdict) WHERE verdict = 'actionable';

-- Cline conversations — agent interaction sessions
CREATE TABLE IF NOT EXISTS cline_conversations (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    business_id     UUID NOT NULL,
    chain_id        UUID REFERENCES agent_reasoning_chains(id) ON DELETE SET NULL,
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed')),
    context         JSONB NOT NULL DEFAULT '{}',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cline_conv_business ON cline_conversations (business_id, created_at DESC);
CREATE INDEX idx_cline_conv_chain ON cline_conversations (chain_id);

-- Cline messages — individual reasoning steps
CREATE TABLE IF NOT EXISTS cline_messages (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES cline_conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('agent', 'system', 'data')),
    phase           TEXT CHECK (phase IN ('think', 'hypothesize', 'experiment', 'synthesize', 'reflect')),
    content         TEXT NOT NULL,
    data            JSONB,
    token_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cline_msg_conv ON cline_messages (conversation_id, created_at);

-- Cline errors — when reasoning goes wrong
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

CREATE INDEX idx_cline_errors_business ON cline_errors (business_id, created_at DESC);
CREATE INDEX idx_cline_errors_agent ON cline_errors (agent_name, created_at DESC);

-- Merchant health — aggregate health scores per domain
CREATE TABLE IF NOT EXISTS merchant_health (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    business_id     UUID NOT NULL,
    score           SMALLINT NOT NULL CHECK (score BETWEEN 0 AND 100),
    category        TEXT NOT NULL CHECK (category IN ('revenue', 'operations', 'customers', 'staff', 'inventory', 'overall')),
    factors         JSONB NOT NULL DEFAULT '{}',
    trend           TEXT CHECK (trend IN ('improving', 'stable', 'declining')),
    measured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_merchant_health_business ON merchant_health (business_id, category, measured_at DESC);

-- RLS policies (scoped to business_id)
ALTER TABLE agent_reasoning_chains ENABLE ROW LEVEL SECURITY;
ALTER TABLE cline_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cline_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE cline_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchant_health ENABLE ROW LEVEL SECURITY;
