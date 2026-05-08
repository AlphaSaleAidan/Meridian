from .base import base_template, heading, paragraph, button, info_box


def render(
    rep_name: str,
    lead_name: str,
    lead_business: str,
    lead_phone: str,
    portal_url: str,
) -> str:
    first = rep_name.split(" ")[0]
    return base_template(
        f"""{heading(f"New Lead Assigned")}
{paragraph(f"Hey {first}, a new lead has been assigned to you.")}
{info_box(f'''
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">CONTACT</p>
<p style="color:#F5F5F7;font-size:14px;font-weight:600;margin:0 0 12px;">{lead_name}</p>
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">BUSINESS</p>
<p style="color:#F5F5F7;font-size:14px;margin:0 0 12px;">{lead_business}</p>
<p style="color:#A1A1A8;font-size:12px;margin:0 0 4px;">PHONE</p>
<p style="color:#F5F5F7;font-size:14px;margin:0;">{lead_phone}</p>
''')}
<div style="text-align:center;">
{button("View Lead", portal_url)}
</div>""",
        preheader=f"New lead: {lead_name} at {lead_business}",
    )
