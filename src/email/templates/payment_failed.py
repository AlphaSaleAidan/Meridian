from .base import base_template, heading, paragraph, divider


def render(
    business_name: str,
    contact_name: str,
    amount: str,
    update_url: str,
    rep_name: str = "",
) -> str:
    first_name = contact_name.split()[0] if contact_name else "there"
    rep_line = f"<p style='color:#52525B;font-size:12px;margin:8px 0 0;'>Your rep <strong>{rep_name}</strong> is here to help if you have questions.</p>" if rep_name else ""

    return base_template(
        f"""{heading("Payment Update Needed")}
{paragraph(f"Hi {first_name},")}
{paragraph(f"We weren't able to process the latest payment of <strong>{amount}</strong> for <strong>{business_name}</strong>. This can happen if your card expired or was declined.")}
{paragraph("To keep your Meridian Analytics dashboard active, please update your payment method using the link below:")}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
<tr><td align="center">
<a href="{update_url}" style="display:inline-block;padding:12px 32px;background:#1A8FD6;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;border-radius:8px;">Update Payment Method</a>
</td></tr>
</table>
{divider()}
{paragraph("If you've already resolved this, you can ignore this email. Your service will continue uninterrupted once payment is confirmed.")}
{rep_line}
<p style="color:#52525B;font-size:12px;margin:8px 0 0;">
Need help? Reply to this email or contact <a href="mailto:help@meridian.tips" style="color:#1A8FD6;">help@meridian.tips</a>
</p>""",
        preheader=f"Payment update needed for {business_name}",
    )
