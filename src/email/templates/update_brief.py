"""Update Brief email template — platform updates sent to the team."""
from .base import base_template, heading, paragraph, divider


def render(
    *,
    subject_line: str,
    greeting: str = "Team",
    intro: str = "",
    sections: list[dict],
    closing: str = "",
    cta_text: str = "",
    cta_url: str = "",
) -> str:
    """Render an update brief email.

    sections: list of {"title": str, "items": list[str]} or {"title": str, "body": str}
    """
    parts: list[str] = []
    parts.append(heading(subject_line))
    parts.append(paragraph(f"Hi {greeting},"))
    if intro:
        parts.append(paragraph(intro))

    for section in sections:
        title = section.get("title", "")
        parts.append(
            f'<h3 style="color:#1A8FD6;font-size:14px;font-weight:600;'
            f'margin:20px 0 8px;text-transform:uppercase;letter-spacing:0.5px;">{title}</h3>'
        )
        if "items" in section:
            items_html = "".join(
                f'<li style="color:#A1A1A8;font-size:13px;line-height:1.65;'
                f'margin-bottom:6px;">{item}</li>'
                for item in section["items"]
            )
            parts.append(
                f'<ul style="margin:0 0 16px;padding-left:20px;">{items_html}</ul>'
            )
        elif "body" in section:
            parts.append(paragraph(section["body"]))

    if closing:
        parts.append(divider())
        parts.append(paragraph(closing))

    if cta_text and cta_url:
        parts.append(
            f'<div style="text-align:center;margin:24px 0 8px;">'
            f'<a href="{cta_url}" style="display:inline-block;background:#1A8FD6;'
            f'color:#ffffff;padding:12px 28px;border-radius:8px;text-decoration:none;'
            f'font-weight:600;font-size:14px;line-height:1;">{cta_text}</a></div>'
        )

    return base_template("\n".join(parts), preheader=intro[:100] if intro else subject_line)
