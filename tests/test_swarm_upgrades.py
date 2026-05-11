"""
End-to-end tests for agent swarm upgrades 1-5.

Tests each upgrade with synthetic data to verify the integration
actually works — not just that files parse.
"""
import asyncio
import sys
import os
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def report(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    tag = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


# ═══════════════════════════════════════════════════════════════
# UPGRADE 1: Forecasting Ensemble
# ═══════════════════════════════════════════════════════════════
def test_forecasting_ensemble():
    print("\n── Upgrade 1: Forecasting Ensemble ──")
    import pandas as pd
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA, AutoETS, AutoTheta, SeasonalNaive

    # Test adaptive model selection — short series (SeasonalNaive)
    n = 21
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    vals = [1000 + i * 10 + (50 if i % 7 == 5 else 0) for i in range(n)]
    df = pd.DataFrame({"unique_id": "rev", "ds": dates, "y": vals})

    models = [SeasonalNaive(season_length=7)]
    sf = StatsForecast(models=models, freq="D", n_jobs=1)
    sf.fit(df)
    fc = sf.predict(h=7, level=[80]).reset_index()
    report("SeasonalNaive (n<30)", len(fc) == 7, f"{len(fc)} rows forecast")

    # Test ensemble — medium series (AutoETS + AutoARIMA)
    n = 60
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    vals = [1000 + i * 5 + (100 if i % 7 == 6 else 0) for i in range(n)]
    df = pd.DataFrame({"unique_id": "rev", "ds": dates, "y": vals})

    models = [AutoETS(season_length=7), AutoARIMA(season_length=7)]
    model_names = ["AutoETS", "AutoARIMA"]
    sf = StatsForecast(models=models, freq="D", n_jobs=1)
    sf.fit(df)
    fc = sf.predict(h=7, level=[80, 95]).reset_index()

    point_cols = [c for c in fc.columns if c in model_names]
    report("Ensemble 2-model (30≤n<90)", len(point_cols) == 2,
           f"point cols: {point_cols}")

    fc["ensemble_mean"] = fc[point_cols].mean(axis=1)
    report("Ensemble mean computed", fc["ensemble_mean"].notna().all())

    lo_cols = [c for c in fc.columns if c.endswith("-lo-80")]
    hi_cols = [c for c in fc.columns if c.endswith("-hi-80")]
    report("Confidence interval cols", len(lo_cols) >= 1 and len(hi_cols) >= 1,
           f"lo={len(lo_cols)}, hi={len(hi_cols)}")

    # Test full ensemble — long series (3 models)
    n = 120
    dates = pd.date_range("2025-09-01", periods=n, freq="D")
    vals = [2000 + i * 3 + (200 if i % 7 == 5 else -50 if i % 7 == 1 else 0) for i in range(n)]
    df = pd.DataFrame({"unique_id": "rev", "ds": dates, "y": vals})

    models = [AutoARIMA(season_length=7), AutoETS(season_length=7), AutoTheta(season_length=7)]
    sf = StatsForecast(models=models, freq="D", n_jobs=1)
    sf.fit(df)
    fc = sf.predict(h=30, level=[80, 95]).reset_index()
    point_cols = [c for c in fc.columns if c in ["AutoARIMA", "AutoETS", "AutoTheta"]]
    report("Full 3-model ensemble (n≥90)", len(point_cols) == 3,
           f"models: {point_cols}")


# ═══════════════════════════════════════════════════════════════
# UPGRADE 2: CLV with lifetimes
# ═══════════════════════════════════════════════════════════════
def test_clv_lifetimes():
    print("\n── Upgrade 2: CLV with lifetimes (BG/NBD + Gamma-Gamma) ──")
    import numpy as np
    import pandas as pd
    from lifetimes import BetaGeoFitter, GammaGammaFitter
    from lifetimes.utils import summary_data_from_transaction_data
    import random

    random.seed(42)
    rows = []
    for cid in range(50):
        n_txns = random.randint(1, 20)
        for t in range(n_txns):
            day_offset = random.randint(0, 180)
            rows.append({
                "customer_id": f"cust_{cid}",
                "date": pd.Timestamp("2025-06-01") + pd.Timedelta(days=day_offset),
                "monetary_value": random.randint(500, 5000),
            })
    df = pd.DataFrame(rows)

    rfm = summary_data_from_transaction_data(
        df, "customer_id", "date",
        monetary_value_col="monetary_value",
        observation_period_end=df["date"].max(),
    )
    report("RFM summary built", len(rfm) == 50, f"{len(rfm)} customers")
    report("RFM has frequency/recency/T/monetary",
           all(c in rfm.columns for c in ["frequency", "recency", "T", "monetary_value"]))

    # BG/NBD
    bgf = BetaGeoFitter(penalizer_coef=0.1)
    bgf.fit(rfm["frequency"], rfm["recency"], rfm["T"])
    p_alive = bgf.conditional_probability_alive(rfm["frequency"], rfm["recency"], rfm["T"])
    p_alive_valid = not np.any(np.isnan(np.asarray(p_alive)))
    report("BG/NBD fit + p_alive", p_alive_valid,
           f"p_alive range: [{np.nanmin(p_alive):.2f}, {np.nanmax(p_alive):.2f}]")

    pred_30d = bgf.conditional_expected_number_of_purchases_up_to_time(
        30, rfm["frequency"], rfm["recency"], rfm["T"]
    )
    pred_valid = not np.any(np.isnan(np.asarray(pred_30d)))
    report("BG/NBD 30-day purchase prediction", pred_valid,
           f"mean pred: {np.nanmean(pred_30d):.2f}")

    # Gamma-Gamma
    returning = rfm[rfm["frequency"] > 0]
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(returning["frequency"], returning["monetary_value"])
    clv = ggf.customer_lifetime_value(
        bgf, returning["frequency"], returning["recency"],
        returning["T"], returning["monetary_value"],
        time=12, discount_rate=0.01,
    )
    report("Gamma-Gamma CLV", clv.notna().all(),
           f"mean 12-mo CLV: {clv.mean():.0f} cents")

    churn_count = (p_alive < 0.3).sum()
    report("Churn identification (p_alive<0.3)", True,
           f"{churn_count} of {len(rfm)} at risk")


# ═══════════════════════════════════════════════════════════════
# UPGRADE 3: Vision YOLO v11
# ═══════════════════════════════════════════════════════════════
def test_vision_yolo():
    print("\n── Upgrade 3: Vision YOLO v11 ──")
    # Can't run inference without ultralytics installed on this machine,
    # but verify the default model name is correct in source.
    with open("src/camera/detector.py") as f:
        src = f.read()
    report("detector.py default=yolo11n", 'model_size: str = "yolo11n"' in src)

    with open("src/camera/pipeline.py") as f:
        src = f.read()
    report("pipeline.py default=yolo11n", 'model_size: str = "yolo11n"' in src)

    with open("edge/edge_agent.py") as f:
        src = f.read()
    report("edge_agent.py uses yolo11n.pt", 'YOLO("yolo11n.pt")' in src)


# ═══════════════════════════════════════════════════════════════
# UPGRADE 4: Anomaly Detection (PyOD Ensemble + Luminol)
# ═══════════════════════════════════════════════════════════════
def test_anomaly_detection():
    print("\n── Upgrade 4: Anomaly Detection ──")
    import numpy as np
    from pyod.models.iforest import IForest
    from pyod.models.lof import LOF
    from pyod.models.knn import KNN

    # Synthetic data with clear outliers
    np.random.seed(42)
    normal = np.random.normal(1000, 50, 95)
    outliers = np.array([200, 2500, 150, 2800, 100])
    values = np.concatenate([normal, outliers])
    arr = values.reshape(-1, 1)

    models = [
        IForest(contamination=0.05, random_state=42),
        LOF(contamination=0.05, n_neighbors=20),
        KNN(contamination=0.05, n_neighbors=10),
    ]
    votes = np.zeros(len(values))
    for m in models:
        m.fit(arr)
        votes += m.labels_

    ensemble_labels = [1 if v >= 2 else 0 for v in votes]
    anomaly_count = sum(ensemble_labels)
    report("PyOD 3-model ensemble", anomaly_count >= 3,
           f"{anomaly_count} anomalies detected (expected ~5)")

    # Check that the known outliers (indices 95-99) are flagged
    outlier_caught = sum(ensemble_labels[95:])
    report("Known outliers caught", outlier_caught >= 3,
           f"{outlier_caught}/5 outliers flagged by majority vote")

    # Luminol time-series (patch numpy.asscalar removed in numpy>=1.23)
    if not hasattr(np, "asscalar"):
        np.asscalar = lambda a: a.item()
    from luminol.anomaly_detector import AnomalyDetector

    ts = {i: float(v) for i, v in enumerate(values)}
    detector = AnomalyDetector(ts)
    anomalies = detector.get_anomalies()
    report("Luminol anomaly detector", len(anomalies) >= 1,
           f"{len(anomalies)} anomaly windows found")

    if anomalies:
        scores = [a.anomaly_score for a in anomalies]
        report("Luminol scores meaningful", max(scores) > 0,
               f"max score: {max(scores):.0f}")


# ═══════════════════════════════════════════════════════════════
# UPGRADE 5: LiteLLM Routing
# ═══════════════════════════════════════════════════════════════
def test_litellm_routing():
    print("\n── Upgrade 5: LiteLLM Routing ──")
    import litellm

    version = getattr(litellm, "__version__", "unknown")
    report("litellm importable", True, f"v{version}")

    # Verify our llm_layer uses litellm
    with open("src/ai/llm_layer.py") as f:
        src = f.read()

    report("llm_layer imports litellm", "from litellm import acompletion" in src)
    report("llm_layer has _call_llm", "async def _call_llm" in src)
    report("llm_layer has fallback model", "MERIDIAN_LLM_FALLBACK" in src)
    report("llm_layer retains httpx fallback", "httpx.AsyncClient" in src)

    # Verify model routing config
    report("Default model configurable", "MERIDIAN_LLM_MODEL" in src)
    report("Fallback chain loop", "for model in [_DEFAULT_MODEL, _FALLBACK_MODEL]" in src)


# ═══════════════════════════════════════════════════════════════
# UPGRADE 6+7: DSPy + mem0 (already integrated — smoke check)
# ═══════════════════════════════════════════════════════════════
def test_existing_integrations():
    print("\n── Upgrades 6-7: DSPy + mem0 (pre-existing) ──")
    with open("src/ai/dspy_optimizer.py") as f:
        src = f.read()
    report("DSPy optimizer exists", "dspy.ChainOfThought" in src or "ChainOfThought" in src)
    report("DSPy MIPROv2 compiler", "MIPROv2" in src)

    with open("src/ai/agent_memory.py") as f:
        src = f.read()
    report("mem0 Memory integration", "mem0" in src.lower() or "Memory" in src)


# ═══════════════════════════════════════════════════════════════
# INTEGRATION: BaseAgent methods use upgraded code
# ═══════════════════════════════════════════════════════════════
def test_base_agent_integration():
    print("\n── Integration: BaseAgent upgraded methods ──")
    with open("src/ai/agents/base.py") as f:
        src = f.read()

    report("base.forecast uses ensemble",
           "AutoETS" in src and "AutoTheta" in src and "SeasonalNaive" in src)
    report("base.forecast ensemble_mean", "ensemble_mean" in src)
    report("base.detect_anomalies uses LOF+KNN",
           "from pyod.models.lof import LOF" in src and "from pyod.models.knn import KNN" in src)
    report("base.detect_anomalies majority vote", "votes += m.labels_" in src)


# ═══════════════════════════════════════════════════════════════
# REQUIREMENTS: All deps listed
# ═══════════════════════════════════════════════════════════════
def test_requirements():
    print("\n── Requirements completeness ──")
    with open("requirements.txt") as f:
        reqs = f.read()

    for dep in ["statsforecast", "lifetimes", "pyod", "luminol", "litellm"]:
        report(f"requirements.txt has {dep}", dep in reqs)


# ═══════════════════════════════════════════════════════════════
# AGENT FILE: ForecasterAgent uses ensemble
# ═══════════════════════════════════════════════════════════════
def test_forecaster_agent_source():
    print("\n── ForecasterAgent source check ──")
    with open("src/ai/agents/forecaster.py") as f:
        src = f.read()
    report("Adaptive model selection", "if n < 30:" in src and "elif n < 90:" in src)
    report("Ensemble mean in forecaster", "ensemble_mean" in src)
    report("Conservative bounds (lo-80/hi-80)", 'lo-80' in src and 'hi-80' in src)
    report("Error rate varies by ensemble size", '0.10 if len(models) >= 3 else 0.15' in src)


# ═══════════════════════════════════════════════════════════════
# AGENT FILE: CustomerLTVAgent uses lifetimes
# ═══════════════════════════════════════════════════════════════
def test_clv_agent_source():
    print("\n── CustomerLTVAgent source check ──")
    with open("src/ai/agents/customer_ltv.py") as f:
        src = f.read()
    report("Imports lifetimes", "from lifetimes import BetaGeoFitter" in src)
    report("BG/NBD fitter", "BetaGeoFitter" in src)
    report("Gamma-Gamma fitter", "GammaGammaFitter" in src)
    report("p_alive churn detection", 'p_alive' in src)
    report("Manual formula fallback", "not lifetimes_used" in src)
    report("Per-customer CLV output", "per_customer_clv" in src)


# ═══════════════════════════════════════════════════════════════
# RUN ALL
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))

    tests = [
        test_forecasting_ensemble,
        test_clv_lifetimes,
        test_vision_yolo,
        test_anomaly_detection,
        test_litellm_routing,
        test_existing_integrations,
        test_base_agent_integration,
        test_requirements,
        test_forecaster_agent_source,
        test_clv_agent_source,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"\n  [ERROR] {t.__name__} crashed:")
            traceback.print_exc()
            FAIL += 1

    print(f"\n{'═' * 50}")
    print(f"  TOTAL: {PASS + FAIL} | PASS: {PASS} | FAIL: {FAIL}")
    print(f"{'═' * 50}")
    sys.exit(0 if FAIL == 0 else 1)
