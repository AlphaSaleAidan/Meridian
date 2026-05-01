"""Money Left on Table headline insight."""
from ._insight_helpers import fmt_cents, cite, make_insight


def generate(ctx, money_left: dict, bench, models) -> list[dict]:
    insights = []

    total = money_left.get("total_score_cents", 0)
    if total <= 0:
        return insights

    components = money_left.get("components", {})
    top_actions = money_left.get("top_actions", [])

    component_lines = []
    for name, data in sorted(
        components.items(),
        key=lambda x: x[1].get("amount_cents", 0),
        reverse=True,
    ):
        amt = data.get("amount_cents", 0)
        if amt > 0:
            component_lines.append(
                f"  • {name.replace('_', ' ').title()}: {fmt_cents(amt)}/mo"
            )

    component_text = "\n".join(component_lines[:5]) if component_lines else ""

    action_text = ""
    if top_actions:
        action_text = "\n\n*Prioritized action plan:*"
        for i, action in enumerate(top_actions[:5], 1):
            action_text += (
                f"\n{i}. {action['description']} "
                f"(est. {fmt_cents(action.get('impact_cents', 0))}/mo)"
            )

    insights.append(make_insight(
        ctx=ctx,
        type="money_left",
        title=f"💸 {fmt_cents(total)}/Month Left on the Table — Here's How to Capture It",
        summary=(
            f"Meridian's Money Left on Table analysis identifies "
            f"{fmt_cents(total)}/month in unrealized revenue across your operations. "
            f"This score is calculated using five economic dimensions, each benchmarked "
            f"against industry standards:"
            f"\n\n"
            f"*Component breakdown:*\n{component_text}"
            f"\n\n"
            f"McKinsey research confirms most SMBs leave 2-7% of revenue on the table "
            f"through suboptimal pricing, staffing, and inventory management — and that "
            f"structured optimization yields an average 3.3% revenue lift "
            f"{cite('mckinsey_pricing')}.{action_text}"
        ),
        impact_cents=total,
        confidence=0.65,
        details={
            "components": {
                k: {"amount_cents": v.get("amount_cents", 0), "detail": v.get("detail", "")}
                for k, v in components.items()
            },
            "top_actions": top_actions[:5],
            "citations": [
                "mckinsey_pricing", "hbr_pricing_power",
                "mit_sloan_scheduling", "nra_food_waste",
            ],
        },
    ))

    return insights
