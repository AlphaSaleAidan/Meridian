from .base import base_template, heading, paragraph, button


def render(first_name: str, onboarding_url: str) -> str:
    return base_template(
        f"""{heading(f"{first_name}, finish your setup")}
{paragraph("It looks like you haven't completed your onboarding yet. Finishing takes about 5 minutes and unlocks your full analytics dashboard.")}
<div style="text-align:center;">
{button("Complete Setup", onboarding_url)}
</div>
<p style="color:#52525B;font-size:12px;margin:20px 0 0;">
Questions? Reply to this email or contact support.
</p>""",
        preheader="Finish your Meridian setup — it only takes 5 minutes.",
    )
