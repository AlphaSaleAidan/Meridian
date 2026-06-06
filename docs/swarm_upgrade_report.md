# Meridian Swarm Upgrade — Phase 5 Report

Date: 2026-06-07
Branch: `swarm-upgrade`
Scope: closes Phases 3–5 of `MERIDIAN_SWARM_UPGRADE_MASTERPLAN.md`, building on
the Phase 0 reconciliation (`swarm_inventory.md`, `swarm_baseline.md`,
`agent_registry.md`).

> **Reconciled stack reminder.** This swarm is a hand-rolled Python `asyncio`
> orchestrator (`src/ai/engine.py` + `src/ai/agents/base.py`) on a LiteLLM
> latency router — *not* kyegomez/swarms. The Phase 0 STOP-condition (see
> `swarm_inventory.md` §6) renegotiated every later phase against that reality.
> All work here respects it: the tier resolver sits **on** the existing
> router rather than replacing it, and confidence escalation is bounded to a
> single step for cost.

---

## 1. What shipped

### Phase 3 — Tiered model routing + 1-step escalation (`f37fe50e`)

A three-tier model ladder layered onto the existing LiteLLM router instead of a
parallel router.

- `src/ai/routing/tiered_router.py` — tiers `lightweight` / `standard` /
  `heavy_reasoning` map to LiteLLM model-groups `meridian-t1` / `-t2` / `-t3`
  (legacy `meridian-llm` retained). Latency-based routing still picks the
  fastest provider *within* a tier group.
- `src/ai/llm_layer.py` — `_get_router()` now builds its `model_list` from
  `tier_model_list()`; `_call_api`/`_call_llm` resolve the caller's agent name
  → tier, dispatch to the tier's model-group, and record the tier on every
  trace. Low-confidence results escalate exactly one tier up
  (`is_low_confidence`, threshold 0.45) then fall back to local.
- `tests/swarm_eval/test_tier_resolver.py` — 11 tests, fake router captures the
  dispatched `model` kwarg; no `pytest-asyncio` dependency (`asyncio.run`).

### Phase 4 — Agent contract + drift gate (`b1bbff66`)

A machine-readable registry made the source of truth for routing tiers, with a
CI gate that fails when the code and the registry diverge.

- `agents/registry.yaml` — 48 rows (41 concrete `BaseAgent` subclasses + 7
  LLM-calling agents). Each row: `name`, `class`, `module`, `category`,
  `exec_tier`, `calls_llm`, `model_tier` (set iff `calls_llm`).
- `src/ai/routing/registry_loader.py` — parses the YAML and applies its tier
  assignments to the router (`load_registry_tiers`, lru-cached, fail-soft);
  the YAML, not the in-code seed map, is now authoritative.
- `scripts/validate_agents.py` — schema + class-resolvability + **drift**
  checks. Discovers concrete `BaseAgent` subclasses by import + recursive
  `__subclasses__()` walk and fails if any lacks a registry row. Current
  output: `agent registry OK — 48 agents (7 LLM-calling), no drift`.
- `tests/swarm_eval/test_agent_registry.py` — 5 tests (validator passes,
  ≥40 rows, `model_tier` validity, registry drives router tiers, voice bot
  never routes heavy — latency-critical).
- `tools/pre-commit-hook.sh` — runs the validator when registry / validator /
  agent / routing files are staged; blocks the commit on drift.

> **Design note — independent failure.** The voice-bot "never heavy" guarantee
> is enforced two independent ways: the registry row declares `standard`, and
> the test asserts it directly against `registry_tier_map()`. The latency path
> can't silently inherit a heavy tier from a future default change.

### Phase 5 — Consolidated eval harness (`6d624fd5`)

- `scripts/run_swarm_eval.py` — one entrypoint: registry validator →
  routing/registry unit suite → Wave-1 ML evals, with a pass/fail summary and
  a CI-gating exit code. `--fast` skips the slow model-training ml_eval section.
- `.gitignore` — ignores the `data/swarm_traces.sqlite` test artifact.

---

## 2. Test results (2026-06-07)

```
$ python scripts/run_swarm_eval.py --fast
agent registry OK — 48 agents (7 LLM-calling), no drift
16 passed in 8.07s
  PASS  agent_registry
  PASS  swarm_eval
  OVERALL: PASS
```

