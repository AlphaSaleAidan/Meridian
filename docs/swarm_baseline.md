# Meridian Swarm Baseline — Phase 0

Date: 2026-06-02
Status: **Cannot produce a usable baseline from existing data.** Instrumentation must precede Phase 1 acceptance.

The masterplan requires 20–30 representative recent swarm tasks with latency, token cost, and a quality note. This document records what data exists, why it isn't enough, and the minimum instrumentation needed to produce a real baseline.

---

## 1. Data sources inventoried

| Source | Path / table | Rows | Date range | Verdict |
|--------|--------------|------|------------|---------|
| Deerflow runs | `services/deerflow/backend/.deer-flow/data/deerflow.db` → `runs` | 4 | 2026-05-14 only | Token counts all zero; no model name. **Not usable.** |
| Deerflow run events | same DB → `run_events` | 0 | — | Empty. |
| Agent reasoning chains | Supabase `agent_reasoning_chains` (`supabase/migrations/20260501_005_cline_agent.sql:9-27`) | 0 (schema only) | — | Schema exists; no data written yet. |
| Cline conversations | Supabase `cline_conversations` | 0 | — | Empty. |
| Cline messages | Supabase `cline_messages` | 0 | — | Empty. |
| Agent JSON logs | `logs/agents/*.log` via `src/ai/agent_logger.py` | 0 files | — | Logger code exists but no agent invokes it. |
| pm2 logs | `~/.pm2/logs/meridian-api-*.log` etc. | many | rolling | HTTP access logs only — no LLM-level fields. |
| Langfuse traces | `services/deerflow/.../tracing_config.py:26-47` | 0 | — | Configured but `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` not set in env. |
| Sentry / PostHog | `src/api/app.py:24-42` | not for swarm tasks | — | App-level monitoring, not agent-level. |

## 2. Why this fails the masterplan's Phase 0 requirement

Phase 0 asks for: "for 20–30 representative recent swarm tasks, record current latency, token cost, and a quality note."

- We have only **4 deerflow runs** total, all from one day, all with zero token counts.
- No agent has ever written to `logs/agents/`.
- Supabase audit tables are populated only when ClineAgent runs, which has not been triggered.
- LiteLLM router (`src/ai/llm_layer.py`) does not currently persist call metadata anywhere — `cache_responses=True` keeps recent calls in memory but nothing is written.

There is no honest way to claim a baseline from this data. Reporting one would mean fabrication.

## 3. Minimum instrumentation to produce a real baseline

The goal is a single structured table the eval harness can query. Two compatible options; option A is preferred.

### Option A — wire Langfuse (already partially configured)
1. Provision a Langfuse instance (self-hosted on this VPS or hosted).
2. Set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` in the meridian-api / deerflow environments.
3. Confirm `services/deerflow/.../tracing_config.py` picks them up.
4. Wrap `litellm.acompletion` / `router.acompletion` calls in `src/ai/llm_layer.py` with the Langfuse decorator so every LLM call records `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `agent_name` (passed as metadata).
5. Run 20–30 real swarm tasks via the meridian-api endpoint (mix of `analyze_merchant`, `enhance_insights`, `forecast_generator`, weekly report, ClineAgent).
6. Pull traces via Langfuse SDK into `docs/swarm_baseline.csv`.

### Option B — local SQLite trace (no external dep)
1. Add a `swarm_traces` table to the existing meridian Postgres (or a SQLite under `data/`).
2. Tee writes from `agent_logger.py` to the table. Add similar tee from `llm_layer.py` post-call.
3. Run the same 20–30 tasks. Pull with a SELECT.

Either option produces:

| field | type | source |
|-------|------|--------|
| `trace_id` | uuid | request-scoped |
| `agent_name` | text | call-site |
| `tier` | text | once tiers exist |
| `provider` | text | LiteLLM response metadata |
| `model` | text | LiteLLM response metadata |
| `prompt_tokens` | int | LiteLLM usage |
| `completion_tokens` | int | LiteLLM usage |
| `latency_ms` | int | wall clock around the await |
| `escalated_from` | text? | empty pre-Phase-1; populated after |
| `success` | bool | derived from exception path |
| `task_kind` | text | label per call site |
| `created_at` | timestamp | now() |

