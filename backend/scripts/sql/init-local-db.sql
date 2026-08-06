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
