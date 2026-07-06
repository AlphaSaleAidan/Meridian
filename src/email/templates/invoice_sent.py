"""Invoice email — sent by a rep from the lead page ("Email Invoice").

Same story as proposal_sent: the frontend has posted template='invoice_sent'
since the Canada portal shipped, but no server-side template existed, so
every send 400'd. This is that missing template.
"""
from .base import base_template, button, heading, paragraph, info_box, stat_row, divider


def render(
    business_name: str,
    first_name: str = "",
    invoice_number: str = "",
    amount: str = "",
    rep_name: str = "",
    rep_email: str = "",
    invoice_url: str = "",
    recurring: bool = False,
) -> str:
    rows = ""
    if invoice_number:
        rows += stat_row("Invoice", invoice_number)
    if amount:
        rows += stat_row("Amount", amount + (" / month" if recurring else ""))
    if recurring:
        rows += stat_row("Billing", "Recurring monthly — cancel anytime")

    greet = f"Hi {first_name}," if first_name else "Hello,"
    cta = button("View &amp; Pay Invoice", invoice_url) if invoice_url else ""
    contact = (
        f"{rep_name} ({rep_email})" if rep_name and rep_email
        else rep_name or rep_email or "your Meridian representative"
    )

    return base_template(
        f"""{heading(f"Invoice from Meridian — {business_name}")}
{paragraph(greet)}
{paragraph(f"Your Meridian invoice for {business_name} is ready.")}
{info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{rows}
</table>
''') if rows else ""}
{cta}
{divider()}
{paragraph(f"Questions about this invoice? Reply to this email or contact {contact}.")}
""",
        preheader=f"Your Meridian invoice for {business_name}",
    )
