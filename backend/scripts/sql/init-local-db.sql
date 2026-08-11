-- Local development schema & seed data for the Meridian Kotlin backend.
-- Applied by scripts/init-local-db.sh. Idempotent — safe to re-run.
-- Staging/prod: apply the same DDL via Supabase migrations (spring.session.jdbc
-- initialize-schema is "embedded", so Boot never creates these tables on Postgres).

-- Application tables ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.businesses (
    id TEXT PRIMARY KEY,
    name TEXT,
    plan_tier TEXT,
    access_token TEXT,
    token_status TEXT,
    status TEXT,
    pos_provider TEXT,
    onboarded BOOLEAN DEFAULT FALSE
);

-- Login identity resolution (user_port slice) reads owner linkage + these tables.
-- Prod/staging already have them via Supabase migrations; IF NOT EXISTS keeps this idempotent.
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS owner_user_id UUID;

CREATE TABLE IF NOT EXISTS public.business_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id TEXT NOT NULL,
    user_id UUID,
    email TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'staff',
    location_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    login_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.admin_users (
    user_id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.sales_reps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE
);

-- Unified signup (invite redemption + self-serve business creation)
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS owner_name TEXT;
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS business_type TEXT;
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ;

-- Primary-business resolution orders by insertion date (oldest first).
ALTER TABLE public.businesses ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.business_users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.access_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE DEFAULT ('mtk_' || encode(gen_random_bytes(16), 'hex')),
    created_by TEXT,
    redeemed BOOLEAN NOT NULL DEFAULT FALSE,
    redeemed_at TIMESTAMPTZ,
    redeemed_by UUID,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.onboarding_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_by TEXT,
    notes TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarding_step ON public.onboarding_progress(business_id, step_name);

-- Seed default local test record
INSERT INTO public.businesses (id, name, plan_tier, access_token, token_status, status, pos_provider, onboarded)
VALUES ('demo-org-123', 'Maple Bakery', 'starter', 'demo-portal-token-999', 'active', 'active', 'square', true)
ON CONFLICT (id) DO NOTHING;

-- spring-session-jdbc tables --------------------------------------------------
-- Mirrors spring-session-jdbc's schema-postgresql.sql (with IF NOT EXISTS added).

CREATE TABLE IF NOT EXISTS public.spring_session (
    primary_id CHAR(36) NOT NULL,
    session_id CHAR(36) NOT NULL,
    creation_time BIGINT NOT NULL,
    last_access_time BIGINT NOT NULL,
    max_inactive_interval INT NOT NULL,
    expiry_time BIGINT NOT NULL,
    principal_name VARCHAR(100),
    CONSTRAINT spring_session_pk PRIMARY KEY (primary_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS spring_session_ix1 ON public.spring_session (session_id);
CREATE INDEX IF NOT EXISTS spring_session_ix2 ON public.spring_session (expiry_time);
CREATE INDEX IF NOT EXISTS spring_session_ix3 ON public.spring_session (principal_name);

CREATE TABLE IF NOT EXISTS public.spring_session_attributes (
    session_primary_id CHAR(36) NOT NULL,
    attribute_name VARCHAR(200) NOT NULL,
    attribute_bytes BYTEA NOT NULL,
    CONSTRAINT spring_session_attributes_pk PRIMARY KEY (session_primary_id, attribute_name),
    CONSTRAINT spring_session_attributes_fk FOREIGN KEY (session_primary_id)
        REFERENCES public.spring_session (primary_id) ON DELETE CASCADE
);
