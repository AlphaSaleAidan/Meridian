"""Wave 2B — scikit-survival churn backend eval.

Asserts the survival backend (1) returns the documented contract,
(2) ranks customers better than chance (concordance > 0.5) on data with
a planted hazard signal, and (3) is a no-op (returns ``None``) on cohorts
too small to fit — the safety property that keeps the incumbent path the
default.

scikit-survival is heavy/optional → importorskip so CI without the dep
skips rather than fails.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip(
    "sksurv",
    reason="scikit-survival powers the Wave 2B survival churn backend. "
           "Install with `pip install scikit-survival`.",
)

from src.ai.ml.survival_churn import survival_churn  # noqa: E402

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _profile(visit_count, avg_interval, avg_ticket, span_days, days_since_last, trend="stable"):
    last = NOW - timedelta(days=days_since_last)
    first = last - timedelta(days=span_days)
    return {
        "visit_count": visit_count,
        "avg_ticket_cents": avg_ticket,
        "avg_interval_days": avg_interval,
        "span_days": span_days,
        "first_visit": first,
        "last_visit": last,
        "ticket_trend": trend,
    }


def _planted_cohort(n=60):
    """Half loyal (frequent, recent, growing) → censored/active; half
    lapsing (infrequent, long gap, declining) → events. Interval is the
    dominant churn driver, so a fit should recover positive concordance."""
    customers = {}
    for i in range(n):
        if i % 2 == 0:
            # loyal: short interval, recent visit (not churned)
            customers[f"loyal_{i}"] = _profile(
                visit_count=12, avg_interval=7, avg_ticket=4000,
                span_days=180, days_since_last=5, trend="growing",
            )
        else:
            # lapsing: long interval, long gap (churned: gap > interval*4)
            customers[f"lapse_{i}"] = _profile(
                visit_count=4, avg_interval=20, avg_ticket=2500,
                span_days=90, days_since_last=120, trend="declining",
            )
    return customers


def test_contract_and_ranking():
    out = survival_churn(_planted_cohort(), now=NOW)
    assert out is not None, "expected a fit on a 60-customer cohort"
    assert out["model"] == "CoxPHSurvivalAnalysis"
    assert out["n_events"] >= 3
    # Concordance is None only on a degenerate (all-equal-risk) fit; here
    # there is a planted signal so it must beat chance.
    assert out["concordance_index"] is not None
    assert out["concordance_index"] > 0.5
    # Hazard ratios present for every covariate.
    assert set(out["hazard_ratios"]) == {
        "avg_interval_days", "visit_count", "avg_ticket_cents", "ticket_trend_code",
    }
    # Per-customer contract.
    sample = next(iter(out["per_customer"].values()))
    assert "risk_score" in sample and "event" in sample
    assert "median_days_to_churn" in sample


def test_rsf_backend(monkeypatch):
    monkeypatch.setenv("MERIDIAN_CHURN_SURVIVAL_MODEL", "rsf")
    out = survival_churn(_planted_cohort(), now=NOW)
    assert out is not None
    assert out["model"] == "RandomSurvivalForest"
    assert out["hazard_ratios"] == {}  # RSF has no linear coefficients


def test_too_small_cohort_is_noop():
    # Below MIN_CUSTOMERS → returns None so the incumbent path stays default.
    tiny = {f"c{i}": _profile(4, 20, 2500, 90, 120, "declining") for i in range(5)}
    assert survival_churn(tiny, now=NOW) is None
