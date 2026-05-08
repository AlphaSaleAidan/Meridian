"""Base HTML template — dark-themed, Meridian brand."""


def base_template(content: str, *, preheader: str = "") -> str:
    """Wrap inner content in the Meridian email shell."""
    preheader_block = ""
    if preheader:
        preheader_block = (
            f'<span style="display:none;font-size:1px;color:#0A0A0B;'
            f'max-height:0;overflow:hidden;">{preheader}</span>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Meridian</title>
</head>
<body style="margin:0;padding:0;background:#0A0A0B;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;-webkit-text-size-adjust:100%;">
{preheader_block}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0B;">
<tr><td align="center" style="padding:40px 16px;">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

<!-- Logo -->
<tr><td align="center" style="padding-bottom:28px;">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td style="width:36px;height:36px;border-radius:8px;background:rgba(26,143,214,0.12);border:1px solid rgba(26,143,214,0.25);text-align:center;vertical-align:middle;">
<span style="color:#1A8FD6;font-weight:bold;font-size:16px;line-height:36px;">M</span>
</td>
<td style="padding-left:10px;">
<span style="color:#F5F5F7;font-size:18px;font-weight:700;letter-spacing:-0.3px;">Meridian</span>
</td>
</tr>
</table>
</td></tr>

<!-- Content card -->
<tr><td style="background:#111113;border:1px solid #1F1F23;border-radius:12px;padding:32px 28px;">
{content}
</td></tr>

<!-- Footer -->
<tr><td style="padding-top:24px;text-align:center;">
<p style="color:#52525B;font-size:11px;margin:0;line-height:1.5;">
Meridian POS Intelligence<br>
<a href="https://meridian.tips" style="color:#52525B;text-decoration:underline;">meridian.tips</a>
</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def button(text: str, url: str) -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:#1A8FD6;color:#ffffff;'
        f"padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;"
        f'font-size:14px;line-height:1;">{text}</a>'
    )


def heading(text: str) -> str:
    return f'<h2 style="color:#F5F5F7;font-size:20px;font-weight:700;margin:0 0 12px;line-height:1.3;">{text}</h2>'


def paragraph(text: str) -> str:
    return f'<p style="color:#A1A1A8;font-size:14px;line-height:1.65;margin:0 0 20px;">{text}</p>'


def info_box(content: str) -> str:
    return (
        f'<div style="background:#0A0A0B;border:1px solid #1F1F23;border-radius:8px;'
        f'padding:16px;margin:0 0 20px;">{content}</div>'
    )


def stat_row(label: str, value: str) -> str:
    return (
        f'<tr><td style="color:#A1A1A8;font-size:13px;padding:4px 0;">{label}</td>'
        f'<td style="color:#F5F5F7;font-size:13px;font-weight:600;padding:4px 0;text-align:right;">{value}</td></tr>'
    )


def divider() -> str:
    return '<hr style="border:none;border-top:1px solid #1F1F23;margin:24px 0;">'
