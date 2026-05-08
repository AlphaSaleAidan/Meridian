from .base import base_template, heading, paragraph, button, info_box


def render(
    first_name: str,
    pos_name: str,
    location_name: str,
    dashboard_url: str,
) -> str:
    return base_template(
        f"""{heading("POS Connected Successfully!")}
{paragraph(f"Great news, {first_name} — your <strong style='color:#F5F5F7;'>{pos_name}</strong> account is now connected.")}
{info_box(f'''
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">LOCATION</p>
<p style="color:#F5F5F7;font-size:14px;font-weight:600;margin:0 0 12px;">{location_name}</p>
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">STATUS</p>
<p style="color:#22C55E;font-size:14px;font-weight:600;margin:0;">Syncing — data will be ready in 10-30 minutes</p>
''')}
<div style="text-align:center;">
{button("Go to Dashboard", dashboard_url)}
</div>""",
        preheader=f"Your {pos_name} POS is now connected to Meridian.",
    )
