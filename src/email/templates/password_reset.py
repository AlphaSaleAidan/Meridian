from .base import base_template, heading, paragraph, button


def render(reset_url: str, expires_minutes: int = 60) -> str:
    return base_template(
        f"""{heading("Reset Your Password")}
{paragraph("We received a request to reset your Meridian password. Click the button below to choose a new password.")}
<div style="text-align:center;margin-bottom:20px;">
{button("Reset Password", reset_url)}
</div>
<p style="color:#52525B;font-size:12px;margin:0;">
This link expires in {expires_minutes} minutes. If you didn't request this, you can safely ignore this email.
</p>""",
        preheader="Reset your Meridian password.",
    )
