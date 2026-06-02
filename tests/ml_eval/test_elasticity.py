"""Wave 1A — panel price elasticity (OLS + DoubleML) eval.

Per the approved Wave-1 eval shape: the DML estimate is *expected* to
diverge from OLS where price is endogenous — that is the entire point
of the upgrade. So we do NOT assert agreement with OLS. We assert:

  1. **Directional sanity (both estimators)** — on normal-goods synthetic
     data, both OLS and DML produce a negative elasticity. A positive
     elasticity here would mean the implementation is broken.

  2. **DML fold-stability** — per-fold DML estimates have
     ``std/mean < 0.5``. Wildly unstable folds mean the partial-residuals
     aren't reliable on the chosen sample size, which is a bigger problem
     than the choice of estimator.

  3. **DML beats OLS toward truth under endogeneity** — when a confounder
     biases price upward with demand, the DML estimate is closer to the
     known true elasticity than OLS. This is the headline value of the
     upgrade and the test that justifies acting on the DML coefficient
     for pricing decisions.

Both ``statsmodels`` and ``econml`` are heavy optional deps — gated
behind importorskip so the test skips cleanly today.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

import pytest

statsmodels = pytest.importorskip(
    "statsmodels",
    reason="statsmodels powers the OLS baseline. Install with "
           "`pip install statsmodels` to run this eval.",
)
econml = pytest.importorskip(
    "econml",
    reason="econml provides LinearDML for the causal elasticity. Install "
           "with `pip install econml` (pulls scikit-learn + LightGBM) "
           "to run this eval.",
)


TRUE_ELASTICITY = -1.5  # ground truth used to generate the synthetic data


def _synthetic_panel(
    n: int = 400,
    seed: int = 17,
    endogeneity_strength: float = 0.6,
) -> list[dict]:
    """Generate a panel where ``demand_shifter`` biases price upward and
    demand upward simultaneously — the classic OLS-confounding setup.

    Generative model (in logs):
        log(P) = 1.0 + endogeneity_strength * W + e_p
        log(Q) = 2.5 + TRUE_ELASTICITY * log(P) + 0.8 * W + e_q

    With this DGP, OLS of log(Q) on log(P) without W is biased *toward
    zero* (the positive W → demand path partially cancels the negative
    price → demand path). DML with W as a confounder recovers
    TRUE_ELASTICITY.
    """
    rng = random.Random(seed)
    rows: list[dict] = []
    for i in range(n):
        w = rng.gauss(0, 1)
        e_p = rng.gauss(0, 0.2)
        e_q = rng.gauss(0, 0.2)
        log_p = 1.0 + endogeneity_strength * w + e_p
        log_q = 2.5 + TRUE_ELASTICITY * log_p + 0.8 * w + e_q
        rows.append({
            "price": math.exp(log_p),
            "quantity": math.exp(log_q),
            "demand_shifter": w,
        })
    return rows


@pytest.fixture(scope="module")
def fit_result():
    """Fit once, reuse across the three checks. DML's K-fold refit is
    the expensive step — about 5–10 s on this VPS."""
    from src.ai.economics.models import EconomicModels

    obs = _synthetic_panel()
    return EconomicModels.estimate_price_elasticity_panel(
        obs,
        confounders=["demand_shifter"],
        dml_n_splits=5,
    )


def _ok(result: dict, key: str) -> None:
    """Helper to surface a useful failure when a backend is unexpectedly
    unavailable. importorskip should have caught this, but a partial
    install can still leave one estimator broken."""
    status = result["backend_status"][key]
    assert status == "ok", (
        f"{key} backend status = {status!r} (expected 'ok'). "
        f"importorskip may have admitted a partial install."
    )


def test_directional_sanity_both_estimators_negative(fit_result):
    """Both OLS and DML must produce a negative elasticity on the
    synthetic normal-goods panel. A non-negative value indicates the
    log-log transformation or the cross-fitting plumbing is broken."""
    _ok(fit_result, "ols")
    _ok(fit_result, "dml")
    print(f"\n  OLS  = {fit_result['ols_elasticity']}")
    print(f"  DML  = {fit_result['dml_elasticity']}")
    print(f"  true = {TRUE_ELASTICITY}")
    assert fit_result["ols_elasticity"] < 0, (
        f"OLS elasticity {fit_result['ols_elasticity']} is not negative"
    )
    assert fit_result["dml_elasticity"] < 0, (
        f"DML elasticity {fit_result['dml_elasticity']} is not negative"
    )


def test_dml_fold_stability(fit_result):
    """std/mean across CV folds < 0.5. Tighter would risk flakiness on
    small samples; looser would hide real instability that a downstream
    pricing decision shouldn't rely on."""
    _ok(fit_result, "dml")
    folds = fit_result["dml_fold_estimates"]
    print(f"\n  fold estimates = {folds}")
    print(f"  stability (std/|mean|) = {fit_result['dml_fold_stability']}")
    assert len(folds) >= 3, f"too few folds: {len(folds)}"
    assert fit_result["dml_fold_stability"] < 0.5, (
        f"DML fold-stability {fit_result['dml_fold_stability']} >= 0.5 — "
        f"per-fold estimates diverge too much to act on."
    )


def test_dml_closer_to_truth_than_ols(fit_result):
    """The headline upgrade signal: under the planted endogeneity, the
    DML estimate sits closer to ``TRUE_ELASTICITY`` than the naive OLS.

    We compare |β̂ − true| absolutely; the inequality is strict because a
    tie indicates the DGP didn't actually induce confounding on this
    sample, which means the test isn't measuring what it's supposed to.
    """
    _ok(fit_result, "ols")
    _ok(fit_result, "dml")
    ols_err = abs(fit_result["ols_elasticity"] - TRUE_ELASTICITY)
    dml_err = abs(fit_result["dml_elasticity"] - TRUE_ELASTICITY)
    print(f"\n  |OLS - true| = {ols_err:.3f}")
    print(f"  |DML - true| = {dml_err:.3f}")
    assert dml_err < ols_err, (
        f"DML error {dml_err:.3f} not smaller than OLS error {ols_err:.3f} "
        f"— either the planted endogeneity is too weak or the DML "
        f"implementation isn't partialling out the confounder."
    )
