"""Wave 1D — GBM → XGBoost + CalibratedClassifierCV churn classifier eval.

Per the approved Wave-1 eval shape: prediction parity is NOT the test —
the swap is meant to *improve* the model on quality + calibration. We
assert:

  1. **AUC ≥ incumbent** — XGBoost + isotonic calibration must not
     degrade the classifier's discriminative power vs sklearn's
     GradientBoostingClassifier on the same training set.

  2. **Average precision (PR-AUC) ≥ incumbent** — same property at
     the precision-recall frontier; matters for the imbalanced-churn
     class regime where AUC alone can mislead.

  3. **Brier score < incumbent** — the calibration-as-loss metric.
     Isotonic calibration's whole job is to lower this.

  4. **Expected Calibration Error (ECE, 10-bin) < incumbent** — the
     reliability-diagram summary statistic. Both Brier and ECE moving
     the same direction is the unambiguous calibration win.

Both the XGBoost dep and a recent scikit-learn (with
CalibratedClassifierCV) are heavy/optional; both are importorskip'd.
"""

from __future__ import annotations

import random

import pytest

np = pytest.importorskip("numpy")
sklearn = pytest.importorskip(
    "sklearn",
    reason="scikit-learn powers GradientBoostingClassifier + "
           "CalibratedClassifierCV. Install with `pip install scikit-learn`.",
)
xgboost = pytest.importorskip(
    "xgboost",
    reason="xgboost is the Wave 1D replacement classifier. Install "
           "with `pip install xgboost` to run this eval.",
)


N_FEATURES = 5
RNG_SEED = 23


def _synthetic_churn_dataset(
    n: int = 2000, seed: int = RNG_SEED
) -> tuple["np.ndarray", "np.ndarray", "np.ndarray", "np.ndarray"]:
    """Build a churn dataset with planted signal across the 5 features
    the production model consumes:
        days_since_last, avg_interval_days, visit_count,
        avg_ticket_cents, span_days

    Larger ``days_since_last / avg_interval_days`` and a declining
    ``avg_ticket_cents`` raise churn risk — the same shape the heuristic
    in ``churn_warning.py`` builds on top of.

    Returns
    -------
    (X_train, X_test, y_train, y_test)
    """
    rng = np.random.default_rng(seed)
    avg_interval = rng.uniform(7, 60, n)
    days_since_last = rng.uniform(0, 180, n)
    visit_count = rng.integers(1, 50, n)
    avg_ticket = rng.normal(3000, 700, n)
    span_days = rng.integers(30, 365, n)

    # True log-odds: dominantly driven by overdue ratio + declining ticket.
    z = (
        1.6 * (days_since_last / avg_interval - 1.5)
        - 0.6 * np.log1p(visit_count)
        - 0.0005 * (avg_ticket - 3000)
        - 0.002 * span_days
        + rng.normal(0, 0.4, n)
    )
    proba = 1.0 / (1.0 + np.exp(-z))
    y = (rng.uniform(0, 1, n) < proba).astype(int)
    X = np.column_stack([
        days_since_last, avg_interval, visit_count, avg_ticket, span_days,
    ])

    # 70/30 split.
    perm = rng.permutation(n)
    split = int(0.7 * n)
    train_idx, test_idx = perm[:split], perm[split:]
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def _ece(y_true: "np.ndarray", proba: "np.ndarray", n_bins: int = 10) -> float:
    """Expected Calibration Error — confidence/accuracy gap averaged
    across equal-width probability bins, weighted by bin support."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    inds = np.digitize(proba, bins) - 1
    inds = np.clip(inds, 0, n_bins - 1)
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        mask = inds == b
        if not mask.any():
            continue
        bin_conf = proba[mask].mean()
        bin_acc = y_true[mask].mean()
        ece += (mask.sum() / n) * abs(bin_conf - bin_acc)
    return float(ece)


@pytest.fixture(scope="module")
def fit_both():
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import GradientBoostingClassifier
    from xgboost import XGBClassifier

    X_train, X_test, y_train, y_test = _synthetic_churn_dataset()

    gbm = GradientBoostingClassifier(
        n_estimators=50, max_depth=3, random_state=RNG_SEED,
    )
    gbm.fit(X_train, y_train)
    gbm_proba = gbm.predict_proba(X_test)[:, 1]

    cal = CalibratedClassifierCV(
        XGBClassifier(
            n_estimators=50, max_depth=3, random_state=RNG_SEED,
            eval_metric="logloss", verbosity=0,
        ),
        method="isotonic",
        cv=3,
    )
    cal.fit(X_train, y_train)
    cal_proba = cal.predict_proba(X_test)[:, 1]

    return {
        "y_test": y_test,
        "gbm_proba": gbm_proba,
        "cal_proba": cal_proba,
    }


def test_auc_not_worse(fit_both):
    from sklearn.metrics import roc_auc_score

    y = fit_both["y_test"]
    auc_gbm = roc_auc_score(y, fit_both["gbm_proba"])
    auc_cal = roc_auc_score(y, fit_both["cal_proba"])
    print(f"\n  AUC  GBM={auc_gbm:.4f}  XGB+cal={auc_cal:.4f}")
    # Small floating-point tolerance — equal is fine; the swap's value
    # is calibration, AUC equality is the constraint.
    assert auc_cal + 1e-3 >= auc_gbm, (
        f"AUC regressed: GBM={auc_gbm:.4f} > XGB+cal={auc_cal:.4f}"
    )


def test_pr_auc_not_worse(fit_both):
    from sklearn.metrics import average_precision_score

    y = fit_both["y_test"]
    ap_gbm = average_precision_score(y, fit_both["gbm_proba"])
    ap_cal = average_precision_score(y, fit_both["cal_proba"])
    print(f"\n  AvgPrec  GBM={ap_gbm:.4f}  XGB+cal={ap_cal:.4f}")
    assert ap_cal + 1e-3 >= ap_gbm, (
        f"AP regressed: GBM={ap_gbm:.4f} > XGB+cal={ap_cal:.4f}"
    )


def test_brier_strictly_lower(fit_both):
    from sklearn.metrics import brier_score_loss

    y = fit_both["y_test"]
    brier_gbm = brier_score_loss(y, fit_both["gbm_proba"])
    brier_cal = brier_score_loss(y, fit_both["cal_proba"])
    print(f"\n  Brier  GBM={brier_gbm:.4f}  XGB+cal={brier_cal:.4f}")
    assert brier_cal < brier_gbm, (
        f"Brier did not improve: GBM={brier_gbm:.4f}, XGB+cal={brier_cal:.4f}"
    )


def test_ece_strictly_lower(fit_both):
    y = fit_both["y_test"]
    ece_gbm = _ece(y, fit_both["gbm_proba"])
    ece_cal = _ece(y, fit_both["cal_proba"])
    print(f"\n  ECE  GBM={ece_gbm:.4f}  XGB+cal={ece_cal:.4f}")
    assert ece_cal < ece_gbm, (
        f"ECE did not improve: GBM={ece_gbm:.4f}, XGB+cal={ece_cal:.4f}"
    )
