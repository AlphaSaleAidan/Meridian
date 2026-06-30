"""
Domain: MARKETING / DEMAND GENERATION & REPUTATION.

Each archetype is a distinct reasoning pattern about *creating demand* and
*managing reputation* — owned channels (email, loyalty, SMS), earned signals
(reviews, word-of-mouth, UGC), and occasion-driven pushes (seasonal, birthday,
local-event). Specialization per vertical changes the lever: a florist's missed
occasion is the Valentine's/Mother's-Day preorder window; a jeweler's is the
anniversary trigger; a restaurant's is the lapsed-regular reactivation; a
dispensary's is the loyalty tier.

Signal provenance (rigorous, so gaps are explicit not silent):
  * Email archetypes read the EXISTING `email_send_log` (opened_at / clicked_at /
    bounced_at) → swarm_capability FULL.
  * Promo/reactivation/lifecycle archetypes join email_send_log + transactions and
    need a fusion/lifecycle agent → PARTIAL.
  * Review / social / listing archetypes have NO ingest yet → MISSING, and each
    specs the new ReviewIngestAgent / ReputationAgent that must be built first.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical, VERTICALS
from .base import Archetype, Built, X, register


# ── Targeting helpers (union semantics, fed into applies_keys) ───────────────
def _keys_with_any_flag(*flags: str) -> tuple[str, ...]:
    fs = set(flags)
    return tuple(v.key for v in VERTICALS if fs & v.flags)


def _keys_with_channel(*channels: str) -> tuple[str, ...]:
    cs = set(channels)
    return tuple(v.key for v in VERTICALS if cs & set(v.channels))


_OCCASION = {
    "florist": "Valentine's / Mother's-Day / sympathy",
    "jewelry": "engagement / anniversary / holiday-gift",
    "event_venue": "wedding-season / holiday-party",
    "full_restaurant": "Valentine's / Mother's-Day / holiday",
    "spa": "Mother's-Day / holiday gifting",
    "med_spa": "wedding-prep / holiday gifting",
}


def _occasion(v: Vertical) -> str:
    return _OCCASION.get(v.key, "peak-season / holiday")


# ═══════════════════════ OWNED: EMAIL (existing log) ═════════════════════════
def _email_open_click_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your emails get opened but don't get clicked — {X}% open, {X}% click",
        observation=f"Across the last {X} sends, opened_at fires on {X}% of recipients but clicked_at on only {X}% — the subject line works, the body doesn't.",
        reasoning=f"A high open / low click gap means attention is being won and then wasted: the offer, the call-to-action, or the {unit} relevance inside the email is failing, so paid attention converts to zero {unit}s.",
        conclusion=f"Rewrite the top {X} campaigns to a single {unit}-specific CTA above the fold and A/B test against the current body for {X} sends.",
        expected_effect=f"Lifting click-through to {X}% on an already-opening list is worth ~${X}/mo at your average {unit} value.",
        recommend_when={"state": "open_high_click_low", "min_signal": "email_send_log"},
        tags=("marketing", "email", v.family),
    )


def _email_list_underused(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You email your list {X}x/month — far below what it can carry",
        observation=f"email_send_log shows only {X} campaigns in the last {X} days to {X} reachable contacts; most months have zero sends.",
        reasoning=f"An owned list is the one demand channel with no per-{v.sale_unit} acquisition cost; leaving it idle means the cheapest repeat-{v.sale_unit} lever you own is switched off while you pay for harder channels.",
        conclusion=f"Set a steady cadence of {X} value-led emails/month (not just discounts) and measure incremental {v.sale_unit}s versus the silent baseline.",
        expected_effect=f"A reactivated list at {X} sends/month typically returns ~${X}/mo in otherwise-unprompted {v.sale_unit}s.",
        recommend_when={"state": "list_underused", "min_signal": "email_send_log"},
        tags=("marketing", "email", v.family),
    )


def _email_bounce_decay(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your list is decaying — {X}% of sends bounce",
        observation=f"bounced_at is set on {X}% of the last {X} sends and the bounce rate is climbing month over month.",
        reasoning=f"A rising hard-bounce rate drags sender reputation down, which suppresses inbox placement for the {X}% of contacts who ARE valid — so a dirty list quietly throttles every future campaign, not just the dead addresses.",
        conclusion=f"Suppress addresses with {X}+ consecutive bounces, run a re-confirmation send to the stale {X}% segment, and stop importing unverified contacts.",
        expected_effect=f"Cleaning the list restores deliverability to the ~{X} valid contacts and protects ~${X}/mo of email-driven {v.sale_unit}s.",
        recommend_when={"state": "list_decay", "min_signal": "email_send_log"},
        tags=("marketing", "email", "deliverability", v.family),
    )


# ═══════════════════════ OWNED: PROMO ECONOMICS ═════════════════════════════
def _promo_roi_negative(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {X} promo loses money on every redemption",
        observation=f"The {X} campaign drove {X} redemptions, but at a {X}% discount the redeemed {unit}s carried negative contribution after the markdown.",
        reasoning=f"Redemptions are not the win — incremental margin is. A promo that mostly subsidizes {unit}s customers would have bought anyway converts marketing spend into a direct margin transfer to existing demand.",
        conclusion=f"Gate the offer to lapsed-only contacts and cap the discount at {X}%, or switch to a fixed add-on instead of a percentage off the core {unit}.",
        expected_effect=f"Retargeting the same promo to non-cannibalizing segments turns a ~${X}/mo loss into break-even or better.",
        recommend_when={"state": "promo_roi_negative", "min_signal": "email_send_log"},
        tags=("marketing", "promotions", "margin", v.family),
    )


def _winback_discount_too_generous(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your win-back works — but the discount gives away the margin",
        observation=f"Reactivation emails recover {X}% of lapsed customers, yet at a {X}% win-back code the first {v.sale_unit} back returns little net margin.",
        reasoning=f"Win-back is worth paying for ONLY if the reactivated customer returns to full-price {v.sale_unit}s afterward; if second-visit rate is low, a deep code buys one subsidized {v.sale_unit} and no relationship.",
        conclusion=f"Test a shallower {X}% offer plus a reason-to-return (new {v.sale_unit}, loyalty enrolment) and track second-{v.sale_unit} rate, not just redemption.",
        expected_effect=f"Tuning win-back depth to the lifetime-value math protects ~${X}/mo while keeping the reactivation lift.",
        recommend_when={"state": "winback_too_deep", "min_signal": "transactions"},
        tags=("marketing", "retention", "margin", v.family),
    )


def _offpeak_promo_untapped(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You never market into your slow {X} window",
        observation=f"The {X}–{X} window carries only {X}% of {v.sale_unit}s, yet no email, SMS, or offer ever targets it — every campaign hits already-busy times.",
        reasoning=f"Marketing spent on a peak you already fill just shifts demand you'd capture anyway; the same spend aimed at a structurally slow window adds incremental {v.sale_unit}s on fixed costs you're already paying.",
        conclusion=f"Run a time-boxed off-peak offer (happy-{v.sale_unit}, slow-day perk) to the list and measure lift in the {X} window against control days.",
        expected_effect=f"Filling even {X}% of the slow window on existing fixed costs is worth ~${X}/mo in incremental margin.",
        recommend_when={"state": "offpeak_unmarketed", "min_signal": "hourly_revenue"},
        tags=("marketing", "demand_shaping", v.family),
    )


# ═══════════════════════ LIFECYCLE (email + txn fusion) ═════════════════════
def _reactivation_opportunity(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "leaking": " The lapsed segment is growing month over month — the leak is active, not historical.",
        "untapped": " No reactivation email has ever been sent to this segment.",
    }.get(situation, "")
    return Built(
        title=f"{X} once-regular customers have gone quiet — and no one has asked them back",
        observation=f"{X} contacts who used to buy {X}+ {unit}s/month haven't transacted in {X} days, yet sit in your list with no reactivation touch.{extra}",
        reasoning=f"Lapsed regulars are the highest-intent, lowest-cost demand you can recover: they already know the {v.name.lower()}, so a single relevant nudge converts far better than acquiring a cold {unit}.",
        conclusion=f"Trigger a {X}-step win-back sequence to the lapsed segment with a reason-to-return, not just a discount.",
        expected_effect=f"Recovering even {X}% of {X} lapsed regulars is worth ~${X}/mo in restored {unit} value.",
        recommend_when={"state": "lapsed_regulars", "min_signal": "transactions"},
        tags=("marketing", "reactivation", v.family),
    )


def _new_customer_no_followup(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"First-time customers get no second-visit nudge",
        observation=f"{X}% of {unit}s last period were first-timers, but only {X}% received any follow-up before their next visit window closed.",
        reasoning=f"The gap between a first and second {unit} is where churn is decided; a timely, well-framed follow-up in that window is the single highest-leverage point to convert a one-off into a repeat {v.name.lower()} customer.",
        conclusion=f"Auto-send a first-visit thank-you + low-friction reason-to-return within {X} days of a customer's first {unit}.",
        expected_effect=f"Lifting first-to-second conversion by {X}pts compounds into ~${X}/mo of repeat {unit} value.",
        recommend_when={"state": "no_first_visit_followup", "min_signal": "transactions"},
        tags=("marketing", "lifecycle", v.family),
    )


def _high_value_unrecognized(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your top {X}% of customers get the same generic emails as everyone else",
        observation=f"The top {X}% of customers drive {X}% of {unit} revenue, yet receive identical mass campaigns with no VIP recognition or tier.",
        reasoning=f"High-value customers are the cheapest growth you have and the most expensive to lose; treating them like the cold list under-invests in the exact relationships that carry your revenue and invites a competitor to court them.",
        conclusion=f"Segment the top {X}% and give them early access, a recognition perk, or a personal {v.staff_role} touch distinct from the mass list.",
        expected_effect=f"A {X}pt retention gain on your top {X}% is worth ~${X}/mo given their outsized {unit} value.",
        recommend_when={"state": "vip_untiered", "min_signal": "transactions"},
        tags=("marketing", "vip", v.family),
    )


def _birthday_anniversary_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Birthday & anniversary triggers are sitting unused",
        observation=f"You hold contact records for {X} customers but fire zero date-triggered {unit} offers on birthdays or anniversaries.",
        reasoning=f"Date triggers are the highest-converting automated email type because they arrive with built-in intent and emotion; for a {v.name.lower()} a personally-timed offer feels like service, not marketing, so it converts where a blast wouldn't.",
        conclusion=f"Stand up an automated birthday/anniversary {unit} offer sent {X} days ahead, personalized to the customer's history.",
        expected_effect=f"A perennial date-trigger program on {X} contacts compounds to ~${X}/mo with near-zero ongoing effort.",
        recommend_when={"state": "date_triggers_untapped", "min_signal": "customer_profiles"},
        tags=("marketing", "lifecycle", "automation", v.family),
    )


# ═══════════════════════ EARNED: REVIEWS (NEW INGEST) ═══════════════════════
def _review_volume_low(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You collect almost no reviews — {X} in {X} months",
        observation=f"Only {X} new public reviews landed in the last {X} months despite serving {X} customers — a request rate near zero.",
        reasoning=f"For a {v.name.lower()}, review count is a primary ranking and trust signal: thin volume suppresses map/search visibility AND lets a single bad review dominate the average, so low volume is both a discovery problem and a reputation-fragility problem.",
        conclusion=f"Automate a post-{v.sale_unit} review request (SMS/email) timed {X} hours after a happy interaction, and ask only satisfied customers.",
        expected_effect=f"Raising volume to {X} reviews/month lifts local discovery and is worth ~${X}/mo in incremental walk-in/search demand.",
        recommend_when={"state": "review_volume_low", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "reviews", v.family),
    )


def _review_rating_declining(v: Vertical, situation: str) -> Built:
    extra = {
        "anomaly": " The drop is a sudden break from a stable history — treat it as an incident and find the root cause now.",
        "declining": " The slide has run for several periods — a process, not a one-off, is eroding the score.",
    }.get(situation, "")
    return Built(
        title=f"Your rating is sliding — {X} stars, down from {X}",
        observation=f"Trailing-90-day average rating has fallen to {X} from {X}, driven by {X} recent low-star reviews.{extra}",
        reasoning=f"A falling rating compounds: each tenth of a star lost cuts click-through from search/map results, so the decline silently shrinks top-of-funnel demand long before it shows up in {v.sale_unit} counts.",
        conclusion=f"Triage the {X} recent low-star themes, fix the top operational cause, and run a satisfied-customer request push to re-weight the average.",
        expected_effect=f"Recovering {X} tenths of a star restores discovery click-through worth ~${X}/mo.",
        recommend_when={"state": "rating_declining", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "reviews", v.family),
    )


def _review_response_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You reply to {X}% of reviews — owners' responses are missing",
        observation=f"{X}% of reviews (and {X}% of negative ones) have no owner response, including reviews older than {X} days.",
        reasoning=f"Public responses are read by prospects far more than by the original reviewer; an unanswered complaint signals an inattentive {v.name.lower()}, while a calm reply converts a negative into proof of care — so silence forfeits free reputation repair.",
        conclusion=f"Respond to every review within {X} hours using a brief, specific, non-defensive template — negatives first.",
        expected_effect=f"Consistent responses measurably lift conversion from your listing, worth ~${X}/mo at current traffic.",
        recommend_when={"state": "review_response_gap", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "reviews", v.family),
    )


def _review_keyword_theme(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"One complaint theme keeps recurring in your reviews",
        observation=f"{X}% of low-star reviews in the last {X} days mention the same theme (e.g. {X}), clustering well above any other issue.",
        reasoning=f"A repeated theme in review text is a free, unsolicited operational audit: it pinpoints the single fix that would prevent the most future negatives, which a star average alone hides because it averages distinct causes together.",
        conclusion=f"Treat the top recurring theme as a P1 operational fix, then watch whether its mention rate falls in the next {X} reviews.",
        expected_effect=f"Eliminating the dominant complaint theme protects ~${X}/mo of reputation-driven demand and reduces refund/comeback cost.",
        recommend_when={"state": "review_theme_cluster", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "voc", v.family),
    )


def _review_velocity_stalled(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your review flow stalled after an early burst",
        observation=f"Review velocity peaked at {X}/month around launch and has since fallen to {X}/month, while {v.sale_unit} volume held steady.",
        reasoning=f"Recency is weighted in local ranking: a stalled flow makes a {v.name.lower()} look dormant even when busy, so steady velocity matters as much as total count — a one-time burst decays in relevance.",
        conclusion=f"Re-instate a continuous post-{v.sale_unit} request so a steady {X}+ reviews/month land, rather than relying on the launch spike.",
        expected_effect=f"Restoring steady velocity defends ranking recency worth ~${X}/mo in sustained discovery.",
        recommend_when={"state": "review_velocity_stalled", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "reviews", v.family),
    )


def _competitor_review_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Nearby competitors out-review you {X} to 1",
        observation=f"Comparable {v.name.lower()}s within {X} km hold {X} reviews at {X} stars; you hold {X} at {X} — a visible gap on the same search result.",
        reasoning=f"Customers choose between you and the next pin on the map by review count and rating side-by-side; a thin profile next to a dense one loses the click before the {v.sale_unit} ever starts, regardless of who's actually better.",
        conclusion=f"Close the volume gap with a sustained request program and lead your listing with the {X} differentiators competitors lack.",
        expected_effect=f"Drawing even with local competitors on review density is worth ~${X}/mo in recaptured comparison clicks.",
        recommend_when={"state": "competitor_review_gap", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "competitive", v.family),
    )


# ═══════════════════════ EARNED: SOCIAL / UGC / LISTINGS ════════════════════
def _social_proof_missing_pos(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"No social proof at the point of {v.sale_unit}",
        observation=f"The checkout/{v.sale_unit} moment shows no rating, review snippet, or QR review prompt — the highest-satisfaction instant goes uncaptured.",
        reasoning=f"The moment right after a good {v.sale_unit} is peak goodwill; not surfacing proof there both wastes the easiest review-capture opportunity AND skips a low-cost reassurance that lifts attach and repeat intent at the till.",
        conclusion=f"Add a QR review prompt + a 'rated {X} stars by {X} locals' card at the {v.sale_unit} point and measure review capture rate.",
        expected_effect=f"Converting {X}% of {v.sale_unit}s into a review request compounds reputation worth ~${X}/mo.",
        recommend_when={"state": "no_pos_social_proof", "min_signal": "review_feed"},
        tags=("marketing", "reputation", "pos", v.family),
    )


def _ugc_not_captured(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Customers post about you — and you capture none of it",
        observation=f"Roughly {X} tagged mentions/photos appear monthly on social, but none are reshared, rights-cleared, or repurposed into marketing.",
        reasoning=f"User-generated content is free, trusted, high-converting creative; for a visual {v.name.lower()} category, leaving organic posts uncollected forfeits authentic proof that outperforms anything you'd produce in-house.",
        conclusion=f"Stand up a light UGC workflow: monitor tags, request reshare rights, and feature {X} customer posts/week across owned channels.",
        expected_effect=f"A steady UGC stream lifts social-driven discovery and trust worth ~${X}/mo at near-zero production cost.",
        recommend_when={"state": "ugc_uncaptured", "min_signal": "social_mentions"},
        tags=("marketing", "reputation", "ugc", v.family),
    )


def _listing_incomplete(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your business listing is incomplete where it costs you clicks",
        observation=f"Key listing fields are missing or stale ({X} of hours, photos, attributes, primary category), and there are {X} unanswered listing questions.",
        reasoning=f"The listing is most prospects' first and sometimes only impression of the {v.name.lower()}; missing photos/hours/category directly suppress ranking and conversion in local results, so incompleteness leaks demand upstream of everything else you do.",
        conclusion=f"Complete the profile (correct category, {X}+ fresh photos, accurate hours, attributes) and answer outstanding listing questions.",
        expected_effect=f"A fully optimized listing typically lifts local action rate worth ~${X}/mo in incremental {v.sale_unit}s.",
        recommend_when={"state": "listing_incomplete", "min_signal": "listing_profile"},
        tags=("marketing", "reputation", "local_seo", v.family),
    )


# ═══════════════════════ REFERRAL / LOYALTY / MEMBERSHIP ════════════════════
def _referral_program_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your happiest customers have no way to refer you",
        observation=f"You have {X} repeat customers and {X} five-star reviewers, but no referral mechanism — zero tracked word-of-mouth {unit}s.",
        reasoning=f"Repeat, high-rating customers are pre-qualified advocates; without a structured ask and reward, their goodwill produces only random word-of-mouth instead of a measurable, compounding {unit} channel that costs nothing until it works.",
        conclusion=f"Launch a give-{X}/get-{X} referral offer to your repeat segment and track referred {unit}s as their own cohort.",
        expected_effect=f"Even a {X}% referral rate on {X} advocates yields ~${X}/mo in low-cost new {unit}s.",
        recommend_when={"state": "referral_untapped", "min_signal": "transactions"},
        tags=("marketing", "referral", v.family),
    )


def _loyalty_signup_rate_low(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Only {X}% of customers join your loyalty program",
        observation=f"Loyalty enrolment runs at {X}% of {v.sale_unit}s — far below the {X}% achievable for a {v.family.replace('_',' ')} business with repeat traffic.",
        reasoning=f"Loyalty's value is the contactable, identified relationship it creates; a low signup rate means most {v.sale_unit}s stay anonymous, so you can't reactivate, segment, or attribute them — capping every downstream marketing lever.",
        conclusion=f"Move the ask to the {v.staff_role} at checkout with a first-{v.sale_unit} incentive and reduce signup to {X} taps.",
        expected_effect=f"Doubling enrolment to {X}% widens your addressable list and is worth ~${X}/mo in future targeted demand.",
        recommend_when={"state": "loyalty_signup_low", "min_signal": "loyalty_enrolments"},
        tags=("marketing", "loyalty", v.family),
    )


def _loyalty_inactive_members(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Most loyalty members are dormant",
        observation=f"{X}% of enrolled members haven't earned or redeemed in {X} days, and {X} carry an unredeemed-points balance.",
        reasoning=f"A loyalty base only pays back if it changes behavior; dormant members and a growing unredeemed-points liability mean the program is administrative overhead, not a demand engine, and the liability sits on the books unused.",
        conclusion=f"Trigger a points-expiry-warning + bonus-earn campaign to the dormant {X}% and measure reactivated {v.sale_unit}s.",
        expected_effect=f"Reactivating {X}% of dormant members is worth ~${X}/mo and draws down the points liability productively.",
        recommend_when={"state": "loyalty_dormant", "min_signal": "loyalty_enrolments"},
        tags=("marketing", "loyalty", v.family),
    )


def _membership_marketing_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your regulars would pay for membership — but you've never offered it",
        observation=f"{X} customers buy {X}+ {unit}s/month at full price, an ideal membership cohort, yet no recurring/membership offer is marketed to them.",
        reasoning=f"Converting predictable repeat buyers to a membership trades a small per-{unit} discount for guaranteed recurring revenue and a lock-in that blunts competitor switching — a margin-for-certainty trade that only your most frequent customers should be offered.",
        conclusion=f"Pilot a membership/recurring tier to the top {X} frequency cohort and track retention versus matched non-members.",
        expected_effect=f"Converting {X}% of frequent buyers to membership stabilizes ~${X}/mo of recurring revenue.",
        recommend_when={"state": "membership_untapped", "min_signal": "transactions"},
        tags=("marketing", "membership", v.family),
    )


# ═══════════════════════ OCCASION / SEASONAL / LOCAL ════════════════════════
def _occasion_campaign_missed(v: Vertical, situation: str) -> Built:
    occ = _occasion(v)
    unit = v.sale_unit
    extra = " The next occasion window is approaching — prep the campaign before it opens." if situation == "seasonal_peak" else ""
    return Built(
        title=f"You let your biggest {occ} occasion pass without a campaign",
        observation=f"{unit.title()} volume spikes ~{X}% around {occ}, but the last {X} occasions ran with no advance email, preorder push, or capacity prep.{extra}",
        reasoning=f"For a {v.name.lower()}, occasion demand is concentrated, high-intent, and predictable on the calendar; not marketing into a known spike forfeits the easiest revenue of the year AND risks under-capacity that sends ready buyers to a competitor.",
        conclusion=f"Build a {X}-week pre-occasion sequence (early-bird preorder, gift framing, deadline) and staff/stock to the expected {occ} spike.",
        expected_effect=f"Capturing the {occ} occasion deliberately is worth ~${X} per cycle in incremental {unit}s.",
        recommend_when={"state": "occasion_missed", "min_signal": "transactions"},
        tags=("marketing", "occasion", "seasonal", v.family),
    )


def _seasonal_preorder_missed(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The next preorder window is near — open it now to shape production." if situation == "seasonal_peak" else ""
    return Built(
        title=f"You don't open preorders ahead of your demand peaks",
        observation=f"Preorder share sits at {X}% of peak-period {unit}s; demand arrives same-day, forcing reactive {v.staff_role} production and {X}% waste/stockouts.{extra}",
        reasoning=f"Preorders convert uncertain demand into a production plan: for a perishable {v.name.lower()} they cut waste, lock margin, and smooth labor — so the absence of a preorder push is both a marketing miss and an operations cost.",
        conclusion=f"Promote a preorder deadline {X} days before each peak and reward early commitment with priority/pickup perks.",
        expected_effect=f"Lifting preorder share to {X}% cuts waste and captures peak demand worth ~${X} per cycle.",
        recommend_when={"state": "preorder_unmarketed", "min_signal": "transactions"},
        tags=("marketing", "preorder", "seasonal", v.family),
    )


def _local_event_tie_in(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Local events drive foot traffic past you — and you never tie in",
        observation=f"{X} sizable events happen within {X} km each month (games, festivals, markets), yet no offer, hours change, or campaign aligns to them.",
        reasoning=f"Local events create a temporary surge of nearby, in-the-mood foot traffic; a {v.name.lower()} that ignores the calendar leaves that surge to walk past, while a tied-in offer or extended hours converts proximity into {v.sale_unit}s at almost no acquisition cost.",
        conclusion=f"Maintain a local-event calendar and pre-stage an offer + matching hours/staffing for the {X} highest-traffic events.",
        expected_effect=f"Tying into even {X} events/month is worth ~${X}/mo in event-driven {v.sale_unit}s.",
        recommend_when={"state": "local_event_untapped", "min_signal": "local_events"},
        tags=("marketing", "local", "demand_shaping", v.family),
    )


# ═══════════════════════ ONLINE FUNNEL ══════════════════════════════════════
def _abandoned_online_cart(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Online carts are abandoned with no recovery",
        observation=f"{X}% of online {unit} carts are abandoned before payment, and zero recovery email/SMS is sent afterward.",
        reasoning=f"An abandoned cart is the highest-intent signal you ever get — the customer chose the {unit} and stopped at friction or hesitation; without a recovery touch you discard demand that's one nudge from converting.",
        conclusion=f"Fire a {X}-step cart-recovery sequence within {X} hours and instrument WHERE in checkout the drop happens to remove the friction.",
        expected_effect=f"Recovering {X}% of abandoned carts is worth ~${X}/mo in online {unit}s on existing traffic.",
        recommend_when={"state": "cart_abandon_no_recovery", "min_signal": "online_orders"},
        tags=("marketing", "online", "funnel", v.family),
    )


# ─────────────────────────── REGISTER ───────────────────────────────────────
register(
    # Owned: email (existing log → FULL)
    Archetype(
        key="email_open_click_gap", domain="marketing", name="High open / low click",
        build=_email_open_click_gap, situations=("baseline",),
        required_signals=("email_send_log",),
        required_agents=("EmailAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="email_list_underused", domain="marketing", name="List under-mailed",
        build=_email_list_underused, situations=("baseline", "untapped"),
        required_signals=("email_send_log",),
        required_agents=("EmailAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="email_bounce_decay", domain="marketing", name="List decay / bounces",
        build=_email_bounce_decay, situations=("baseline", "leaking"),
        required_signals=("email_send_log",),
        required_agents=("EmailAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    # Owned: promo economics
    Archetype(
        key="promo_roi_negative", domain="marketing", name="Promo loses margin",
        build=_promo_roi_negative, situations=("baseline", "leaking"),
        required_signals=("email_send_log", "transactions"),
        required_agents=("EmailAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PromoMarginAgent: join redemption events in email_send_log to per-line margin in transactions to compute incremental (non-cannibalizing) contribution per campaign.",
    ),
    Archetype(
        key="winback_discount_too_generous", domain="marketing", name="Win-back too deep",
        build=_winback_discount_too_generous, situations=("baseline",),
        required_signals=("email_send_log", "transactions"),
        required_agents=("EmailAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PromoMarginAgent (shared): pair win-back redemption with subsequent full-price second-visit rate to value win-back depth against reactivated LTV.",
    ),
    Archetype(
        key="offpeak_promo_untapped", domain="marketing", name="Slow window unmarketed",
        build=_offpeak_promo_untapped, situations=("baseline",),
        required_signals=("hourly_revenue", "email_send_log"),
        required_agents=("PatternAnalyzer", "EmailAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PromoTimingAgent: cross hourly_revenue troughs with campaign send timing to detect demand windows never targeted by marketing.",
    ),
    # Lifecycle (email + txn fusion)
    Archetype(
        key="reactivation_opportunity", domain="marketing", name="Lapsed-regular reactivation",
        build=_reactivation_opportunity, situations=("baseline", "leaking", "untapped"),
        required_signals=("transactions", "email_send_log"),
        required_agents=("RevenueAnalyzer", "EmailAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CustomerLifecycleAgent: build per-customer recency/frequency from transactions (needs stable customer_id) and join to email_send_log to find lapsed-but-reachable segments.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership", "high_ticket"),
    ),
    Archetype(
        key="new_customer_no_followup", domain="marketing", name="No first-visit follow-up",
        build=_new_customer_no_followup, situations=("baseline",),
        required_signals=("transactions", "email_send_log"),
        required_agents=("RevenueAnalyzer", "EmailAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CustomerLifecycleAgent (shared): flag first-time customers lacking a follow-up touch inside the second-visit window.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership"),
    ),
    Archetype(
        key="high_value_unrecognized", domain="marketing", name="VIPs untiered",
        build=_high_value_unrecognized, situations=("baseline", "concentrated"),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CustomerLifecycleAgent (shared): rank customers by trailing spend to surface a top-decile VIP segment for differentiated treatment.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership", "high_ticket"),
    ),
    Archetype(
        key="birthday_anniversary_untapped", domain="marketing", name="Date triggers unused",
        build=_birthday_anniversary_untapped, situations=("baseline",),
        required_signals=("customer_profiles", "email_send_log"),
        required_agents=("CustomerLifecycleAgent", "EmailAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CustomerLifecycleAgent: ingest customer DOB/anniversary fields (not yet captured at POS/booking) and emit date-triggered campaign opportunities.",
        applies_keys=_keys_with_any_flag("high_ticket", "membership", "repeat_purchase"),
    ),
    # Earned: reviews (NEW ingest → MISSING)
    Archetype(
        key="review_volume_low", domain="marketing", name="Low review volume",
        build=_review_volume_low, situations=("baseline",),
        required_signals=("review_feed", "transactions"),
        required_agents=("ReviewIngestAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewIngestAgent: pull public reviews (Google/Yelp/Facebook) into a review_feed source — no review data is ingested today; compute volume/velocity vs served-customer count.",
        exclude_keys=("ghost_kitchen",),
    ),
    Archetype(
        key="review_rating_declining", domain="marketing", name="Rating sliding",
        build=_review_rating_declining, situations=("declining", "anomaly"),
        required_signals=("review_feed",),
        required_agents=("ReviewIngestAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewIngestAgent (shared): track trailing-window average rating and detect declines/anomalies against the merchant's own history.",
        exclude_keys=("ghost_kitchen",),
    ),
    Archetype(
        key="review_response_gap", domain="marketing", name="Reviews unanswered",
        build=_review_response_gap, situations=("baseline",),
        required_signals=("review_feed",),
        required_agents=("ReputationAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationAgent: read review_feed (from ReviewIngestAgent) to flag unanswered reviews and draft response copy — depends on review ingest existing first.",
    ),
    Archetype(
        key="review_keyword_theme", domain="marketing", name="Recurring complaint theme",
        build=_review_keyword_theme, situations=("baseline",),
        required_signals=("review_feed",),
        required_agents=("ReputationAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationAgent (shared): run topic/sentiment clustering over review_feed text to surface the dominant recurring complaint theme.",
        exclude_keys=("ghost_kitchen",),
    ),
    Archetype(
        key="review_velocity_stalled", domain="marketing", name="Review velocity stalled",
        build=_review_velocity_stalled, situations=("baseline", "declining"),
        required_signals=("review_feed", "transactions"),
        required_agents=("ReviewIngestAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewIngestAgent (shared): compute review arrival rate over time and compare to transaction volume to detect a stalled flow.",
        exclude_keys=("ghost_kitchen",),
    ),
    Archetype(
        key="competitor_review_gap", domain="marketing", name="Out-reviewed by competitors",
        build=_competitor_review_gap, situations=("baseline",),
        required_signals=("review_feed", "competitor_listings"),
        required_agents=("ReputationAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationAgent + CompetitorWatchAgent: pull nearby same-category listings' review count/rating to benchmark the merchant's profile density on the local SERP.",
        exclude_keys=("ghost_kitchen",),
    ),
    # Earned: social / UGC / listings (NEW ingest → MISSING)
    Archetype(
        key="social_proof_missing_pos", domain="marketing", name="No social proof at POS",
        build=_social_proof_missing_pos, situations=("baseline",),
        required_signals=("review_feed",),
        required_agents=("ReputationAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationAgent (shared): surface rating/review snippets back to the POS/checkout surface and capture post-sale review requests.",
        applies_keys=_keys_with_channel("walk_in"),
    ),
    Archetype(
        key="ugc_not_captured", domain="marketing", name="UGC uncaptured",
        build=_ugc_not_captured, situations=("baseline",),
        required_signals=("social_mentions",),
        required_agents=("ReputationAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationAgent (social listening): ingest tagged social mentions/photos (social_mentions source does not exist yet) to detect and repurpose UGC.",
    ),
    Archetype(
        key="listing_incomplete", domain="marketing", name="Listing incomplete",
        build=_listing_incomplete, situations=("baseline",),
        required_signals=("listing_profile",),
        required_agents=("ReputationAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationAgent (listings): read the business listing profile (Google Business Profile API; not yet connected) to score completeness and unanswered questions.",
        applies_keys=_keys_with_channel("walk_in"),
    ),
    # Referral / loyalty / membership
    Archetype(
        key="referral_program_untapped", domain="marketing", name="No referral mechanism",
        build=_referral_program_untapped, situations=("baseline", "untapped"),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "ReferralAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReferralAgent: stand up referral tracking (give/get codes, referred-cohort attribution) — no referral data model exists today; identify advocate segment from repeat + 5-star signals.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership", "high_ticket"),
    ),
    Archetype(
        key="loyalty_signup_rate_low", domain="marketing", name="Low loyalty enrolment",
        build=_loyalty_signup_rate_low, situations=("baseline",),
        required_signals=("loyalty_enrolments", "transactions"),
        required_agents=("LoyaltyAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LoyaltyAgent: read loyalty enrolment events (partially available per POS) and compute signup rate vs transactions; standardize enrolment ingest across POS providers.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership"),
    ),
    Archetype(
        key="loyalty_inactive_members", domain="marketing", name="Dormant loyalty base",
        build=_loyalty_inactive_members, situations=("baseline",),
        required_signals=("loyalty_enrolments", "transactions"),
        required_agents=("LoyaltyAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LoyaltyAgent (shared): track per-member earn/redeem recency and unredeemed-point liability to surface a dormant segment for reactivation.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership"),
    ),
    Archetype(
        key="membership_marketing_untapped", domain="marketing", name="Membership unoffered",
        build=_membership_marketing_untapped, situations=("baseline", "untapped"),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "MembershipAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MembershipAgent: identify high-frequency full-price cohorts from transactions and model a recurring/membership tier; no membership-conversion modeling exists today.",
        applies_keys=_keys_with_any_flag("repeat_purchase", "membership"),
    ),
    # Occasion / seasonal / local
    Archetype(
        key="occasion_campaign_missed", domain="marketing", name="Occasion campaign missed",
        build=_occasion_campaign_missed, situations=("baseline", "seasonal_peak"),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "OccasionCalendarAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="OccasionCalendarAgent: map calendar occasions to the merchant's historical demand spikes and flag occasions that ran with no advance campaign.",
        applies_flags=("seasonal",),
        applies_keys=("florist", "jewelry", "event_venue", "full_restaurant", "spa", "med_spa"),
    ),
    Archetype(
        key="seasonal_preorder_missed", domain="marketing", name="Preorder window unmarketed",
        build=_seasonal_preorder_missed, situations=("baseline", "seasonal_peak"),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "OccasionCalendarAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="OccasionCalendarAgent (shared): detect peak periods with low preorder share to recommend a preorder-deadline push that shapes production.",
        applies_keys=("bakery", "florist"),
    ),
    Archetype(
        key="local_event_tie_in", domain="marketing", name="Local events untapped",
        build=_local_event_tie_in, situations=("baseline",),
        required_signals=("local_events", "transactions"),
        required_agents=("LocalEventAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocalEventAgent: ingest nearby event calendars (sports/festivals/markets via a geo events feed; not connected) and correlate to foot-traffic lift to recommend tie-ins.",
        applies_keys=_keys_with_channel("walk_in"),
    ),
    # Online funnel
    Archetype(
        key="abandoned_online_cart", domain="marketing", name="Cart abandonment unrecovered",
        build=_abandoned_online_cart, situations=("baseline",),
        required_signals=("online_orders", "email_send_log"),
        required_agents=("OnlineFunnelAgent", "EmailAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="OnlineFunnelAgent: capture online checkout funnel/cart-abandon events (online store webhooks not yet ingested) and trigger recovery sequences.",
        applies_keys=_keys_with_channel("online"),
    ),
)
