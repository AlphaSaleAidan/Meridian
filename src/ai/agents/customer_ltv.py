from .base import BaseAgent


class CustomerLTVAgent(BaseAgent):
    name = "customer_ltv"
    description = "Customer lifetime value prediction and churn risk"
    tier = 5

    def _try_btyd(self, customer_txns: dict, days: int) -> dict | None:
        """Attempt BG/NBD + Gamma-Gamma CLV prediction via btyd."""
        try:
            import pandas as pd
            from btyd import BetaGeoFitter, GammaGammaFitter
            from btyd.utils import summary_data_from_transaction_data
        except ImportError:
            return None

        rows = []
        for cid, ts in customer_txns.items():
            for t in ts:
                date = t.get("transaction_at") or t.get("date") or t.get("created_at", "")
                amount = t.get("total_cents", 0) / 100
                if date and amount > 0:
                    rows.append({"customer_id": cid, "date": str(date)[:10], "amount": amount})

        if len(rows) < 20:
            return None

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        if df.empty:
            return None

        try:
            summary = summary_data_from_transaction_data(
                df, "customer_id", "date",
                monetary_value_col="amount",
                observation_period_end=df["date"].max(),
            )

            summary = summary[summary["frequency"] > 0]
            if len(summary) < 5:
                return None

            bgf = BetaGeoFitter(penalizer_coef=0.01)
            bgf.fit(summary["frequency"], summary["recency"], summary["T"])

            summary["predicted_purchases_30"] = bgf.conditional_expected_number_of_purchases_up_to_time(
                30, summary["frequency"], summary["recency"], summary["T"],
            )
            summary["predicted_purchases_90"] = bgf.conditional_expected_number_of_purchases_up_to_time(
                90, summary["frequency"], summary["recency"], summary["T"],
            )
            summary["predicted_purchases_365"] = bgf.conditional_expected_number_of_purchases_up_to_time(
                365, summary["frequency"], summary["recency"], summary["T"],
            )

            summary["prob_alive"] = bgf.conditional_probability_alive(
                summary["frequency"], summary["recency"], summary["T"],
            )

            ggf = GammaGammaFitter(penalizer_coef=0.01)
            ggf.fit(summary["frequency"], summary["monetary_value"])

            clv_30 = ggf.customer_lifetime_value(
                bgf, summary["frequency"], summary["recency"], summary["T"],
                summary["monetary_value"], time=1, freq="D",
            )
            clv_90 = ggf.customer_lifetime_value(
                bgf, summary["frequency"], summary["recency"], summary["T"],
                summary["monetary_value"], time=3, freq="D",
            )
            clv_365 = ggf.customer_lifetime_value(
                bgf, summary["frequency"], summary["recency"], summary["T"],
                summary["monetary_value"], time=12, freq="D",
            )

            per_customer = []
            for idx, row in summary.iterrows():
                per_customer.append({
                    "customer_id": idx,
                    "frequency": int(row["frequency"]),
                    "recency_days": int(row["recency"]),
                    "tenure_days": int(row["T"]),
                    "avg_order_value": round(row["monetary_value"], 2),
                    "prob_alive": round(row["prob_alive"], 3),
                    "predicted_clv_30d": round(float(clv_30.get(idx, 0)) * 100),
                    "predicted_clv_90d": round(float(clv_90.get(idx, 0)) * 100),
                    "predicted_clv_365d": round(float(clv_365.get(idx, 0)) * 100),
                })

            per_customer.sort(key=lambda c: c["predicted_clv_365d"], reverse=True)

            avg_clv_365 = int(sum(c["predicted_clv_365d"] for c in per_customer) / max(len(per_customer), 1))
            at_risk = [c for c in per_customer if c["prob_alive"] < 0.3]

            return {
                "model": "BG/NBD + Gamma-Gamma",
                "avg_clv_365d_cents": avg_clv_365,
                "total_customers": len(per_customer),
                "at_risk_count": len(at_risk),
                "at_risk_pct": round(len(at_risk) / max(len(per_customer), 1) * 100, 1),
                "top_customers": per_customer[:20],
                "at_risk_customers": at_risk[:20],
            }

        except Exception:
            return None

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        agent_outputs = getattr(self.ctx, "agent_outputs", {})
        txns = getattr(self.ctx, "transactions", []) or []
        daily = getattr(self.ctx, "daily_revenue", []) or []

        if not txns and not daily:
            return self._insufficient_data("Transaction data required for LTV estimation")

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

        basket_output = agent_outputs.get("basket_analysis", {})
        avg_basket = basket_output.get("data", {}).get("avg_basket_size_cents", 0)
        if not avg_basket and txns:
            avg_basket = sum(t.get("total_cents", 0) for t in txns) // max(len(txns), 1)

        days = avail.date_range_days or 30

        # Try BTYD probabilistic model first (full path with customer IDs)
        btyd_result = None
        if path == "full":
            from collections import defaultdict
            customer_txns = defaultdict(list)
            for t in txns:
                cid = t.get("customer_id", "")
                if cid:
                    customer_txns[cid].append(t)

            btyd_result = self._try_btyd(customer_txns, days)

        if btyd_result:
            confidence = min(0.95, avail.quality_score + 0.1)
            ltv_cents = btyd_result["avg_clv_365d_cents"]
            total_customers = btyd_result["total_customers"]
            churn_pct = btyd_result["at_risk_pct"]
            at_risk_customers = btyd_result.get("at_risk_customers", [])

            repeat_customers = sum(
                1 for c in btyd_result.get("top_customers", []) if c["frequency"] > 1
            )
            retention_rate = repeat_customers / max(total_customers, 1)

            insights.append({
                "type": "customer_ltv",
                "title": f"Predicted Customer CLV: ${ltv_cents / 100:.0f}/yr (BG/NBD model)",
                "detail": f"Probabilistic model on {total_customers} customers. "
                          f"{churn_pct:.0f}% at risk of churning.",
                "impact_cents": ltv_cents,
                "estimated": False,
            })

            data = {
                "ltv_cents": ltv_cents,
                "model": "BG/NBD + Gamma-Gamma",
                "total_customers": total_customers,
                "repeat_customers": repeat_customers,
                "retention_rate": round(retention_rate, 3),
                "churn_risk_pct": round(churn_pct, 1),
                "at_risk_count": btyd_result["at_risk_count"],
                "top_customers": btyd_result["top_customers"][:10],
                "at_risk_customers": at_risk_customers[:10],
                "avg_basket_cents": avg_basket,
            }

            if churn_pct > 10:
                recommendations.append({
                    "action": f"Target {btyd_result['at_risk_count']} at-risk customers with win-back offers",
                    "impact_cents": int(avg_basket * 3 * btyd_result["at_risk_count"]),
                    "effort": "low",
                })

            score = min(100, max(0, int(retention_rate * 100 + (50 if ltv_cents > avg_basket * 24 else 20))))

            return self._result(
                summary=f"CLV ${ltv_cents / 100:.0f}/yr (BG/NBD) | {retention_rate:.0%} retention | "
                        f"{churn_pct:.0f}% churn risk",
                score=score,
                insights=insights,
                recommendations=recommendations,
                data=data,
                confidence=confidence,
                calculation_path="btyd",
            )

        # Fallback: manual LTV calculation
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

            if retention_rate > 0 and retention_rate < 1:
                monthly_value = avg_basket * avg_visit_freq
                annual_value = monthly_value * 12
                ltv_cents = int(annual_value * retention_rate / (1 - retention_rate))
            else:
                ltv_cents = int(avg_basket * avg_visit_freq * 12)

            churn_risk = []
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

            churn_pct = 15.0
            churn_risk = []

        else:
            est_customers = max(len(txns) // 4, len(daily) * 20) if txns else len(daily) * 20
            total_customers = est_customers
            retention_rate = 0.4
            avg_visit_freq = 2.5
            ltv_cents = int(avg_basket * avg_visit_freq * 12 * retention_rate / (1 - retention_rate))
            repeat_customers = int(total_customers * retention_rate)
            churn_pct = 20.0
            churn_risk = []

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
            "model": "manual",
            "total_customers": total_customers,
            "repeat_customers": repeat_customers,
            "retention_rate": round(retention_rate, 3),
            "avg_visit_frequency_monthly": round(avg_visit_freq, 2),
            "avg_basket_cents": avg_basket,
            "churn_risk_pct": round(churn_pct, 1),
            "churn_risk_count": len(churn_risk),
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
