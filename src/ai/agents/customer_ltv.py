from .base import BaseAgent

try:
    from lifetimes import BetaGeoFitter, GammaGammaFitter
    from lifetimes.utils import summary_data_from_transaction_data
    HAS_LIFETIMES = True
except ImportError:
    HAS_LIFETIMES = False


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

            # --- lifetimes BG/NBD + Gamma-Gamma probabilistic CLV ---
            lifetimes_used = False
            ltv_cents = 0
            churn_risk = []
            per_customer_clv = {}

            if HAS_LIFETIMES and total_customers >= 10 and repeat_customers >= 5:
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
                        rfm = summary_data_from_transaction_data(
                            df, "customer_id", "date",
                            monetary_value_col="monetary_value",
                            observation_period_end=df["date"].max(),
                        )

                        bgf = BetaGeoFitter(penalizer_coef=0.01)
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
                            lifetimes_used = True
                            confidence = min(confidence + 0.1, 0.9)
                except Exception as e:
                    import logging
                    logging.getLogger("meridian.ai.agents").warning(
                        f"lifetimes CLV failed, falling back to manual: {e}"
                    )

            if not lifetimes_used:
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
        if path == "full" and locals().get("lifetimes_used"):
            data["model"] = "BG/NBD + Gamma-Gamma"
            data["per_customer_clv_sample"] = {
                k: int(v) for k, v in list(per_customer_clv.items())[:10]
            } if per_customer_clv else {}

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
