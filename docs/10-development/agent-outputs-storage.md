# agent_outputs Storage & Retrieval — Design (not yet implemented)

**Status:** scoping only. The `agent_outputs` table exists in Railway Postgres (`id UUID, org_id TEXT, outputs JSONB, generated_at TIMESTAMPTZ` + `idx_agent_outputs_org_time`), created 2026-06-12, 0 rows. Nothing writes to it yet.

## Goal

Persist every swarm run's agent outputs so they are (a) queryable per org/time for dashboards and cross-run comparison, and (b) semantically searchable so agents can retrieve "what did we conclude about X before" instead of recomputing.

## Original idea vs. recommendation

The original sketch was: translate outputs to a compact form → **translate to Chinese to reduce characters** → store in a quant system. Recommendation: **drop the Chinese-translation step.** Token-level compression via translation saves storage bytes but destroys exact-match queryability, complicates debugging, adds a lossy translation hop, and saves nothing where it matters (embeddings are fixed-size regardless of input language). Quantization should happen at the **vector** level, not the text level — that's where the 4–32x wins are, with measurable recall trade-offs.

## Recommended pipeline

```
swarm run completes (src/ai/engine.py)
  → 1. STRUCTURE: per-agent output → canonical JSON row in agent_outputs (org_id, agent, run_id, generated_at)
  → 2. DISTILL: one-paragraph natural-language summary per agent output (template-first; LLM only for free-text fields)
  → 3. EMBED: all-MiniLM-L6-v2, 384-dim (already used in src/inference/embeddings.py — reuse it)
  → 4. QUANTIZE + INDEX: Int8 quantization (~3.92x memory reduction, proven in the ruflo stack) + HNSW index
  → 5. RETRIEVE: agents query top-k similar prior conclusions, scoped by org_id, before analyze()
```

Storage split:
- **Postgres `agent_outputs`** = source of truth (full JSONB, no compression — Postgres TOAST already compresses JSONB; rows are small).
- **AgentDB (local, Contabo)** = quantized vector index for semantic retrieval. Rebuildable from Postgres at any time, so it is a cache, not a second source of truth.

## Why Int8 + HNSW (the "turbo quant" part)

- Int8 scalar quantization: 4x smaller vectors, ~1–2% recall loss at this scale — fine for "find related prior insights."
- HNSW: sub-ms top-k at 10⁵–10⁶ vectors. At Meridian's scale (48 agents × runs/day × orgs), brute force would honestly work for a year — HNSW is future-proofing, not a launch requirement.
- Binary quantization (32x) is NOT recommended at 384-dim/small-corpus — recall degrades hard below ~10⁵ vectors where reranking can't recover it.

## Integration points (when implemented)

- Write path: `src/ai/engine.py` after swarm completion (same place `dump_baseline.py` aggregates), Celery task in `src/workers/tasks.py` for embed+index so the analyze path never blocks.
- Read path: `BaseAgent.get_prior_insights(org_id, query, k=5)` on `src/ai/agents/base.py`, fail-soft (empty list on any retrieval error).
- Trace: record retrieval hits to `swarm_traces` so we can measure whether prior-insight injection actually improves verdicts before rolling it out widely.

## Open decisions for Aidan

1. Retention: keep all runs forever in Postgres, or roll up to weekly after 90 days (matches HOT/WARM/COLD tiers in CONTEXT.md)?
2. Should phone-agent and SMS conclusions land in the same store, or is this swarm-only?
3. Cross-org retrieval is OFF by design (org_id scope). Anonymous cross-org patterns would go through the existing benchmarking pipeline instead.
