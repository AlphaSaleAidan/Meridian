from .base import base_template, heading, paragraph, button, info_box


def render(
    business_name: str,
    alert_title: str,
    alert_detail: str,
    severity: str,
    dashboard_url: str,
) -> str:
    severity_colors = {
        "critical": "#EF4444",
        "high": "#F59E0B",
        "medium": "#1A8FD6",
        "low": "#6B7280",
    }
    color = severity_colors.get(severity, "#F59E0B")

    return base_template(
        f"""{heading(f"Alert: {alert_title}")}
<div style="display:inline-block;background:{color}22;border:1px solid {color}44;border-radius:6px;padding:4px 10px;margin-bottom:16px;">
<span style="color:{color};font-size:11px;font-weight:700;text-transform:uppercase;">{severity}</span>
</div>
{paragraph(f"An anomaly was detected for <strong style='color:#F5F5F7;'>{business_name}</strong>:")}
{info_box(f'<p style="color:#F5F5F7;font-size:13px;margin:0;line-height:1.6;">{alert_detail}</p>')}
<div style="text-align:center;">
{button("View in Dashboard", dashboard_url)}
</div>""",
        preheader=f"[{severity.upper()}] {alert_title} — {business_name}",
    )
