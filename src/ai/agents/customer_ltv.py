import os

from .base import BaseAgent

try:
    from lifetimes import BetaGeoFitter, GammaGammaFitter
    from lifetimes.utils import summary_data_from_transaction_data
    HAS_LIFETIMES = True
except ImportError:
    HAS_LIFETIMES = False

# pymc-marketing is the maintained Bayesian successor to ``lifetimes`` (which
# is no longer being updated). It produces per-customer credible intervals
# on top of the same BG/NBD + Gamma-Gamma point estimate, which is the
# headline upgrade. Gated by MERIDIAN_CLV_BACKEND so we can keep the
# incumbent reachable for one reporting cycle after cutover.
try:
    from pymc_marketing.clv import (  # type: ignore[import-not-found]
        BetaGeoModel,
        GammaGammaModel,
    )
    HAS_PYMC_MARKETING = True
except Exception:  # noqa: BLE001 — also catches pytensor/llvmlite init errors
    HAS_PYMC_MARKETING = False


def _select_clv_backend() -> str:
    """Resolve the active CLV backend.

    Returns ``"pymc_marketing"`` only when the operator has explicitly opted
    in AND the dependency is importable; otherwise falls back to
    ``"lifetimes"``. Anything other than these two values is treated as
    ``"lifetimes"`` (the incumbent) so a typo never silently disables CLV.
    """
    backend = os.environ.get("MERIDIAN_CLV_BACKEND", "lifetimes").lower()
    if backend == "pymc_marketing" and HAS_PYMC_MARKETING:
        return "pymc_marketing"
    return "lifetimes"


def _fit_pymc_marketing_clv(rfm) -> tuple:
    """Fit BG/NBD + Gamma-Gamma via pymc-marketing and extract per-customer
    posterior CLV + an 80% credible interval.

    Inputs
    ------
    rfm : pandas.DataFrame
        Columns: ``customer_id``, ``frequency``, ``recency``, ``T``,
        ``monetary_value``. Produced by ``summary_data_from_transaction_data``
        (lifetimes helper) and ``.reset_index()``-ed so ``customer_id`` is
        a real column, matching what pymc-marketing expects.

    Returns
    -------
    (ltv_cents, per_customer_clv, per_customer_clv_lo, per_customer_clv_hi,
     churn_risk)
        ``ltv_cents``                 — int, cohort mean CLV (cents)
        ``per_customer_clv``          — dict customer_id → posterior mean CLV
        ``per_customer_clv_lo``       — dict customer_id → 10th percentile
        ``per_customer_clv_hi``       — dict customer_id → 90th percentile
        ``churn_risk``                — list[str] customer_ids with
                                         posterior-mean p_alive < 0.3

    Notes
    -----
    Sampler parameters (draws/tune/chains) are intentionally small —
    pymc-marketing CLV is in the CPU-only batch path on this VPS, and
    the masterplan explicitly accepts coarse posteriors here over
    real-time latency. The tighter parameters live behind
    MERIDIAN_CLV_MCMC_DRAWS / _TUNE / _CHAINS env vars for tuning.

    Requires pymc-marketing >= 0.11. The eval at
    tests/ml_eval/test_clv.py is the authoritative API contract; if
    pymc-marketing's public surface drifts, that test fails first.
    """
    draws = int(os.environ.get("MERIDIAN_CLV_MCMC_DRAWS", "500"))
    tune = int(os.environ.get("MERIDIAN_CLV_MCMC_TUNE", "500"))
    chains = int(os.environ.get("MERIDIAN_CLV_MCMC_CHAINS", "2"))
    # ``cores`` controls how many chains PyMC samples in parallel. Default
    # is ``chains`` (matches PyMC's default), but on a memory-constrained
    # host (this VPS shares 47GB with qwen-server + PoolDrop) the eval can
    # cap at MERIDIAN_CLV_MCMC_CORES=1 to keep total fit RSS bounded.
    cores = int(os.environ.get("MERIDIAN_CLV_MCMC_CORES", "0")) or chains

    bg_data = rfm[["customer_id", "frequency", "recency", "T"]].copy()
    bg_model = BetaGeoModel(data=bg_data)
    bg_model.build_model()
    bg_model.fit(
        progressbar=False, draws=draws, tune=tune, chains=chains, cores=cores,
    )

    # pymc-marketing's posterior helpers take the input DataFrame
    # directly (positional-or-keyword ``data``), NOT per-column kwargs.
    # Passing the original frame keeps customer order aligned with the
    # downstream dict construction.
    p_alive_post = bg_model.expected_probability_alive(data=bg_data)
    p_alive_mean = p_alive_post.mean(dim=("chain", "draw"))
    churn_risk = [
        cid for cid, p in zip(rfm["customer_id"].tolist(),
                               [float(x) for x in p_alive_mean.values])
        if p < 0.3
    ]

    returning_mask = rfm["frequency"] > 0
    returning = rfm.loc[returning_mask].copy()
    if len(returning) < 5:
        return 0, {}, {}, {}, churn_risk

    gg_data = returning[["customer_id", "frequency", "monetary_value"]]
    gg_model = GammaGammaModel(data=gg_data)
    gg_model.build_model()
    gg_model.fit(
        progressbar=False, draws=draws, tune=tune, chains=chains, cores=cores,
    )

    # expected_customer_lifetime_value expects ``data`` to carry every
    # column either model touches (customer_id, frequency, recency, T,
    # monetary_value). ``future_t`` replaces lifetimes' ``time`` kwarg.
    clv_input = returning[[
        "customer_id", "frequency", "recency", "T", "monetary_value",
    ]]
    clv_post = gg_model.expected_customer_lifetime_value(
        transaction_model=bg_model,
        data=clv_input,
        future_t=12,
        discount_rate=0.01,
    )
    clv_mean = clv_post.mean(dim=("chain", "draw"))
    clv_lo = clv_post.quantile(0.1, dim=("chain", "draw"))
    clv_hi = clv_post.quantile(0.9, dim=("chain", "draw"))

    cids = returning["customer_id"].tolist()
    per_customer_clv = {
        cid: float(v) for cid, v in zip(cids, [float(x) for x in clv_mean.values])
    }
    per_customer_clv_lo = {
        cid: float(v) for cid, v in zip(cids, [float(x) for x in clv_lo.values])
    }
    per_customer_clv_hi = {
        cid: float(v) for cid, v in zip(cids, [float(x) for x in clv_hi.values])
    }
    ltv_cents = int(sum(per_customer_clv.values()) / max(len(per_customer_clv), 1))
    return (
        ltv_cents,
        per_customer_clv,
        per_customer_clv_lo,
        per_customer_clv_hi,
        churn_risk,
    )


