-- Insight Library backend storage + lifecycle gate (DB-level belt-and-suspenders).
--
-- The canonical catalog ships as a version-controlled JSONL in the backend
-- (src/ai/insight_library/data/insight_catalog.jsonl); this table is the
-- optional queryable store. Critically, it enforces the SAME gate the app does:
-- a row carrying an unfilled {x} placeholder can NEVER be marked proven/published,
-- so a half-finished insight cannot be persisted in a customer-servable state
-- even by a buggy writer.

CREATE TABLE IF NOT EXISTS insight_templates (
    id              TEXT PRIMARY KEY,
    org_id          UUID,                       -- NULL for library rows; set when filled for a merchant
    domain          TEXT NOT NULL,
    archetype       TEXT NOT NULL,
    vertical        TEXT NOT NULL,
    situation       TEXT NOT NULL,
    title           TEXT NOT NULL,
    reasoning       JSONB NOT NULL,             -- {observation, reasoning, conclusion, expected_effect}
    required_signals JSONB NOT NULL DEFAULT '[]',
    required_agents  JSONB NOT NULL DEFAULT '[]',
    swarm_capability TEXT NOT NULL DEFAULT 'full',
    swarm_upgrade    TEXT NOT NULL DEFAULT '',
    recommend_when   JSONB NOT NULL DEFAULT '{}',
    tags             JSONB NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'template'
                    CHECK (status IN ('template','candidate','proven','published','rejected')),
    reject_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_insight_templates_lookup
    ON insight_templates (vertical, domain, status);
CREATE INDEX IF NOT EXISTS idx_insight_templates_org
    ON insight_templates (org_id, status) WHERE org_id IS NOT NULL;

-- ── DB-level gate ────────────────────────────────────────────────────────────
-- Reject any attempt to mark a row proven/published while its text still contains
-- an unfilled placeholder. Mirrors schema.is_portal_safe at the storage layer.
CREATE OR REPLACE FUNCTION insight_templates_gate() RETURNS trigger AS $$
DECLARE
    blob TEXT;
BEGIN
    IF NEW.status IN ('proven','published') THEN
        blob := coalesce(NEW.title,'') || ' ' ||
                coalesce(NEW.reasoning->>'observation','') || ' ' ||
                coalesce(NEW.reasoning->>'reasoning','') || ' ' ||
                coalesce(NEW.reasoning->>'conclusion','') || ' ' ||
                coalesce(NEW.reasoning->>'expected_effect','');
        IF blob ~ '\{x\b[^}]*\}' OR blob ~ '\{[a-z_]+\}' THEN
            RAISE EXCEPTION 'insight % cannot be % — unfilled placeholder present', NEW.id, NEW.status;
        END IF;
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_insight_templates_gate ON insight_templates;
CREATE TRIGGER trg_insight_templates_gate
    BEFORE INSERT OR UPDATE ON insight_templates
    FOR EACH ROW EXECUTE FUNCTION insight_templates_gate();

-- RLS: library rows (org_id IS NULL) readable by authenticated; merchant-filled
-- rows (org_id set) scoped to the org. Customer portals must ALSO filter
-- status='published' in app code (serve_for_portal) — this is defense in depth.
ALTER TABLE insight_templates ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "insight_templates_read" ON insight_templates;
    CREATE POLICY "insight_templates_read" ON insight_templates FOR SELECT
        USING (
            org_id IS NULL
            OR org_id IN (SELECT org_id FROM business_users WHERE user_id = auth.uid())
        );
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
