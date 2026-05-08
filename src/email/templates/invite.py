from .base import base_template, heading, paragraph, button, info_box


def render(
    inviter_name: str,
    role: str,
    portal: str,
    invite_url: str,
) -> str:
    portal_label = "Meridian Canada" if portal == "canada" else "Meridian"
    role_label = role.replace("_", " ").title()

    return base_template(
        f"""{heading(f"You've Been Invited to {portal_label}")}
{paragraph(f"<strong style='color:#F5F5F7;'>{inviter_name}</strong> has invited you to join the {portal_label} team.")}
{info_box(f'''
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">YOUR ROLE</p>
<p style="color:#F5F5F7;font-size:14px;font-weight:600;margin:0;">{role_label}</p>
''')}
<div style="text-align:center;">
{button("Accept Invitation", invite_url)}
</div>
<p style="color:#52525B;font-size:12px;margin:20px 0 0;">
This invitation expires in 7 days.
</p>""",
        preheader=f"{inviter_name} invited you to {portal_label}.",
    )
