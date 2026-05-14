from .base import base_template, heading, paragraph, button, info_box


def render(
    staff_name: str,
    week_range: str,
    shift_summary: str,
    schedule_url: str,
) -> str:
    return base_template(
        f"""{heading(f"Your Schedule is Ready, {staff_name}!")}
{paragraph(f"The schedule for <strong>{week_range}</strong> has been published. Here are your upcoming shifts:")}
{info_box(f'<p style="color:#F5F5F7;font-size:13px;margin:0;line-height:1.8;">{shift_summary}</p>')}
{paragraph("If you have any questions or need to request a change, please contact your manager.")}
<div style="text-align:center;padding-top:4px;">
{button("View Schedule", schedule_url)}
</div>""",
        preheader=f"Your schedule for {week_range} is ready.",
    )
