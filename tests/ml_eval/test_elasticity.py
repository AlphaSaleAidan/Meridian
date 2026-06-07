"""Wave 1A — panel price elasticity (OLS + DoubleML) eval.

Per the approved Wave-1 eval shape: the DML estimate is *expected* to
diverge from OLS where price is endogenous — that is the entire point
of the upgrade. We do NOT assert agreement with OLS. We assert:

  1. **Directional sanity (both estimators)** — both the naive log-log
     OLS and DML produce a negative elasticity on normal-goods
     synthetic data. A positive elasticity here would mean the
     implementation is broken.

  2. **DML fold-stability** — per-fold DML estimates have
     ``std/|mean| < 0.5``. Wildly unstable folds mean the
     partial-residuals aren't reliable on the sample size, which is a
     bigger problem than the choice of estimator.

  3. **DML beats naive OLS toward truth under endogeneity** — when a
     confounder biases price upward with demand, the DML estimate
     (with the confounder partialled out via cross-fitted GBM
     nuisance models) is closer to the known true elasticity than the
     *naive* log-log OLS that omits the confounder. This is the
     headline value of the upgrade.

Why compare DML against naive OLS, not the production OLS-with-W
``estimate_price_elasticity_panel`` also reports? OLS-with-W is the
correctly-specified estimator on this DGP and is itself unbiased; on
a finite sample it's noise-competitive with DML. The interesting
contrast — the one that justifies adding DML to the codebase — is the
gap between *uncontrolled* OLS and DML. The production method
exposes both: calling it with ``confounders=[]`` runs naive OLS;
calling with ``confounders=[…]`` runs DML with the confounder. We
exercise both calls here, then compare naive_ols vs dml against
truth.

Both ``statsmodels`` and ``econml`` are heavy optional deps — gated
behind importorskip so the test skips cleanly when neither is
installed.
"""

from __future__ import annotations

import math
import random

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
    n: int = 4000,
    seed: int = 17,
    endogeneity_strength: float = 1.0,
) -> list[dict]:
    """Generate a panel with strong, planted price endogeneity.

    Generative model (in logs):
        W            ~ N(0, 1)                    (demand shifter)
        log(P)       = 1.0 + endogeneity_strength * W + e_p
        log(Q)       = 2.5 + TRUE_ELASTICITY * log(P) + 0.8 * W + e_q

    With ``endogeneity_strength = 1.0`` and ``n = 4000``, the naive
    OLS of log(Q) on log(P) alone has a closed-form asymptotic bias of
    roughly +0.8 * (Var(W) / (s² + Var(W))) ≈ +0.77, pulling the
    estimate from −1.5 toward roughly −0.7. DML with W as a
    confounder partials this out and recovers something near −1.5.
    The signal-to-noise ratio at n=4000 is strong enough that the
    "DML closer to truth than naive OLS" inequality is a real
    property, not coin-flippable noise.
    """
    rng = random.Random(seed)
    rows: list[dict] = []
    for _ in range(n):
        w = rng.gauss(0.0, 1.0)
        e_p = rng.gauss(0.0, 0.2)
        e_q = rng.gauss(0.0, 0.2)
        log_p = 1.0 + endogeneity_strength * w + e_p
        log_q = 2.5 + TRUE_ELASTICITY * log_p + 0.8 * w + e_q
        rows.append({
            "price": math.exp(log_p),
            "quantity": math.exp(log_q),
            "demand_shifter": w,
        })
    return rows


@pytest.fixture(scope="module")
def fit_result() -> dict:
    """Run the production method twice:
       * once without confounders → naive OLS (biased by endogeneity);
       * once with the confounder → DML + controlled OLS (both
         unbiased on this DGP).
    The fold-stability + closer-to-truth checks compare DML against
    the *naive* OLS, which is the apples-to-apples bias comparison.

    DML's K-fold refit is the expensive step (~30–60 s on this VPS);
    module scope keeps it to a single fit.
    """
    from src.ai.economics.models import EconomicModels

    obs = _synthetic_panel()
    naive = EconomicModels.estimate_price_elasticity_panel(
        obs, confounders=[], dml_n_splits=5,
    )
    full = EconomicModels.estimate_price_elasticity_panel(
        obs, confounders=["demand_shifter"], dml_n_splits=5,
    )
    return {
        "naive": naive,
        "full": full,
    }


def _require_ok(report: dict, key: str) -> None:
    """Surface a useful failure when a backend status isn't 'ok'."""
    status = report["backend_status"][key]
    assert status == "ok", (
        f"{key} backend status = {status!r} (expected 'ok'). "
        f"importorskip may have admitted a partial install."
    )


def test_directional_sanity_both_estimators_negative(fit_result):
    """Both naive OLS and DML must produce a negative elasticity on
    the synthetic normal-goods panel. Non-negative ⇒ implementation
    or log-log plumbing is broken."""
    naive = fit_result["naive"]
    full = fit_result["full"]
    _require_ok(naive, "ols")
    _require_ok(full, "dml")
    print(
        f"\n  naive OLS   = {naive['ols_elasticity']}"
        f"\n  controlled  = {full['ols_elasticity']}"
        f"\n  DML         = {full['dml_elasticity']}"
        f"\n  true        = {TRUE_ELASTICITY}"
    )
    assert naive["ols_elasticity"] < 0, (
        f"naive OLS elasticity {naive['ols_elasticity']} is not negative"
    )
    assert full["dml_elasticity"] < 0, (
        f"DML elasticity {full['dml_elasticity']} is not negative"
    )


def test_dml_fold_stability(fit_result):
    """``std/|mean| < 0.5`` across CV folds. Tighter risks flakiness
    on n=4000; looser hides instability that pricing decisions
    shouldn't rely on."""
    full = fit_result["full"]
    _require_ok(full, "dml")
    folds = full["dml_fold_estimates"]
    print(f"\n  fold estimates  = {folds}")
    print(f"  stability ratio = {full['dml_fold_stability']}")
    assert len(folds) >= 3, f"too few folds: {len(folds)}"
    assert full["dml_fold_stability"] < 0.5, (
        f"DML fold-stability {full['dml_fold_stability']} >= 0.5 — "
        f"per-fold estimates diverge too much to act on."
    )


def test_dml_closer_to_truth_than_naive_ols(fit_result):
    """Headline upgrade signal: under planted endogeneity, the DML
    estimate is closer to ``TRUE_ELASTICITY`` than a naive log-log OLS
    that omits the confounder. The inequality is strict — a tie means
    the DGP didn't actually induce confounding on this sample, which
    in turn means the test isn't measuring what it's supposed to.
    """
    naive = fit_result["naive"]
    full = fit_result["full"]
    _require_ok(naive, "ols")
    _require_ok(full, "dml")

    naive_err = abs(naive["ols_elasticity"] - TRUE_ELASTICITY)
    dml_err = abs(full["dml_elasticity"] - TRUE_ELASTICITY)
    print(f"\n  |naive OLS − true| = {naive_err:.3f}")
    print(f"  |DML − true|        = {dml_err:.3f}")
    assert dml_err < naive_err, (
        f"DML error {dml_err:.3f} not smaller than naive OLS error "
        f"{naive_err:.3f} — either the planted endogeneity is too "
        f"weak or DML isn't partialling out the confounder."
    )
