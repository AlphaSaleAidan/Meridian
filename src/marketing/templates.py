"""
Email Templates — HTML templates for marketing campaigns.

Minimal, mobile-friendly templates matching Meridian brand.
"""
from typing import Any

BRAND_COLOR = "#1A8FD6"
BG_COLOR = "#0A0A0B"
CARD_BG = "#1F1F23"
TEXT_COLOR = "#F5F5F7"
MUTED_COLOR = "#A1A1A8"

BASE_STYLE = f"""
<style>
  body {{ background: {BG_COLOR}; color: {TEXT_COLOR}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 24px; }}
  .card {{ background: {CARD_BG}; border-radius: 12px; padding: 24px; margin: 16px 0; border: 1px solid #2A2A2E; }}
  .header {{ color: {BRAND_COLOR}; font-size: 24px; font-weight: 700; margin-bottom: 16px; }}
  .metric {{ font-size: 32px; font-weight: 700; font-family: monospace; color: {TEXT_COLOR}; }}
  .muted {{ color: {MUTED_COLOR}; font-size: 14px; }}
  .cta {{ display: inline-block; background: {BRAND_COLOR}; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 16px; }}
  .footer {{ color: {MUTED_COLOR}; font-size: 12px; margin-top: 32px; text-align: center; }}
</style>
"""

TEMPLATES: dict[str, str] = {
    "win_back": """
<!DOCTYPE html>
<html>
<head>{style}</head>
<body>
<div class="container">
  <div class="card">
    <div class="header">Customer Win-Back Alert</div>
    <p>{total_at_risk} customers are at risk of churning.</p>
    <p class="muted">Average lifetime value:</p>
    <div class="metric">${avg_ltv}</div>
    <p>These customers haven't visited recently. A personalized offer could bring them back.</p>
    <a href="https://app.meridian.tips/actions" class="cta">View Action Plan</a>
  </div>
  <div class="footer">Meridian Analytics — Powered by AI</div>
</div>
</body>
</html>
""",

    "promo_performance": """
<!DOCTYPE html>
<html>
<head>{style}</head>
<body>
<div class="container">
  <div class="card">
    <div class="header">Promotion Performance Report</div>
    <p>Your top promotions generated:</p>
    <div class="metric">${total_lift}</div>
    <p class="muted">in additional revenue</p>
    <p>Top performing promotions are driving real results. See the full breakdown in your dashboard.</p>
    <a href="https://app.meridian.tips/insights" class="cta">View Full Report</a>
  </div>
  <div class="footer">Meridian Analytics — Powered by AI</div>
</div>
</body>
</html>
""",

    "retention_sequence": """
<!DOCTYPE html>
<html>
<head>{style}</head>
<body>
<div class="container">
  <div class="card">
    <div class="header">Retention Alert</div>
    <p>{total_churning} customers show signs of leaving.</p>
    <p class="muted">Average days since last visit:</p>
    <div class="metric">{avg_days} days</div>
    <p>A targeted retention campaign could save significant revenue. We've identified the customers most likely to respond.</p>
    <a href="https://app.meridian.tips/customers" class="cta">Launch Retention Campaign</a>
  </div>
  <div class="footer">Meridian Analytics — Powered by AI</div>
</div>
</body>
</html>
""",
}


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """Render an email template with context variables."""
    template = TEMPLATES.get(template_name)
    if not template:
        return f"<p>Unknown template: {template_name}</p>"

    replacements = {
        "{style}": BASE_STYLE,
        "{total_at_risk}": str(context.get("total_at_risk", 0)),
        "{avg_ltv}": f"{context.get('avg_ltv_cents', 0) / 100:,.2f}",
        "{total_lift}": f"{context.get('total_lift_cents', 0) / 100:,.2f}",
        "{total_churning}": str(context.get("total_churning", 0)),
        "{avg_days}": str(context.get("avg_days_since_visit", 0)),
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result
