from .base import base_template, heading, paragraph, info_box, stat_row, button, divider


def render(
    business_name: str,
    email: str,
    password: str,
    login_url: str,
    rep_name: str = "",
) -> str:
    return base_template(
        f"""{heading("Your Meridian Login")}
{paragraph(f"Welcome to Meridian! Your account for {business_name} is ready. Use the credentials below to log in and access your business intelligence dashboard.")}
{info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{stat_row("Email", email)}
{stat_row("Temporary Password", f'<code style="background:#1F1F23;padding:2px 8px;border-radius:4px;color:#F5F5F7;">{password}</code>')}
</table>
''')}
<div style="text-align:center;margin:24px 0;">
{button("Log In to Meridian", login_url)}
</div>
{paragraph("For security, please change your password after your first login.")}
{divider()}
<p style="color:#52525B;font-size:12px;margin:0;">
{f"Your sales rep {rep_name} set this up for you. " if rep_name else ""}Reply to this email if you need help.
</p>""",
        preheader=f"Your Meridian login for {business_name}",
    )
