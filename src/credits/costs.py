"""Credit cost catalog — single source of truth, shared with the frontend.

Pricing model: 1 credit ≈ $0.001 retail at the lowest pack tier ($2 / 2000).
At the Agency tier ($35 / 50000) credits are ~30% cheaper per unit, so the
margins below assume the worst case (lowest tier).

Margin policy (target ~3.3x on telecom-routed costs):
  - Twilio/LLM cost line items are listed in costs.py so we can re-check
    margins when carrier prices move.
  - Phone is metered per minute (rounded up to next 30s).
  - SMS is metered per direction (inbound processed + outbound sent).

If you change a number here, also bump frontend/src/lib/content-demo-data.ts
CREDIT_COSTS and any upsell-modal copy that quotes specific credit amounts.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CreditCost:
    """One pricing entry: action key, credit cost, and the underlying $ basis."""
    action: str
    credits: int
    underlying_cost_usd: float
    description: str

    @property
    def retail_usd(self) -> float:
        return self.credits * 0.001

    @property
    def margin_multiple(self) -> float:
        if self.underlying_cost_usd <= 0:
            return float("inf")
        return self.retail_usd / self.underlying_cost_usd


# Phone — per minute of call audio (rounded up to next 30s).
# Underlying: Twilio Voice $0.0085 + Media Streams $0.004 + SambaNova ~$0.002 + compute = ~$0.015.
PHONE_CALL_PER_MIN = CreditCost(
    action="phone_call_per_min",
    credits=50,
    underlying_cost_usd=0.015,
    description="AI phone call (per minute, rounded up to next 30s)",
)

# SMS — split per direction so customers can see they're not paying for
# inbound spam that the LLM never replied to in a useful way.
# Inbound: Twilio inbound $0.0075 + SambaNova ~$0.001 = ~$0.0085.
SMS_INBOUND = CreditCost(
    action="sms_inbound",
    credits=20,
    underlying_cost_usd=0.0085,
    description="Inbound SMS processed by the AI",
)
# Outbound: Twilio outbound $0.0079 + LLM tail ~$0.001 = ~$0.0089 per segment.
SMS_OUTBOUND = CreditCost(
    action="sms_outbound",
    credits=30,
    underlying_cost_usd=0.0089,
    description="Outbound SMS sent by the AI (per segment)",
)

# Content generation — already defined in frontend, mirrored here for backend
# enforcement once the content routes start checking balance.
CONTENT_SOCIAL_POST = CreditCost(
    action="content_social_post",
    credits=100,
    underlying_cost_usd=0.04,  # fal.ai image + LLM copy
    description="Social post (image + copy)",
)
CONTENT_SEO_ARTICLE = CreditCost(
    action="content_seo_article",
    credits=250,
    underlying_cost_usd=0.10,  # longer LLM context
    description="SEO article (300-3000 words)",
)
CONTENT_IMAGE_REGEN = CreditCost(
    action="content_image_regen",
    credits=75,
    underlying_cost_usd=0.03,
    description="Regenerate image variant",
)
CONTENT_CAPTION = CreditCost(
    action="content_caption_only",
    credits=50,
    underlying_cost_usd=0.005,
    description="Rewrite caption (no image)",
)


COSTS: dict[str, CreditCost] = {
    c.action: c
    for c in [
        PHONE_CALL_PER_MIN,
        SMS_INBOUND,
        SMS_OUTBOUND,
        CONTENT_SOCIAL_POST,
        CONTENT_SEO_ARTICLE,
        CONTENT_IMAGE_REGEN,
        CONTENT_CAPTION,
    ]
}


# Free starter grant on signup. Sized so a merchant can run a meaningful
# demo (~20 min of calls or ~30 SMS exchanges) and close at least 5-10
# real orders before they hit zero. At $25-50 avg ticket that's
# $150-1000 of revenue generated before the merchant pays a cent.
STARTER_GRANT = 1000

# When balance drops below this, the dashboard surfaces a low-balance
# nudge and (eventually) the API emails the merchant. Sized for "a couple
# more calls and you're out."
LOW_BALANCE_THRESHOLD = 200


def cost_for_phone_call(duration_seconds: int) -> int:
    """Total credit cost for a phone call of the given duration.

    Rounds up to the next 30-second increment so a 31-second call costs
    a full minute. Minimum 1 minute (50 credits) — covers calls that
    connect and drop before any conversation happens, since Twilio still
    bills us for the leg.
    """
    if duration_seconds <= 0:
        return 0
    half_minutes = math.ceil(duration_seconds / 30)
    minutes_billed = max(2, half_minutes) / 2  # min 2 half-minutes = 1 full minute
    return int(minutes_billed * PHONE_CALL_PER_MIN.credits)
