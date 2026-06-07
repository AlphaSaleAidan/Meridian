"""Honest benchmark: Wave 2 backends vs their incumbents.

Run with an env that has the heavy deps installed (the offline eval venv,
NOT the Railway image):

    python scripts/benchmark_ml_waves2.py

Part A — Forecasting (Wave 2A): AutoGluon-TimeSeries vs the statsforecast
ensemble. Backtest on a held-out tail; report MAE and MASE (MASE < 1 beats
the seasonal-naive baseline). Lower is better.

Part B — Churn (Wave 2B): CoxPH survival ranking vs the incumbent sigmoid
``days_since_last / avg_interval`` heuristic. Report Harrell's concordance
index against the observed event/time (higher is better; 0.5 = chance).

No numbers are hard-coded — everything below is computed from synthetic
data generated in-process. The point is a like-for-like, reproducible
comparison, not a marketing figure.
"""
from __future__ import annotations

import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone

# Allow ``python scripts/benchmark_ml_waves2.py`` from the repo root: put
# the repo root (parent of scripts/) on sys.path so ``import src...`` works.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEED = 42


def _gen_revenue_series(n_days: int) -> list[dict]:
    rng = random.Random(SEED)
    start = datetime(2026, 1, 1)
    rows = []
    for i in range(n_days):
        trend = 50000 + 280 * i
        weekly = 9000 * math.sin(2 * math.pi * (i % 7) / 7)
        monthly = 4000 * math.sin(2 * math.pi * (i % 30) / 30)
        noise = rng.gauss(0, 3500)
        val = max(0, trend + weekly + monthly + noise)
        rows.append({"date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
                     "revenue_cents": int(val)})
    return rows


def _mae(actual, pred) -> float:
    return sum(abs(a - p) for a, p in zip(actual, pred)) / max(len(actual), 1)


def _seasonal_naive_mae(train_vals, season=7) -> float:
    # In-sample MAE of a seasonal-naive forecast = MASE denominator.
    errs = [abs(train_vals[i] - train_vals[i - season])
            for i in range(season, len(train_vals))]
    return sum(errs) / max(len(errs), 1)


def benchmark_forecast(n_days=120, horizon=28):
    print("\n=== Part A — Forecasting: AutoGluon vs statsforecast ===")
    series = _gen_revenue_series(n_days)
    train, test = series[:-horizon], series[-horizon:]
    actual = [r["revenue_cents"] for r in test]
    train_vals = [r["revenue_cents"] for r in train]
    snaive_mae = _seasonal_naive_mae(train_vals, 7)
    print(f"holdout={horizon}d  seasonal-naive(7) in-sample MAE={snaive_mae:,.0f}")

    # --- statsforecast ensemble (incumbent) ---
    sf_mae = sf_mase = None
    try:
        import pandas as pd
        from statsforecast import StatsForecast
        from statsforecast.models import AutoARIMA, AutoETS, AutoTheta
        df = pd.DataFrame(train).rename(columns={"date": "ds", "revenue_cents": "y"})
        df["ds"] = pd.to_datetime(df["ds"])
        df["unique_id"] = "rev"
        df = df[["unique_id", "ds", "y"]]
        sf = StatsForecast(
            models=[AutoARIMA(season_length=7), AutoETS(season_length=7), AutoTheta(season_length=7)],
            freq="D", n_jobs=1,
        )
        sf.fit(df)
        fc = sf.predict(h=horizon)
        cols = [c for c in fc.columns if c in ("AutoARIMA", "AutoETS", "AutoTheta")]
        pred = fc[cols].mean(axis=1).tolist()
        sf_mae = _mae(actual, pred)
        sf_mase = sf_mae / snaive_mae
        print(f"statsforecast  MAE={sf_mae:,.0f}  MASE={sf_mase:.3f}")
    except Exception as e:
        print(f"statsforecast  UNAVAILABLE: {e!r}")

    # --- AutoGluon (Wave 2A) ---
    ag_mae = ag_mase = None
    try:
        from src.ai.ml.autogluon_forecast import autogluon_forecast
        fc = autogluon_forecast(train, horizon)
        if fc:
            pred = [r["predicted"] for r in fc][:horizon]
            ag_mae = _mae(actual, pred)
            ag_mase = ag_mae / snaive_mae
            print(f"autogluon      MAE={ag_mae:,.0f}  MASE={ag_mase:.3f}")
        else:
            print("autogluon      returned None (unavailable or too short)")
    except Exception as e:
        print(f"autogluon      UNAVAILABLE: {e!r}")

    if sf_mase is not None and ag_mase is not None:
        delta = (sf_mase - ag_mase) / sf_mase * 100
        verdict = "AutoGluon better" if ag_mase < sf_mase else "statsforecast better"
        print(f"--> {verdict}: MASE {sf_mase:.3f} → {ag_mase:.3f} ({delta:+.1f}%)")


