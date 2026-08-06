"""Edge surface up/down notices — internal ops alerts, not customer mail."""
from .base import base_template, heading, paragraph, info_box, stat_row


def _detail_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(stat_row(label, value) for label, value in rows)
    return info_box(
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{body}</table>'
    )


def render_down(url: str, detail: str, consecutive_failures: int, checked_at: str) -> str:
    return base_template(
        f"""{heading("Surface unreachable")}
<div style="display:inline-block;background:#EF444422;border:1px solid #EF444444;border-radius:6px;padding:4px 10px;margin-bottom:16px;">
<span style="color:#EF4444;font-size:11px;font-weight:700;text-transform:uppercase;">down</span>
</div>
{paragraph(f"<strong style='color:#F5F5F7;'>{url}</strong> failed {consecutive_failures} consecutive checks from the Meridian backend.")}
{_detail_table([("Surface", url), ("Last error", detail), ("Consecutive failures", str(consecutive_failures)), ("Checked at", checked_at)])}
{paragraph("This probe runs on Railway, so the backend and its email path are unaffected by whatever took the surface down.")}""",
        preheader=f"DOWN — {url}",
    )


def render_recovered(url: str, downtime: str, checked_at: str) -> str:
    return base_template(
        f"""{heading("Surface recovered")}
<div style="display:inline-block;background:#17C5B022;border:1px solid #17C5B044;border-radius:6px;padding:4px 10px;margin-bottom:16px;">
<span style="color:#17C5B0;font-size:11px;font-weight:700;text-transform:uppercase;">recovered</span>
</div>
{paragraph(f"<strong style='color:#F5F5F7;'>{url}</strong> is responding again.")}
{_detail_table([("Surface", url), ("Unreachable for", downtime), ("Recovered at", checked_at)])}""",
        preheader=f"RECOVERED — {url}",
    )
