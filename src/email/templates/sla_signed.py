from .base import base_template, heading, paragraph, info_box, stat_row, divider


def render(
    business_name: str,
    rep_name: str,
    signed_by: str,
    signed_date: str,
    provider_signatory: str = "Aidan Pierce, Founder & CEO",
) -> str:
    return base_template(
        f"""{heading("Your SLA Has Been Signed")}
{paragraph(f"The Service Level Agreement between Meridian AI Business Solutions and {business_name} has been fully executed.")}
{info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{stat_row("Provider", "Meridian AI Business Solutions")}
{stat_row("Provider Signatory", provider_signatory)}
{stat_row("Client", business_name)}
{stat_row("Client Signatory", signed_by)}
{stat_row("Signed Date", signed_date)}
{stat_row("Sales Rep", rep_name)}
</table>
''')}
{paragraph("A copy of the signed agreement is attached to this email. Please retain this for your records.")}
{divider()}
<p style="color:#52525B;font-size:12px;margin:0;">
Questions about your agreement? Reply to this email or contact your sales representative.
</p>""",
        preheader=f"SLA signed: {business_name}",
    )
