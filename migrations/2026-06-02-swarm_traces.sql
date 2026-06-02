-- 2026-06-02-swarm_traces.sql
-- Swarm trace table — Phase 0/Step 2 baseline instrumentation.
--
-- This table is intentionally SQLite-compatible (stdlib sqlite3 writer in
-- src/ai/trace_recorder.py). The same DDL applies cleanly to Postgres if
-- we later promote it to Supabase; SQLite is used today so the recorder is
-- a zero-dep, on-box, no-server tee with no extra requirements.
--
-- Schema follows docs/swarm_baseline.md §3.
-- One row per agent invocation (statistical agents) AND one row per LLM
-- call (LLM-calling agents). `tier` is NULL until the tier resolver lands
-- in Step 3; `escalated_from` is NULL until confidence-escalation lands.
--
-- Rollback: DROP TABLE swarm_traces;

CREATE TABLE IF NOT EXISTS swarm_traces (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id            TEXT NOT NULL,                    -- request-scoped uuid
    agent_name          TEXT NOT NULL,                    -- caller agent class / function
    tier                TEXT,                             -- T1/T2/T3 once tier resolver exists
    provider            TEXT,                             -- e.g. deepseek, sambanova, groq
    model               TEXT,                             -- LiteLLM response model id
    prompt_tokens       INTEGER DEFAULT 0,
    completion_tokens   INTEGER DEFAULT 0,
    latency_ms          INTEGER DEFAULT 0,
    escalated_from      TEXT,                             -- prior tier on retry, NULL pre-Step-3
    success             INTEGER NOT NULL DEFAULT 1,       -- 0/1 boolean
    task_kind           TEXT,                             -- 'llm_call' | 'agent_run' | seed task key
    error               TEXT,                             -- short error message if !success
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_swarm_traces_agent    ON swarm_traces(agent_name);
CREATE INDEX IF NOT EXISTS idx_swarm_traces_trace    ON swarm_traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_swarm_traces_kind     ON swarm_traces(task_kind);
CREATE INDEX IF NOT EXISTS idx_swarm_traces_created  ON swarm_traces(created_at);
