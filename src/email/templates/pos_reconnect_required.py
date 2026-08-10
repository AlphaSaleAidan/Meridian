from .base import base_template, heading, paragraph, button, info_box


def render(
    first_name: str,
    pos_name: str,
    location_name: str,
    reconnect_url: str,
) -> str:
    return base_template(
        f"""{heading(f"Reconnect your {pos_name} account")}
{paragraph(f"Hi {first_name} — {pos_name} has stopped accepting our connection, so Meridian is no longer receiving your sales data.")}
{paragraph("This happens when the authorisation expires or is withdrawn on the POS side. It takes about thirty seconds to restore, and nothing already in your dashboard is lost.")}
{info_box(f'''
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">LOCATION</p>
<p style="color:#F5F5F7;font-size:14px;font-weight:600;margin:0 0 12px;">{location_name}</p>
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">STATUS</p>
<p style="color:#F59E0B;font-size:14px;font-weight:600;margin:0;">Disconnected — new sales are not syncing</p>
''')}
<div style="text-align:center;">
{button(f"Reconnect {pos_name}", reconnect_url)}
</div>
{paragraph("Once you reconnect, we backfill everything recorded while the connection was down, so no revenue goes missing from your reports.")}""",
        preheader=f"{pos_name} needs reconnecting — new sales are not reaching Meridian.",
    )
