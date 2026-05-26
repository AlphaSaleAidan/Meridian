from .base import base_template, heading, paragraph, info_box, stat_row, button, divider
from typing import Optional


def render(
    rep_name: str,
    email: str,
    password: Optional[str],
    login_url: str,
) -> str:
    if password:
        credentials_block = info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{stat_row("Email", email)}
{stat_row("Temporary Password", f'<code style="background:#1F1F23;padding:2px 8px;border-radius:4px;color:#F5F5F7;">{password}</code>')}
</table>
''')
        password_note = paragraph("For security, please change your password after your first login.")
    else:
        credentials_block = info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{stat_row("Email", email)}
{stat_row("Password", "Use the password you created during signup")}
</table>
''')
        password_note = ""

    return base_template(
        f"""{heading("Welcome to the Meridian Sales Team!")}
{paragraph(f"Hi {rep_name}, your application has been approved and your sales rep account is ready. Log in to your Sales Portal to get started.")}
{credentials_block}
<div style="text-align:center;margin:24px 0;">
{button("Log In to Sales Portal", login_url)}
</div>
{password_note}{divider()}
<p style="color:#52525B;font-size:12px;margin:0;">
Reply to this email if you need help getting started.
</p>""",
        preheader=f"Your Meridian Sales Portal login is ready, {rep_name}",
    )