- **Registry validator:** clean — 48 agents, 7 LLM-calling, no drift.
- **Routing + registry unit suite:** 16/16 pass (11 tier-resolver + 5 registry).

### Wave-1 ML evals (`tests/ml_eval`, importorskip'd optional deps)

| Wave | Upgrade | Eval status |
|------|---------|-------------|
| 1A | DoubleML price elasticity | pass |
| 1B | pymc-marketing CLV | pass |
| 1C | FP-Growth basket | pass |
| 1D | XGBoost + calibration churn | **partial — see §3** |

---

## 3. Open: Wave 1D churn-eval expectation gap (needs Aidan's decision)

**The model is shipped and correct.** Production churn (`churn_warning.py`) uses
`XGBClassifier` + `CalibratedClassifierCV(method="sigmoid")` calibrating on
held-out CV folds — exactly the pattern the masterplan calls correct. The gap
is in the *eval's expectations*, not the model.

`test_churn_classifier.py` asserts four properties of calibrated-XGB vs the
incumbent `GradientBoostingClassifier`:

| Assertion | Result | Why |
|-----------|--------|-----|
| ECE strictly lower | **pass** | the actual point of the upgrade — calibration win |
| Brier strictly lower | fail | GBM 0.1533 vs XGB+cal 0.1538 |
| AUC not worse | fail | GBM 0.7288 vs XGB+cal 0.7234 |
| PR-AUC not worse | fail | GBM 0.5891 vs XGB+cal 0.5859 |

**Root cause (not a bug):** `CalibratedClassifierCV` is a monotonic transform of
the score, so it is **AUC/ranking-invariant** — it *cannot* improve
discrimination. On fair synthetic data, XGBoost with default hyperparameters is
a marginally weaker *ranker* than the tuned 200-estimator GBM baseline, so the
discrimination assertions fail while the calibration assertion (ECE) passes.

**What I did not do.** I tried a principled DGP change (more samples, label
noise) to give calibration something to fix; ECE began passing cleanly but
AUC/PR-AUC/Brier still failed for the structural reason above. Per the standing
guidance — *fix the test data, not the thresholds; calibration is the actual
point; do not change model code to chase the metric beyond the 1D
calibration-split fix* — I **reverted** the speculative change rather than force
it green by hobbling the GBM baseline or hyperparameter-tuning XGB. The honest
state is recorded here instead of hacked away.

**Decision needed:** the discrimination assertions (`AUC`/`PR-AUC`/`Brier` ≥/<
incumbent) encode an expectation that calibration improves ranking, which it
cannot. Options for Aidan: (a) relax those three to the calibration metrics that
actually measure the upgrade (ECE, and Brier only if XGB is tuned to match GBM's
ranking); (b) tune XGB hyperparameters so it matches/beats GBM as a ranker *and*
calibrates better; or (c) keep the incumbent GBM and apply calibration to it.
This is a product/eval-shape call, not an engineering blocker.

---

## 4. Still pending

- **Phase 2 — SQLite baseline** (`swarm_baseline.md`): blocked on DeepSeek
  JSON-mode availability + OpenAI quota; trace instrumentation is in place
  (Phase 3 records tier on every call), so a baseline can be captured once a
  working JSON-mode provider is reachable.
- **ML Waves 2+:** 2A AutoGluon forecaster, 2B survival churn
  (scikit-survival CoxPH/RSF), Wave 3 polish (MFLES, DynamicOptimizedTheta,
  CrostonClassic, MAD z-score, STL/MSTL consolidation, PermutationExplainer),
  Wave 4 scaffolds. All behind feature flags, benchmarked vs incumbent, SHAP
  preserved. Already-SOTA agents (#4 MSTL, #13 IsolationForest, #14 ECOD,
  #15 COPOD, #18 contribution margin, #20 HHI, #26 SHAP TreeExplainer) are
  out of scope — do not touch.

---

## 5. Review gate

Per the no-push-to-main rule, this branch stays unmerged pending Aidan's review.
Run `python scripts/run_swarm_eval.py` (full) or `--fast` (skip model training)
to reproduce the results above.
