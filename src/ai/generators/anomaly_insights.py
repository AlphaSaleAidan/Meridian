"""Anomaly detection insights with statistical context."""
from ._insight_helpers import fmt_cents, cite, make_insight


def generate(ctx, revenue: dict, bench, models) -> list[dict]:
    insights = []

    anomalies = revenue.get("anomalies", [])
    recent = [
        a for a in anomalies
        if a.get("severity") in ("high", "medium")
    ][:3]

    for anomaly in recent:
        atype = anomaly.get("type", "anomaly")
        emoji = "📈" if atype == "spike" else "📉"
        z_score = abs(anomaly.get("z_score", 0))
        confidence = min(z_score / 5, 0.95)
        dev_pct = abs(anomaly.get("deviation_pct", 0))

        insights.append(make_insight(
            ctx=ctx,
            type="anomaly",
            title=f"{emoji} Statistical Anomaly: {dev_pct:.0f}% {'Above' if atype == 'spike' else 'Below'} Expected ({anomaly.get('date', '')})",
            summary=(
                f"Revenue of {fmt_cents(anomaly.get('revenue_cents', 0))} on "
                f"{anomaly.get('date', 'this day')} represents a {dev_pct:.0f}% deviation "
                f"from the expected {fmt_cents(anomaly.get('expected_cents', 0))} "
                f"(z-score: {z_score:.1f}σ, confidence: {confidence:.0%})."
                f"\n\n"
                + (
                    f"*Positive anomaly investigation:*\n"
                    f"Identify the driver — was it higher traffic, larger tickets, or a specific "
                    f"product? If replicable, this pattern could be worth "
                    f"~{fmt_cents(int(anomaly.get('revenue_cents', 0) - anomaly.get('expected_cents', 0)))}/occurrence. "
                    f"McKinsey's customer analytics research shows businesses that identify and "
                    f"replicate positive anomalies see 10-30% lift in targeted segments "
                    f"{cite('mckinsey_customer_analytics')}."
                    if atype == "spike" else
                    f"*Root cause framework:*\n"
                    f"1. External: Weather, local events, holidays, competitor activity\n"
                    f"2. Operational: Staffing issues, supply stockouts, equipment problems\n"
                    f"3. Systemic: POS downtime, payment processing errors\n"
                    f"NRA seasonal analysis shows revenue can vary ±15-20% from seasonal "
                    f"factors alone {cite('nra_seasonal_trends')}. Rule out seasonality "
                    f"before investigating operational causes."
                )
            ),
            impact_cents=abs(
                anomaly.get("revenue_cents", 0) - anomaly.get("expected_cents", 0)
            ),
            confidence=confidence,
            details={
                "anomaly": anomaly,
                "z_score": z_score,
                "citations": ["mckinsey_customer_analytics", "nra_seasonal_trends"],
            },
        ))

    return insights
