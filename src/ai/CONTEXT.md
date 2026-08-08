# src/ai/ — AI Analysis Engine

Entry point: `engine.py` → `MeridianAI.analyze_merchant(org_id, days)`
LLM calls: `llm_layer.py` — tier-routed via LiteLLM across DeepSeek →
SambaNova → Groq → Cerebras → OpenAI → local Qwen/llama-cpp, NOT a plain
OpenAI wrapper (see `docs/swarm_inventory.md`). Its `enhance_insights` step
is off by default and currently broken against DeepSeek — `docs/known_issues.md` §1.

## Subdirectories
- `agents/` — 30+ agents (inherit `base.py:BaseAgent`), each has `analyze(data)` method
- `agents/cross_ref/` — 10 camera+POS cross-reference agents
- `analyzers/` — Core analysis (patterns, products, revenue, money_left)
- `predictive/` — ML models (churn, demand, pricing, scenarios, goals, root_cause)
- `generators/` — Output formatters (insights, forecasts, reports)
- `reasoning/` — Karpathy 5-phase reasoning loop
- `economics/` — Economic models (elasticity, marginal analysis, benchmarks)
- `industry_templates/` — Vertical-specific configs (restaurant, retail, salon, etc.)

## Key pattern
All agents return structured dicts with `insights`, `metrics`, `recommendations` keys.
The engine runs agents in dependency order (Level 0→6), aggregates results.
