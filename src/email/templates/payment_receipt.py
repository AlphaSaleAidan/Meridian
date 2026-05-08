from .base import base_template, heading, paragraph, info_box, stat_row, divider


def render(
    business_name: str,
    plan_name: str,
    amount: str,
    period: str,
    invoice_url: str,
) -> str:
    return base_template(
        f"""{heading("Payment Receipt")}
{paragraph(f"Thank you! Here's your receipt for {business_name}.")}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
{stat_row("Plan", plan_name)}
{stat_row("Period", period)}
{stat_row("Amount", amount)}
</table>
{divider()}
<p style="color:#52525B;font-size:12px;margin:0;">
<a href="{invoice_url}" style="color:#1A8FD6;text-decoration:underline;">View invoice</a>
&nbsp;&middot;&nbsp;
Need help? Reply to this email.
</p>""",
        preheader=f"Receipt: {amount} for {plan_name}",
    )
