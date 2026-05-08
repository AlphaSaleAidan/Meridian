from .base import base_template, heading, paragraph, button, info_box


def render(
    first_name: str,
    days_remaining: int,
    billing_url: str,
) -> str:
    urgency = "tomorrow" if days_remaining <= 1 else f"in {days_remaining} days"
    return base_template(
        f"""{heading(f"Your Trial Ends {urgency.title()}")}
{paragraph(f"Hey {first_name}, your Meridian free trial expires {urgency}. Upgrade now to keep access to all your analytics, insights, and AI agents.")}
{info_box('''
<p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; Revenue analytics &amp; forecasts</p>
<p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; AI anomaly detection</p>
<p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; Menu engineering matrix</p>
<p style="color:#F5F5F7;font-size:13px;margin:0;">&bull; Phone order agent</p>
''')}
<div style="text-align:center;">
{button("Upgrade Now", billing_url)}
</div>""",
        preheader=f"Your Meridian trial ends {urgency}.",
    )
