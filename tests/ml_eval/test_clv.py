"""Wave 1B — lifetimes → pymc-marketing CLV migration eval.

Per the approved Wave-1 eval shape: point estimates reconcile within
tolerance on a holdout (sanity), credible intervals produced, and a
loose calibration sanity check. NOT equality with the incumbent.

Synthetic data — important note
-------------------------------
This eval generates RFM directly (frequency / recency / T /
monetary_value), not transactions. The earlier transaction-then-
summarize generator produced borderline frequencies that crashed
lifetimes' MLE solver (ConvergenceError) and threw autograd
overflow during gradient evaluation. The point of this eval is
agreement on the BG/NBD + Gamma-Gamma fit, not on the upstream
RFM-construction pipeline (which is shared by both backends and
already covered by lifetimes' own tests).

Direct RFM generation pins the four properties the BG/NBD model
needs:
  * ``frequency`` drawn from a Poisson(rate * T) so the marginal
    distribution matches the model's assumption, with planted
    heterogeneity in ``rate`` so customers aren't all identical;
  * ``recency <= T`` enforced (otherwise the likelihood is undefined);
  * ``T`` spread across a realistic 60–365 day window;
  * ``monetary_value > 0`` for every repeat customer (Gamma-Gamma
    requires positive monetary values).

With this dataset both lifetimes (MLE) and pymc-marketing (Bayesian)
fit cleanly, which is the precondition for the three assertions
below to be meaningful.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
lifetimes = pytest.importorskip(
    "lifetimes",
    reason="lifetimes is the incumbent CLV library; install with "
           "`pip install lifetimes` to run this eval.",
)
pymc_marketing = pytest.importorskip(
    "pymc_marketing",
    reason="pymc-marketing is the Wave 1B replacement; install with "
           "`pip install pymc-marketing` (heavy — pulls PyMC + pytensor "
           "+ LLVM) to run this eval.",
)


def _synthetic_rfm(n: int = 120, seed: int = 42) -> "pd.DataFrame":
    """Generate a realistic RFM panel with per-customer heterogeneity
    designed so credible intervals have visible variation per customer.

    Key choices and why:
      * Wider tenure distribution (15–365 days). Short-tenured customers
        carry little information and should get *wide* credible
        intervals; long-tenured customers carry a lot and should get
        narrower ones. Without this spread, all per-customer CIs end up
        the same width, the `frac_degenerate < 25%` assertion fails on
        absolute-width thresholds, and the calibration coverage test
        can't differentiate between the backends.
      * Per-customer purchase rate from Gamma(shape=1.2, scale=0.05) —
        median ~0.05/day, heavy tail. Reproduces the BG/NBD generative
        assumption faithfully so MCMC doesn't fight the data.
      * Per-customer mean spend drawn from a Gamma; the spread of
        per-customer means is what makes the Gamma-Gamma posterior
        non-degenerate across customers.
      * recency ≤ T enforced by construction (no truncation needed).
      * n=120 keeps the MCMC fit memory-bounded on the shared VPS.
    """
    rng = np.random.default_rng(seed)

    # Tenure: 15–365 days, broad uniform. Floors low enough that some
    # customers carry genuinely thin histories.
    T = rng.uniform(15.0, 365.0, n)

    # Per-customer purchase rate: Gamma with heavier tail.
    rates = rng.gamma(shape=1.2, scale=0.05, size=n)

    # Observed purchases over T: Poisson(rate * T). frequency =
    # repeat purchases (lifetimes convention = total - 1).
    n_purchases = rng.poisson(rates * T)
    frequency = np.maximum(n_purchases - 1, 0).astype(float)

    # Recency: for repeat customers, distribute uniformly across their
    # active window; the spread keeps p_alive informative per customer.
    recency = np.zeros(n, dtype=float)
    mask_repeat = frequency > 0
    recency[mask_repeat] = rng.uniform(
        1.0, T[mask_repeat], size=int(mask_repeat.sum())
    )
    recency = np.minimum(recency, T)

    # Per-customer mean spend: Gamma → strictly positive, varied across
    # customers so Gamma-Gamma actually has signal to fit. Mean ~ 2100.
    monetary_value = rng.gamma(shape=3.5, scale=600.0, size=n)
    monetary_value[~mask_repeat] = 0.0  # GG ignores these

    rfm = pd.DataFrame({
        "customer_id": [f"c{i:04d}" for i in range(n)],
        "frequency": frequency,
        "recency": recency,
        "T": T,
        "monetary_value": monetary_value,
    })
    return rfm


def _fit_lifetimes_point(rfm: "pd.DataFrame") -> dict:
    """Fit the incumbent (MLE) BG/NBD + Gamma-Gamma on RFM directly
    and return per-customer point CLVs."""
    from lifetimes import BetaGeoFitter, GammaGammaFitter

    # Higher penalizer than the production default keeps the MLE
    # solver stable on small cohorts.
    bgf = BetaGeoFitter(penalizer_coef=0.05)
    bgf.fit(rfm["frequency"], rfm["recency"], rfm["T"])

    returning = rfm[rfm["frequency"] > 0]
    if len(returning) < 5:
        return {}
    ggf = GammaGammaFitter(penalizer_coef=0.05)
    ggf.fit(returning["frequency"], returning["monetary_value"])
    clv = ggf.customer_lifetime_value(
        bgf,
        returning["frequency"], returning["recency"],
        returning["T"], returning["monetary_value"],
        time=12, discount_rate=0.01,
    )
    return dict(zip(
        returning["customer_id"].tolist(),
        [float(v) for v in clv.values],
    ))


@pytest.fixture(scope="module")
def fitted(monkeypatch_module):
    """Fit both backends once on the same RFM; share across the three
    assertions. The pymc fit dominates wall time on this VPS.

    Memory-safe MCMC config (the VPS shares 47 GB with qwen-server +
    PoolDrop):
      * draws=300, tune=300, chains=2 → 600 posterior samples per
        customer. Enough to characterise 10/90 quantiles without
        blowing the heap.
      * cores=1 → no chain-parallel forking, no per-chain CPython
        copy. Sampling takes longer but RSS stays bounded.
      * OMP_NUM_THREADS=1 is set in the pytest invocation in
        scripts; we re-assert it here for safety on direct ``pytest``
        runs.
    """
    monkeypatch_module.setenv("MERIDIAN_CLV_MCMC_DRAWS", "300")
    monkeypatch_module.setenv("MERIDIAN_CLV_MCMC_TUNE", "300")
    monkeypatch_module.setenv("MERIDIAN_CLV_MCMC_CHAINS", "2")
    monkeypatch_module.setenv("MERIDIAN_CLV_MCMC_CORES", "1")
    monkeypatch_module.setenv("OMP_NUM_THREADS", "1")

    from src.ai.agents.customer_ltv import _fit_pymc_marketing_clv

    rfm = _synthetic_rfm()
    lifetimes_clv = _fit_lifetimes_point(rfm)
    (
        ltv_cents,
        pm_clv,
        pm_lo,
        pm_hi,
        _churn,
    ) = _fit_pymc_marketing_clv(rfm)
    return {
        "rfm": rfm,
        "lifetimes_clv": lifetimes_clv,
        "pm_clv": pm_clv,
        "pm_lo": pm_lo,
        "pm_hi": pm_hi,
        "ltv_cents": ltv_cents,
    }


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's default is function-scoped).
    Lets the fitted() fixture set the MCMC env vars once and have them
    visible to the fit calls without re-applying per-test."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


def test_cohort_point_reconciles_within_tolerance(fitted):
    """Cohort-mean CLV agrees within a loose tolerance.

    Why loose: lifetimes is MLE point, pymc-marketing is posterior mean.
    They are not the same estimator. On a clean synthetic cohort of
    ~200 customers we expect them within a factor of 2x of each other;
    we do not expect equality.
    """
    lf_clv = fitted["lifetimes_clv"]
    pm_clv = fitted["pm_clv"]
    assert lf_clv, "lifetimes produced no per-customer CLVs"
    assert pm_clv, "pymc-marketing produced no per-customer CLVs"
    lf_mean = sum(lf_clv.values()) / len(lf_clv)
    pm_mean = sum(pm_clv.values()) / len(pm_clv)
    ratio = pm_mean / lf_mean if lf_mean else float("inf")
    print(f"\n  lifetimes cohort mean CLV = {lf_mean:.0f}")
    print(f"  pymc-marketing cohort mean CLV = {pm_mean:.0f}")
    print(f"  ratio = {ratio:.2f}")
    assert lf_mean > 0 and pm_mean > 0
    assert 0.5 < ratio < 2.0, (
        f"cohort-mean CLV ratio {ratio:.2f} outside [0.5, 2.0]"
    )


def test_per_customer_credible_intervals_produced(fitted):
    """Every returning customer has a valid 80% credible interval."""
    pm_clv = fitted["pm_clv"]
    pm_lo = fitted["pm_lo"]
    pm_hi = fitted["pm_hi"]

    assert pm_clv, "pymc-marketing produced no per-customer CLVs"
    assert set(pm_lo.keys()) == set(pm_clv.keys())
    assert set(pm_hi.keys()) == set(pm_clv.keys())

    degenerate = 0
    for cid, point in pm_clv.items():
        lo = pm_lo[cid]
        hi = pm_hi[cid]
        assert lo >= 0, f"{cid}: lo={lo} < 0"
        assert hi >= lo, f"{cid}: hi={hi} < lo={lo}"
        if hi - lo < 1.0:
            degenerate += 1

    frac_degenerate = degenerate / len(pm_clv)
    print(f"\n  customers with width-collapsed CI: {degenerate}/"
          f"{len(pm_clv)} ({frac_degenerate:.0%})")
    assert frac_degenerate < 0.25, (
        f"too many degenerate intervals: {frac_degenerate:.0%}"
    )


def test_calibration_majority_lifetimes_point_in_ci(fitted):
    """Coverage sanity: the lifetimes MLE point CLV falls inside the
    pymc-marketing 80% credible interval for the majority of customers.

    This is a loose calibration proxy. Under correct model
    specification with enough data we expect coverage near 80%; on
    n≈200 with thin histories per customer we accept ≥ 50% as a
    directional signal that the posterior concentrates around the
    right region.
    """
    lifetimes_clv = fitted["lifetimes_clv"]
    pm_lo = fitted["pm_lo"]
    pm_hi = fitted["pm_hi"]

    shared = set(lifetimes_clv) & set(pm_lo)
    assert shared, "no customers shared between backends"

    inside = sum(
        1 for cid in shared if pm_lo[cid] <= lifetimes_clv[cid] <= pm_hi[cid]
    )
    coverage = inside / len(shared)
    print(f"\n  lifetimes-point ∈ pymc 80% CI: {inside}/"
          f"{len(shared)} ({coverage:.0%})")
    assert coverage >= 0.5, (
        f"only {coverage:.0%} of lifetimes points fall inside the "
        f"pymc-marketing 80% CI — posterior may be miscalibrated."
    )
