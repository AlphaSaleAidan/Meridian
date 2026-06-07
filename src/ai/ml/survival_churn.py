"""Wave 2B — survival-analysis churn backend (opt-in).

The incumbent churn signals are *binary / point-in-time*: a sigmoid on
``days_since_last / avg_interval`` (``ChurnWarningAgent``) and BG/NBD
``p_alive`` (``CustomerLTVAgent``). Both answer "is this customer at
risk *right now*". Neither answers **"how long until they churn"** or
**"which behaviours drive the hazard"**, and neither handles
right-censoring correctly (active customers are not "non-churners" — we
just haven't observed their churn yet).

Survival analysis fixes both. We fit a Cox proportional-hazards model
(default) or a Random Survival Forest (``MERIDIAN_CHURN_SURVIVAL_MODEL=rsf``)
on per-customer behavioural covariates with proper event/censoring, then
expose:

  * per-customer **median expected days-to-churn** (from the survival
    function) and a relative **risk score**;
  * cohort-level **covariate hazard ratios** (CoxPH ``exp(coef)``) — a
    "what drives churn here" explanation that complements the existing
    SHAP layer rather than replacing it;
  * a **concordance index** (Harrell's C) so the eval can score the fit
    honestly against the incumbent's ranking.

Opt-in via ``MERIDIAN_CHURN_SURVIVAL=1`` (resolved in the caller).
``scikit-survival`` is NOT in the deployed Railway image; the import
guard and the blanket ``None`` returns keep production on the incumbent
path until an operator opts in.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("meridian.ai.ml.survival")

# Cox needs a few events to estimate coefficients without blowing up; RSF
# is more tolerant but still meaningless on a handful of rows.
MIN_CUSTOMERS = 15
MIN_EVENTS = 3

_TICKET_TREND_CODE = {"declining": -1, "stable": 0, "unknown": 0, "growing": 1}

# Covariates fed to the model. Deliberately EXCLUDES span_days and
# days_since_last: those define the duration/event and would leak the
# label into the features.
_FEATURES = ["avg_interval_days", "visit_count", "avg_ticket_cents", "ticket_trend_code"]


def _median_survival_days(surv_fn) -> float | None:
    """First time t at which S(t) <= 0.5, from a scikit-survival
    StepFunction. Returns ``None`` when the curve never crosses 0.5
    within the observed horizon (customer outlives the data)."""
    try:
        x, y = surv_fn.x, surv_fn.y
    except AttributeError:
        return None
    for t, s in zip(x, y):
        if s <= 0.5:
            return float(t)
    return None


def survival_churn(customers: dict, now: datetime | None = None) -> dict | None:
    """Fit a survival model on per-customer behaviour and return churn
    timing + hazard explanations.

    ``customers`` is the dict produced by
    ``ChurnWarningAgent._build_customer_profiles`` (values carry
    ``visit_count``, ``avg_interval_days``, ``avg_ticket_cents``,
    ``span_days``, ``first_visit``, ``last_visit``, ``ticket_trend``).

    Returns a dict with ``model``, ``concordance_index``,
    ``hazard_ratios`` (CoxPH only), and ``per_customer`` (cid →
    {risk_score, median_days_to_churn, event}); or ``None`` if
    scikit-survival is unavailable or the cohort is too small/degenerate.
    """
    if not customers or len(customers) < MIN_CUSTOMERS:
        return None
    try:
        import numpy as np
        from sksurv.metrics import concordance_index_censored
        from sksurv.util import Surv
    except Exception as exc:  # noqa: BLE001
        logger.debug("scikit-survival unavailable (%s) — falling back", exc)
        return None

    try:
        now = now or datetime.now(timezone.utc)
        cids: list[str] = []
        feats: list[list[float]] = []
        events: list[bool] = []
        durations: list[float] = []

        for cid, p in customers.items():
            last_visit = p.get("last_visit")
            first_visit = p.get("first_visit")
            avg_interval = float(p.get("avg_interval_days", 30) or 30)
            if last_visit is None or first_visit is None or avg_interval <= 0:
                continue
            try:
                days_since_last = (now - last_visit).days
            except (TypeError, ValueError):
                continue

            # Event = churned, using the SAME threshold as the incumbent
            # "churned" segment (days_since_last > avg_interval * 4).
            churned = days_since_last > avg_interval * 4
            if churned:
                # Effective churn time ≈ last active visit + one expected
                # interval they failed to honour.
                duration = max(1.0, float(p.get("span_days", 1)) + avg_interval)
            else:
                # Still active → right-censored at observed tenure.
                duration = max(1.0, float((now - first_visit).days))

            cids.append(cid)
            feats.append([
                avg_interval,
                float(p.get("visit_count", 0)),
                float(p.get("avg_ticket_cents", 0)),
                float(_TICKET_TREND_CODE.get(p.get("ticket_trend", "unknown"), 0)),
            ])
            events.append(bool(churned))
            durations.append(duration)

        if len(cids) < MIN_CUSTOMERS or sum(events) < MIN_EVENTS:
            return None

        X = np.asarray(feats, dtype=float)
        y = Surv.from_arrays(event=np.asarray(events, dtype=bool),
                             time=np.asarray(durations, dtype=float))

        backend = os.environ.get("MERIDIAN_CHURN_SURVIVAL_MODEL", "cox").lower()
        hazard_ratios: dict[str, float] = {}
        if backend == "rsf":
            from sksurv.ensemble import RandomSurvivalForest
            model = RandomSurvivalForest(
                n_estimators=100, min_samples_leaf=3, random_state=42, n_jobs=1,
            )
            model.fit(X, y)
            model_name = "RandomSurvivalForest"
        else:
            from sksurv.linear_model import CoxPHSurvivalAnalysis
            # alpha (ridge) keeps the fit stable on small, collinear cohorts.
            model = CoxPHSurvivalAnalysis(alpha=0.1)
            model.fit(X, y)
            model_name = "CoxPHSurvivalAnalysis"
            hazard_ratios = {
                f: round(float(np.exp(c)), 4)
                for f, c in zip(_FEATURES, model.coef_)
            }

        risk_scores = model.predict(X)
        try:
            cindex = float(
                concordance_index_censored(
                    np.asarray(events, dtype=bool),
                    np.asarray(durations, dtype=float),
                    risk_scores,
                )[0]
            )
        except Exception:  # noqa: BLE001 — degenerate cohort (all same risk)
            cindex = None

        # Survival functions → median days-to-churn per customer.
        try:
            surv_fns = model.predict_survival_function(X)
        except Exception:  # noqa: BLE001
            surv_fns = [None] * len(cids)

        per_customer: dict[str, dict] = {}
        for i, cid in enumerate(cids):
            median_days = _median_survival_days(surv_fns[i]) if surv_fns[i] is not None else None
            per_customer[cid] = {
                "risk_score": round(float(risk_scores[i]), 4),
                "median_days_to_churn": round(median_days, 1) if median_days is not None else None,
                "event": bool(events[i]),
            }

        return {
            "model": model_name,
            "concordance_index": round(cindex, 4) if cindex is not None else None,
            "n_customers": len(cids),
            "n_events": int(sum(events)),
            "hazard_ratios": hazard_ratios,
            "per_customer": per_customer,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("survival churn failed: %s — falling back", exc)
        return None
