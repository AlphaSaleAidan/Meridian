from .base import base_template, heading, paragraph, button, info_box


def render(first_name: str, dashboard_url: str) -> str:
    return base_template(
        f"""{heading("Onboarding Complete!")}
{paragraph(f"Nice work, {first_name}! Your account is fully set up and your POS data is syncing. Here's what to explore first:")}
{info_box('''
<p style="color:#1A8FD6;font-size:13px;font-weight:600;margin:0 0 8px;">What's next:</p>
<p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; Review your revenue dashboard</p>
<p style="color:#F5F5F7;font-size:13px;margin:0 0 6px;">&bull; Check AI-generated insights</p>
<p style="color:#F5F5F7;font-size:13px;margin:0;">&bull; Set up anomaly alerts</p>
''')}
<div style="text-align:center;">
{button("Go to Dashboard", dashboard_url)}
</div>""",
        preheader="You're all set — your POS data is syncing.",
    )
