"""Proposal email — sent by a rep from the lead page ("Email Proposal").

The frontend has posted template='proposal_sent' since the Canada portal
shipped, but the template never existed server-side, so every send 400'd
with "Unknown template". This is that missing template.
"""
from .base import base_template, button, heading, paragraph, info_box, stat_row, divider


def render(
    business_name: str,
    first_name: str = "",
    rep_name: str = "",
    rep_email: str = "",
    plan_name: str = "",
    monthly_price: str = "",
    setup_fee: str = "",
    due_today: str = "",
    proposal_url: str = "",
) -> str:
    rows = ""
    if plan_name:
        rows += stat_row("Plan", plan_name)
    if monthly_price:
        rows += stat_row("Monthly", monthly_price)
    if setup_fee:
        rows += stat_row("Setup Fee (one-time)", setup_fee)
    if due_today:
        rows += stat_row("Due today", due_today)

    greet = f"Hi {first_name}," if first_name else "Hello,"
    cta = button("View Your Proposal", proposal_url) if proposal_url else ""
    contact = (
        f"{rep_name} ({rep_email})" if rep_name and rep_email
        else rep_name or rep_email or "your Meridian representative"
    )

    return base_template(
        f"""{heading(f"Your Meridian Proposal — {business_name}")}
{paragraph(greet)}
{paragraph(f"Thanks for your time. Here is the Meridian proposal we put together for {business_name} — everything we discussed, in one place.")}
{info_box(f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{rows}
</table>
''') if rows else ""}
{cta}
{paragraph("No contracts, month-to-month, cancel anytime with 30 days' notice.")}
{divider()}
{paragraph(f"Questions? Reply to this email or reach out to {contact} directly.")}
""",
        preheader=f"Your Meridian proposal for {business_name}",
    )
