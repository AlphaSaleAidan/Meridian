from .base import base_template, heading, paragraph, button, info_box, stat_row, divider


def render(
    business_name: str,
    week_label: str,
    revenue: str,
    revenue_change: str,
    orders: str,
    avg_ticket: str,
    top_insights: list[str],
    dashboard_url: str,
) -> str:
    insights_html = ""
    for insight in top_insights[:5]:
        insights_html += f'<p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; {insight}</p>\n'

    change_color = "#22C55E" if not revenue_change.startswith("-") else "#EF4444"

    return base_template(
        f"""{heading(f"Weekly Report — {business_name}")}
{paragraph(f"Here's your performance summary for {week_label}.")}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
{stat_row("Revenue", f'{revenue} <span style="color:{change_color};font-size:11px;">{revenue_change}</span>')}
{stat_row("Orders", orders)}
{stat_row("Avg. Ticket", avg_ticket)}
</table>
{divider()}
{info_box(f'''
<p style="color:#1A8FD6;font-size:13px;font-weight:600;margin:0 0 10px;">Top Insights</p>
{insights_html}
''')}
<div style="text-align:center;">
{button("View Full Report", dashboard_url)}
</div>""",
        preheader=f"{business_name} weekly: {revenue} revenue ({revenue_change})",
    )
