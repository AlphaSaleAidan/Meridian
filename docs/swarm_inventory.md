# Meridian Swarm Inventory — Phase 0

Date: 2026-06-02
Branch: `main` (no edits yet; pre-Phase-1)
Author: Phase 0 audit per `MERIDIAN_SWARM_UPGRADE_MASTERPLAN.md`

> **Phase 0 hard rule:** *"If Phase 0 finds the swarm framework or router differs materially from what's described here, STOP and report before editing."*
>
> **Verdict: STOP-condition triggered.** Stack diverges materially from the masterplan's claim. Details in §6.

---

## 1. Framework

**Masterplan claim:** kyegomez/swarms + VRSEN/agency-swarm.
**Reality:** Hand-rolled Python orchestrator on top of `asyncio`. No `swarms`, no `agency-swarm`, no DSPy modules in the agent path. `dspy` is referenced in `src/ai/dspy_optimizer.py` only and is commented out in `requirements-ml.txt`.

Evidence:
- `src/ai/agents/base.py:56-91` — custom `BaseAgent` class with a 5-phase Karpathy-style reasoning chain. No third-party base class.
- `src/ai/engine.py:482-605` — `run_agent_swarm()` instantiates agents manually, runs tiers 1–4 concurrently via `asyncio.gather(...)`, then tier 5 sequentially.
- `src/ai/agents/__init__.py` — 32 individual agent imports inheriting from local `BaseAgent`.
- `requirements.txt` and `requirements-ml.txt` — neither lists `swarms` nor `agency-swarm`.

What exists in the AI tree (all custom):
- `engine.py`, `llm_layer.py`, `swarm_trainer.py`, `commercial_director.py`, `cross_reference_orchestrator.py`, `dspy_optimizer.py`, `agent_logger.py`, `agent_memory.py`.

## 2. LLM Router

**Masterplan claim:** Free-tier router across SambaNova / Groq / Scaleway / Cerebras + DeepSeek V3.
**Reality:** Two routers, both built on LiteLLM. Scaleway is **not wired**.

### 2a. `src/ai/llm_layer.py` — primary router
Provider chain built dynamically based on env var presence (`llm_layer.py:83-149`):

