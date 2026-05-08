from .base import base_template, heading, paragraph, button, info_box


def render(first_name: str, login_url: str, connect_url: str) -> str:
    return base_template(
        f"""{heading(f"Welcome to Meridian, {first_name}!")}
{paragraph("Your POS intelligence platform is ready. Connect your point-of-sale system and we'll start analyzing your transaction data within minutes.")}
{info_box('''
<p style="color:#F5F5F7;font-size:13px;margin:0 0 8px;"><strong style="color:#1A8FD6;">1.</strong> Log in to your dashboard</p>
<p style="color:#F5F5F7;font-size:13px;margin:0 0 8px;"><strong style="color:#1A8FD6;">2.</strong> Connect your Square / Clover / Toast POS</p>
<p style="color:#F5F5F7;font-size:13px;margin:0;"><strong style="color:#1A8FD6;">3.</strong> Your data syncs in 10-30 minutes</p>
''')}
<div style="text-align:center;padding-top:4px;">
{button("Go to Dashboard", login_url)}
</div>""",
        preheader="Your POS intelligence platform is ready.",
    )