class CustomerLTVAgent(BaseAgent):
    name = "customer_ltv"
    description = "Customer lifetime value prediction and churn risk"
    tier = 5

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        agent_outputs = getattr(self.ctx, "agent_outputs", {})
        txns = getattr(self.ctx, "transactions", []) or []
        daily = getattr(self.ctx, "daily_revenue", []) or []

        if not txns and not daily:
            return self._insufficient_data("Transaction data required for LTV estimation")

        # Path selection
        has_customer_ids = any(t.get("customer_id") for t in txns[:50])
        has_card_fingerprint = any(t.get("card_fingerprint") or t.get("card_last4") for t in txns[:50])

        if has_customer_ids:
            path = "full"
            confidence = min(0.85, avail.quality_score)
        elif has_card_fingerprint:
            path = "partial"
            confidence = min(0.6, avail.quality_score)
        else:
            path = "minimal"
            confidence = min(0.35, avail.quality_score)

        insights = []
        recommendations = []

        # Get basket data from agent outputs
        basket_output = agent_outputs.get("basket_analysis", {})
        avg_basket = basket_output.get("data", {}).get("avg_basket_size_cents", 0)
        if not avg_basket and txns:
            avg_basket = sum(t.get("total_cents", 0) for t in txns) // max(len(txns), 1)

        days = avail.date_range_days or 30

        if path == "full":
            from collections import defaultdict
            customer_txns = defaultdict(list)
            for t in txns:
                cid = t.get("customer_id", "")
                if cid:
                    customer_txns[cid].append(t)

            total_customers = len(customer_txns)
            visit_counts = {cid: len(ts) for cid, ts in customer_txns.items()}
            repeat_customers = sum(1 for c in visit_counts.values() if c > 1)
            retention_rate = repeat_customers / max(total_customers, 1)
            avg_visit_freq = sum(visit_counts.values()) / max(total_customers, 1) / max(days, 1) * 30

            # --- BG/NBD + Gamma-Gamma probabilistic CLV ---
            # Two backends: lifetimes (MLE point estimates, incumbent) and
            # pymc-marketing (Bayesian posterior with credible intervals).
            # Selection via MERIDIAN_CLV_BACKEND; see _select_clv_backend.
            model_used = None  # one of "lifetimes" / "pymc_marketing" / None
            ltv_cents = 0
            churn_risk = []
            per_customer_clv: dict = {}
            per_customer_clv_lo: dict = {}
            per_customer_clv_hi: dict = {}
            backend_choice = _select_clv_backend()

            should_try_clv = total_customers >= 10 and repeat_customers >= 5
            if should_try_clv:
                try:
                    import pandas as pd
                    rows = []
                    for t in txns:
                        cid = t.get("customer_id")
                        if not cid:
                            continue
                        rows.append({
                            "customer_id": cid,
                            "date": t.get("created_at", t.get("date", "")),
                            "monetary_value": t.get("total_cents", 0),
                        })
                    df = pd.DataFrame(rows)
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["date"])

                    if len(df) >= 20:
                        if backend_choice == "pymc_marketing" and HAS_LIFETIMES:
                            # Reuse lifetimes' RFM summary helper — pymc-
                            # marketing's input format is the same shape, and
                            # this avoids re-implementing the recency/T math.
                            rfm = summary_data_from_transaction_data(
                                df, "customer_id", "date",
                                monetary_value_col="monetary_value",
                                observation_period_end=df["date"].max(),
                            ).reset_index()
                            (
                                ltv_cents,
                                per_customer_clv,
                                per_customer_clv_lo,
                                per_customer_clv_hi,
                                churn_risk,
                            ) = _fit_pymc_marketing_clv(rfm)
                            model_used = "pymc_marketing"
                            confidence = min(confidence + 0.1, 0.9)
                        elif HAS_LIFETIMES:
                            rfm = summary_data_from_transaction_data(
                                df, "customer_id", "date",
                                monetary_value_col="monetary_value",
                                observation_period_end=df["date"].max(),
                            )

                            penalizer = 0.1 if len(rfm) < 100 else 0.01
                            bgf = BetaGeoFitter(penalizer_coef=penalizer)
                            bgf.fit(rfm["frequency"], rfm["recency"], rfm["T"])

                            rfm["p_alive"] = bgf.conditional_probability_alive(
                                rfm["frequency"], rfm["recency"], rfm["T"]
                            )
                            rfm["pred_purchases_30d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
                                30, rfm["frequency"], rfm["recency"], rfm["T"]
                            )

                            # Churn: p_alive < 0.3
                            churn_risk = rfm[rfm["p_alive"] < 0.3].index.tolist()

                            # Gamma-Gamma for monetary value — needs repeat buyers
                            returning = rfm[rfm["frequency"] > 0]
                            if len(returning) >= 5:
                                ggf = GammaGammaFitter(penalizer_coef=0.01)
                                ggf.fit(returning["frequency"], returning["monetary_value"])
                                clv = ggf.customer_lifetime_value(
                                    bgf, returning["frequency"], returning["recency"],
                                    returning["T"], returning["monetary_value"],
                                    time=12, discount_rate=0.01,
                                )
                                per_customer_clv = clv.to_dict()
                                ltv_cents = int(clv.mean())
                                model_used = "lifetimes"
                                confidence = min(confidence + 0.1, 0.9)
                except Exception as e:
                    import logging
                    logging.getLogger("meridian.ai.agents").warning(
                        f"CLV ({backend_choice}) failed, falling back to manual: {e}"
                    )

            # Back-compat alias for the data block below + downstream callers
            # that still check for "lifetimes_used". When MERIDIAN_CLV_BACKEND
            # defaults to pymc_marketing in a future cutover this and the
            # ``model`` field can be unified.
            lifetimes_used = model_used is not None

            if not lifetimes_used:
                # A partially-failed model fit above may have populated
                # churn_risk — reset so heuristic IDs don't mix with
                # model-derived ones.
                churn_risk = []
                if retention_rate > 0 and retention_rate < 1:
                    monthly_value = avg_basket * avg_visit_freq
                    annual_value = monthly_value * 12
                    ltv_cents = int(annual_value * retention_rate / (1 - retention_rate))
                else:
                    ltv_cents = int(avg_basket * avg_visit_freq * 12)
                for cid, ts in customer_txns.items():
                    if len(ts) < 4:
                        continue
                    mid = len(ts) // 2
                    first_half_freq = mid
                    second_half_freq = len(ts) - mid
                    if first_half_freq > 0 and second_half_freq / first_half_freq < 0.7:
                        churn_risk.append(cid)

            churn_pct = len(churn_risk) / max(total_customers, 1) * 100

        elif path == "partial":
            # Estimate from card fingerprints
            from collections import defaultdict
            card_groups = defaultdict(int)
            for t in txns:
                fp = t.get("card_fingerprint") or t.get("card_last4") or "unknown"
                card_groups[fp] += 1

            known_cards = {k: v for k, v in card_groups.items() if k != "unknown"}
            total_customers = max(len(known_cards), len(txns) // 3)
            repeat_customers = sum(1 for v in known_cards.values() if v > 1)
            retention_rate = repeat_customers / max(len(known_cards), 1) if known_cards else 0.4
            avg_visit_freq = len(txns) / max(total_customers, 1) / max(days, 1) * 30

            if retention_rate > 0 and retention_rate < 1:
                ltv_cents = int(avg_basket * avg_visit_freq * 12 * retention_rate / (1 - retention_rate))
            else:
                ltv_cents = int(avg_basket * avg_visit_freq * 12)

            churn_pct = 15.0  # industry estimate
            churn_risk = []

        else:
            # Minimal: estimate from transaction volume
            est_customers = max(len(txns) // 4, len(daily) * 20) if txns else len(daily) * 20
            total_customers = est_customers
            retention_rate = 0.4  # industry average
            avg_visit_freq = 2.5  # monthly
            ltv_cents = int(avg_basket * avg_visit_freq * 12 * retention_rate / (1 - retention_rate))
            repeat_customers = int(total_customers * retention_rate)
            churn_pct = 20.0
            churn_risk = []

        # Build insights
        insights.append({
            "type": "customer_ltv",
            "title": f"Estimated Customer LTV: ${ltv_cents / 100:.0f}",
            "detail": f"Based on {path} data: avg basket ${avg_basket / 100:.2f}, "
                      f"{avg_visit_freq:.1f} visits/mo, {retention_rate:.0%} retention",
            "impact_cents": ltv_cents,
            "estimated": path != "full",
        })

        if retention_rate < 0.5:
            gap_cents = int(avg_basket * avg_visit_freq * 12 * 0.1 / max(1 - retention_rate, 0.1))
            recommendations.append({
                "action": "Implement loyalty program to boost retention from "
                          f"{retention_rate:.0%} to {min(retention_rate + 0.1, 0.8):.0%}",
                "impact_cents": gap_cents,
                "effort": "medium",
            })

        if churn_pct > 10:
            recommendations.append({
                "action": f"Target {churn_pct:.0f}% at-risk customers with win-back offers",
                "impact_cents": int(avg_basket * 3),
                "effort": "low",
            })

        if path == "minimal":
            recommendations.append({
                "action": "Connect loyalty or customer ID data for precise LTV tracking",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        score = min(100, max(0, int(retention_rate * 100 + (50 if ltv_cents > avg_basket * 24 else 20))))

        data = {
            "ltv_cents": ltv_cents,
            "total_customers": total_customers,
            "repeat_customers": repeat_customers,
            "retention_rate": round(retention_rate, 3),
            "avg_visit_frequency_monthly": round(avg_visit_freq, 2),
            "avg_basket_cents": avg_basket,
            "churn_risk_pct": round(churn_pct, 1),
            "churn_risk_count": len(churn_risk),
        }
        if path == "full" and lifetimes_used:
            model_name = model_used or "lifetimes"
            data["model"] = (
                "BG/NBD + Gamma-Gamma (pymc-marketing, Bayesian)"
                if model_name == "pymc_marketing"
                else "BG/NBD + Gamma-Gamma (lifetimes, MLE)"
            )
            data["model_backend"] = model_name
            data["per_customer_clv_sample"] = {
                k: int(v) for k, v in list(per_customer_clv.items())[:10]
            } if per_customer_clv else {}
            # Credible intervals are the headline upgrade for the pymc-
            # marketing backend; surface a small sample so callers can
            # see the uncertainty band per customer alongside the point
            # estimate. lifetimes path leaves these empty.
            if model_name == "pymc_marketing" and per_customer_clv_lo:
                data["per_customer_clv_lo_sample"] = {
                    k: int(v) for k, v in list(per_customer_clv_lo.items())[:10]
                }
                data["per_customer_clv_hi_sample"] = {
                    k: int(v) for k, v in list(per_customer_clv_hi.items())[:10]
                }

        return self._result(
            summary=f"Customer LTV ${ltv_cents / 100:.0f} | {retention_rate:.0%} retention | "
                    f"{churn_pct:.0f}% churn risk",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data=data,
            confidence=confidence,
            calculation_path=path,
        )
