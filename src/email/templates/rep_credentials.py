from .base import base_template, heading, paragraph, info_box, stat_row, button, divider


def render(
    rep_name: str,
    email: str,
    password: str,
    login_url: str,
) -> str:
    return base_template(
        f"""{heading("Welcome to the Meridian Sales Team!")}
{paragraph(f"Hi {rep_name}, your application has been approved and your sales rep account is ready. Use the credentials below to log in to the Canada Sales Portal.")}
{info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{stat_row("Email", email)}
{stat_row("Temporary Password", f'<code style="background:#1F1F23;padding:2px 8px;border-radius:4px;color:#F5F5F7;">{password}</code>')}
</table>
''')}
<div style="text-align:center;margin:24px 0;">
{button("Log In to Sales Portal", login_url)}
</div>
{paragraph("For security, please change your password after your first login.")}
{divider()}
<p style="color:#52525B;font-size:12px;margin:0;">
Reply to this email if you need help getting started.
</p>""",
        preheader=f"Your Meridian Sales Portal login is ready, {rep_name}",
    )