## 4. Eval task seed list (proposed)

Once instrumentation is live, run these 25 tasks to fill the baseline (covers all live LLM surfaces + a representative slice of statistical agents). Each task is replayable from the meridian-api endpoint or a CLI invocation; no real customer data needed — use the existing demo merchant.

1. `analyze_merchant(demo_org_id)` — full pipeline ×3 (warm/cold/cache).
2. `enhance_insights(...)` with 5, 25, 100 insights.
3. `forecast_generator(...)` 7d, 30d, 90d.
4. `weekly_report(...)` ×2.
5. `ClineAgent` repair flow ×2 (synthetic failure injection).
6. `CommercialDirector` short clip + still image ×2.
7. `pricing_power` agent against demo merchant ×1.
8. `churn_warning` against demo customer cohort ×1.
9. `seasonality` MSTL run ×1.
10. Cross-reference batch (10 agents) on demo store ×1.

Save outputs + traces to `tests/swarm_eval/baseline_2026-06.json`.

## 5. Verdict

**Phase 1 cannot pass acceptance until this baseline exists.** Recommend the user choose Option A (Langfuse) or Option B (SQLite) before any routing changes land. Estimated effort: <1 day either way, mostly env-var + decorator wiring.

The eval harness skeleton can be built in parallel with the baseline run — tests/swarm_eval/ already has a `test_swarm_upgrades.py` that we can extend.

## 6. Implementation status (2026-06-07)

Option B (SQLite tee) was implemented and **proven working**. Remaining blocker is gateway-side, not instrumentation-side.

**Done and verified:**
- `src/ai/trace_recorder.py` — non-blocking queue-based SQLite tee (stdlib only). Captures `tier / provider / model / prompt_tokens / completion_tokens / latency_ms / task_kind` per call. DB path via `MERIDIAN_SWARM_TRACE_DB` (default `data/swarm_traces.sqlite`, gitignored).
- In-memory smoke test recorded **383 real tokens** across calls — the recorder, schema, and queue flush all work end to end.
- `scripts/run_baseline_seed.py` drives the 25 seed tasks; `scripts/dump_baseline.py` materializes the trace DB to JSON.
- Router model-name fix (this branch): `tiered_router._provider_params()` now registers the gateway's real deployment names (`openai/meridian-local`, `openai/meridian-fast`) with an explicit `api_base` when `OPENAI_BASE_URL`/`OPENAI_API_BASE` is set — previously it registered `gpt-4o-mini`/`gpt-4o`, which the local LiteLLM gateway 400s as unknown models, so calls silently never landed. Gated/additive: no behaviour change when the base-url env is unset.

**Genuine blocker (gateway, not swarm):**
The full seed run still records **0 LLM-call tokens** because every JSON-mode call through the swarm's LiteLLM **Router** fails with:
`litellm.BadRequestError: DeepseekException - {"error":{"message":"This response_format type is unavailable now"...}}  (Model Group=meridian-t2)`
The gateway's `meridian-local` / `meridian-fast` deployments are DeepSeek-upstream and reject the Router's `response_format={"type":"json_object"}` requests. **Direct OpenAI-client JSON calls to the same models succeed** (verified: meridian-fast 1849ms 78/90 tok; meridian-local 41771ms 70/83 tok), which isolates the failure to the Router→gateway JSON path, not the recorder or the models themselves.

**To unblock (one of):**
1. Gateway serves a JSON-capable upstream for the `meridian-*` deployments (part of the Kimi K2.6 gateway migration, currently on the unmerged `kimi-k2.6-gateway` branch), or
2. `enhance_insights` / the affected agents drop `response_format=json_object` and parse free-form JSON, or
3. Run the baseline against a non-gateway provider key (DeepSeek/Groq/Cerebras direct) that honours `response_format`.

Once any of those lands, `run_baseline_seed.py` → `dump_baseline.py` produces `tests/swarm_eval/baseline_2026-06.json` with real token/latency numbers — no further instrumentation work needed.