| Order | Provider | Model id | Env var | Status |
|-------|----------|----------|---------|--------|
| 1 | DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` | ✅ wired |
| 2 | SambaNova | `sambanova/Meta-Llama-3.1-405B-Instruct` | `SAMBANOVA_API_KEY` | ✅ wired |
| 3 | Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` | ✅ wired |
| 4 | Cerebras | `cerebras/llama3.1-70b` | `CEREBRAS_API_KEY` | ✅ wired |
| 5 | OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` | ✅ wired (fallback) |
| 6 | Local Llama 3.1 8B | `llama-cpp-python` | — | ✅ wired (fallback) |
| — | Scaleway | n/a | n/a | ❌ **NOT wired** |

Router config: `routing_strategy="latency-based-routing"`, `num_retries=2`, `cache_responses=True` (`llm_layer.py:136`).

### 2b. `src/inference/router.py` — inference-tier router
- DeepSeek V3 primary if `DEEPSEEK_API_KEY` set, otherwise local Qwen 2.5 7B (`Qwen2.5-7B-Instruct-Q4_K_M.gguf`).
- No multi-provider failover here.

### 2c. What is missing vs the masterplan's intent
The infrastructure is there for failover, but there is **no tier concept** (T1/T2/T3) and **no confidence-based escalation**. LiteLLM's `latency-based-routing` picks the fastest available provider — not the cheapest-suitable one. Every agent today gets routed by latency, not by task complexity.

## 3. Memory

**Masterplan claim:** Mem0 + Letta as the role-aware memory layer.
**Reality:**
- **Mem0:** Optional. Imported with try/except in `src/ai/agent_memory.py:13-50`; if `MEM0_API_KEY` is unset or import fails, falls back to an in-memory dict. `mem0ai` is commented out in `requirements-ml.txt:14` (not even installed by default). Used only during `swarm_trainer._store_agent_memories()` (`swarm_trainer.py:300-323`), not on every agent run.
- **Letta:** **Not present.** Zero references anywhere in `src/`, `requirements*.txt`, or `services/`.

There is **no role-aware context routing** today — every agent receives the same `ctx` object from `engine.py` and reads what it needs.

## 4. Models referenced vs models actually called

| Model | Where called | Real usage |
|-------|--------------|------------|
| DeepSeek V3 (671B) | `src/inference/router.py:43`, `llm_layer.py` first slot | Primary reasoning model when `DEEPSEEK_API_KEY` set |
| Llama 3.1 405B (SambaNova) | `llm_layer.py:100-108` | Failover within router |
| Llama 3.3 70B (Groq) | `llm_layer.py:109-116` | Failover within router |
| Llama 3.1 70B (Cerebras) | `llm_layer.py:117-125` | Failover within router |
| GPT-4o-mini (OpenAI) | `llm_layer.py:126-133, 188-202` | Last-API fallback |
| Llama 3.1 8B (local llama-cpp) | `llm_layer.py:52-77` | Last-resort local fallback for `enhance_insights` |
| Qwen 2.5 7B (local GGUF) | `src/inference/local_llm.py:17`, `services` pm2 `qwen-server` | Local inference router target |

## 5. Agent invocation flow (`engine.py:167-385`)

1. `MeridianAI.analyze_merchant(org_id)` → `analyze(ctx)`.
2. Static analyzers run in parallel (`Phase 1`, `engine.py:219-235`).
3. Money-Left calculator (`Phase 2`).
4. Industry overlay (`Phase 2b`).
5. Insight generation (`Phase 3`).
6. `Phase 3b` — optional LLM enhancement via `llm_layer.enhance_insights(...)` (gated on `ENABLE_LLM_INSIGHTS=1`).
7. Forecast generation (`Phase 4`).
8. Weekly report (`Phase 5`).
9. **`Phase 5b` — Agent swarm**: `run_agent_swarm(ctx)` at `engine.py:317` runs 31 POS agents in tiers 1–4 (parallel) and tier 5 (sequential).
10. **`Phase 5c` — Cross-reference**: `CrossReferenceOrchestrator.analyze_batch(...)` runs the 10 camera×POS agents in parallel.
11. **`Phase 5d` — Self-training**: `SwarmTrainer.run_training_cycle(...)` (optional).
12. `Phase 6` — alert evaluation.

The swarm is therefore **mostly deterministic Python compute** with a small LLM surface (`enhance_insights`, report/forecast generators, CommercialDirector, ClineAgent). The masterplan's "every task routed to whatever free-tier model answers first" framing applies only to the LLM surface, which is a small minority of agents.

## 6. Drift verdict — STOP-condition reasoning

| Masterplan claim | Reality | Status |
|------------------|---------|--------|
| `kyegomez/swarms` | Custom asyncio orchestrator | **DRIFT** |
| `VRSEN/agency-swarm` | Same — custom | **DRIFT** |
| `Mem0 + Letta` | Mem0 optional & disabled by default; Letta absent | **DRIFT** |
| Free router across SambaNova/Groq/Scaleway/Cerebras | LiteLLM router across DeepSeek/SambaNova/Groq/Cerebras/OpenAI/local — **no Scaleway** | **PARTIAL** |
| DeepSeek V3 reasoning model | ✅ Wired and primary when key present | MATCH |
| Qwen 2.5 7B local batch | ✅ Wired via `qwen-server` pm2 process | MATCH |
| "Bloated multi-purpose agents sharing one context" | Mostly correct — agents share `ctx` and many are large. But **63 of ~73 agents are pure statistical/ML, not LLM** — so the "bigger model" lever is moot for them; the right lever for those is the ML-upgrades plan, not the routing plan. | NUANCE |

**Per the masterplan's own rule, Phase 0 must STOP and report at this boundary.** Continuing into Phase 1 without renegotiating the plan would mean editing under false assumptions about the framework.

See `agent_registry.md` for the per-agent breakdown that backs row 7 above.

## 7. Recommended adjusted plan (for user approval)

The intent of the masterplan still holds; the mechanics need to be re-mapped onto the real stack. Proposed:

1. **Tiered routing:** add a tier resolver in front of the existing LiteLLM router in `src/ai/llm_layer.py`. Each tier maps to a subset of the existing provider chain. Keep `latency-based-routing` within a tier; the tier itself is chosen by agent declaration + confidence escalation. **No new providers** unless we want Scaleway, which is currently absent.
2. **Scoped agent standard:** applies almost entirely to the ~10 LLM-calling agents (insight/forecast/report generators, CommercialDirector, ClineAgent, enhance_insights call sites). The 63 statistical agents already have one job; their upgrade lever is the ML plan, not the agent-standard.
3. **ML tool layer (Phase 3):** the masterplan's strongest fit. All five file references in `MERIDIAN_ML_MODEL_UPGRADES_PROMPT.md` are accurate (verified in §8). This phase can proceed independently after Phase 0 approval.
4. **Role-aware memory:** since Letta is absent and Mem0 is opt-in, propose using existing `agent_memory.py` + per-agent `memory_scope` keys before adding a new dependency.
5. **Baseline:** see `swarm_baseline.md` — no baseline data exists yet, instrumentation must precede Phase 1 acceptance gate.

## 8. ML-upgrades file-path verification

All five files referenced in `MERIDIAN_ML_MODEL_UPGRADES_PROMPT.md` exist and contain the claimed code:

| Doc reference | Actual content | Status |
|---------------|----------------|--------|
| `src/ai/economics/models.py:31-88` arc elasticity | `estimate_price_elasticity` arc formula | ✅ exact |
| `src/ai/agents/customer_ltv.py:95` BG/NBD | `BetaGeoFitter(penalizer_coef=penalizer)` at line 95 | ✅ exact |
| `src/ai/agents/customer_ltv.py:111` Gamma-Gamma | `GammaGammaFitter(penalizer_coef=0.01)` at line 111 | ✅ exact |
| `src/ai/agents/forecaster.py:59-192` statsforecast + manual MA/slope | Confirmed; manual block starts at line 132 | ✅ exact |
| `src/ai/predictive/churn_warning.py:60-65` manual sigmoid | `churn_prob = 1 / (1 + math.exp(-x))` at line 65 | ✅ exact |
| `src/ai/agents/base.py:300, 315` mlxtend apriori | `find_associations` at 300; apriori call at 313; rules at 316 | ✅ within 1-3 lines |

Wave 1 of the ML plan can therefore be executed against these files without further discovery work.