def _gen_churn_cohort(n=120):
    """Survival-style cohort: every customer is enrolled ENROLL days ago;
    a latent lifetime L (days) is drawn from an exponential whose hazard
    rises with avg_interval and a declining ticket trend. Customers with
    L < ENROLL churn during the window; the rest are right-censored. The
    profile fields (first/last visit, span) are derived faithfully from L
    so ``survival_churn``'s event/duration reconstruction recovers the
    latent design. days_since_last is therefore a *noisy* recency signal,
    which is all the incumbent sigmoid gets to see — so neither model has
    the full picture and the comparison is fair.
    """
    rng = random.Random(SEED)
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    ENROLL = 365
    trend_code = {"growing": 1, "stable": 0, "declining": -1}
    customers = {}
    for i in range(n):
        avg_interval = rng.choice([6, 8, 10, 14, 21, 28])
        trend = rng.choice(["growing", "stable", "declining"])
        # log-hazard rises with interval, falls with a growing trend.
        # Constant tuned so mid-interval customers straddle the ENROLL
        # window → a realistic mix of churned + right-censored.
        loghaz = 0.08 * avg_interval - 0.7 * trend_code[trend] - 6.5
        hazard = math.exp(loghaz)
        life = rng.expovariate(hazard)  # latent days alive from first visit
        visit_count = max(2, int(rng.gauss(10, 4)))
        ticket = int(max(500, rng.gauss(3500, 800)))
        first = now - timedelta(days=ENROLL)
        if life < ENROLL:
            churn_day = first + timedelta(days=life)
            last = churn_day - timedelta(days=avg_interval * rng.uniform(0.5, 1.5))
        else:
            last = now - timedelta(days=avg_interval * rng.uniform(0.0, 1.0))
        span = max(1, (last - first).days)
        customers[f"c{i}"] = {
            "visit_count": visit_count,
            "avg_ticket_cents": ticket,
            "avg_interval_days": avg_interval,
            "span_days": span,
            "first_visit": first,
            "last_visit": last,
            "ticket_trend": trend,
        }
    return customers, now


def benchmark_churn(n=200):
    print("\n=== Part B — Churn: CoxPH survival vs incumbent sigmoid ===")
    customers, now = _gen_churn_cohort(n)

    # Observed event/time (same definition both backends are scored on).
    events, times, incumbent_risk = [], [], []
    for p in customers.values():
        avg_interval = p["avg_interval_days"]
        days_since_last = (now - p["last_visit"]).days
        churned = days_since_last > avg_interval * 4
        duration = (p["span_days"] + avg_interval) if churned else (now - p["first_visit"]).days
        events.append(bool(churned))
        times.append(max(1.0, float(duration)))
        # incumbent sigmoid heuristic risk
        x = days_since_last / avg_interval - 2 if avg_interval else 0
        risk = 1 / (1 + math.exp(-x))
        if p["ticket_trend"] == "declining":
            risk = min(1.0, risk + 0.1)
        elif p["ticket_trend"] == "growing":
            risk = max(0.0, risk - 0.1)
        incumbent_risk.append(risk)

    n_events = sum(events)
    print(f"cohort={n}  events={n_events}  censored={n - n_events}")

    try:
        import numpy as np
        from sksurv.metrics import concordance_index_censored
        inc_c = concordance_index_censored(
            np.asarray(events, bool), np.asarray(times, float), np.asarray(incumbent_risk, float)
        )[0]
        print(f"incumbent sigmoid  concordance={inc_c:.4f}")
    except Exception as e:
        print(f"incumbent sigmoid  UNAVAILABLE: {e!r}")
        inc_c = None

    try:
        from src.ai.ml.survival_churn import survival_churn
        out = survival_churn(customers, now=now)
        if out and out["concordance_index"] is not None:
            sv_c = out["concordance_index"]
            print(f"survival {out['model']}  concordance={sv_c:.4f}")
            print(f"  hazard_ratios={out['hazard_ratios']}")
            if inc_c is not None:
                delta = (sv_c - inc_c) / inc_c * 100
                verdict = "survival better" if sv_c > inc_c else "incumbent better"
                print(f"--> {verdict}: concordance {inc_c:.4f} → {sv_c:.4f} ({delta:+.1f}%)")
        else:
            print("survival  returned None (unavailable or degenerate)")
    except Exception as e:
        print(f"survival  UNAVAILABLE: {e!r}")


if __name__ == "__main__":
    print("Wave 2 ML benchmark — synthetic, reproducible (seed=%d)" % SEED)
    benchmark_forecast()
    benchmark_churn()
    print("\nDone. Numbers above are computed live, not hard-coded.")
