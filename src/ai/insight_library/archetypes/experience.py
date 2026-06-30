"""
Domain: EXPERIENCE / SERVICE QUALITY.

Each archetype is a distinct reasoning pattern about a driver of SERVICE QUALITY
and SATISFACTION that moves retention or revenue — wait, accuracy, rework, speed,
consistency, recognition, recovery, friction. This domain is framed around how the
experience FELT and what it cost in repeat business, NOT staffing levels (labor)
or raw demand timing (footfall/timing) or the bookable resource (capacity).

Most experience signals don't exist in today's POS feed (review text, complaint
themes, accuracy/rework flags, per-stage service timing), so many archetypes are
PARTIAL/MISSING and spec concrete upgrade agents — ExperienceSignalAgent,
ReviewThemeAgent, ReworkLedgerAgent, ServiceTimingAgent — to produce them.
Specialization per vertical changes the felt failure mode so a salon redo, an
auto comeback, and a restaurant walkout are genuinely different reasoning.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


def _wait_walkout(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    extra = {
        "declining": " Waits that customers used to tolerate have crept past their limit as volume grew.",
        "anomaly": " A sudden wait spike on {x} broke the norm — find the cause before it costs repeats.".replace("{x}", X),
    }.get(situation, "")
    return Built(
        title=f"Long waits at your {X} peak are driving {X} walkouts/week",
        observation=f"Wait time hits {X} minutes during the {X} rush, and {X}% of arriving customers leave before being served.",
        reasoning=f"Past a tolerance threshold, wait converts directly into abandoned {sale}s AND a worse memory of the visit — so it costs the immediate sale and the repeat one.{extra}",
        conclusion=f"Attack the {X} bottleneck (express path, pre-order, queue triage) before the wait crosses the walkout threshold.",
        expected_effect=f"Cutting peak wait below the walkout line recovers ~${X}/mo in abandoned {sale}s.",
        recommend_when={"state": "wait_drives_walkout", "min_signal": "service_timing"},
        tags=("experience", "wait", v.family),
    )


def _order_accuracy(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Order-accuracy errors are quietly costing repeat {sale}s",
        observation=f"{X}% of {sale}s are remade or corrected, concentrated on {X} and the {X} menu/service items.",
        reasoning=f"Every wrong {sale} burns food/labor twice and, worse, a first-time customer who gets it wrong rarely returns — accuracy is a retention lever disguised as a cost line.",
        conclusion=f"Tighten the build/confirm step on the {X} error-prone items and add a final check during the {X} rush.",
        expected_effect=f"Halving the error rate saves rework and protects ~${X}/mo in at-risk repeat {sale}s.",
        recommend_when={"state": "order_accuracy_rework", "min_signal": "rework_log"},
        tags=("experience", "accuracy", v.family),
    )


def _comeback_redo(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    role = v.staff_role
    return Built(
        title=f"Your redo/comeback rate is eroding margin and trust",
        observation=f"{X}% of {sale}s come back for a redo within {X} days, clustered on {X} work and a few {role}s.",
        reasoning=f"A comeback is unpaid rework that ties up a {role} and a slot you could have sold — and the customer's confidence drops with every redo, which is the real retention cost.",
        conclusion=f"Root-cause the {X} comeback driver (technique, materials, or expectation-setting) and coach the {role}s it concentrates on.",
        expected_effect=f"Cutting comebacks recovers ~${X}/mo in lost capacity plus the retention it protects.",
        recommend_when={"state": "comeback_redo_rate", "min_signal": "rework_log"},
        tags=("experience", "rework", v.family),
    )


def _speed_slipping(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Speed of service is slipping — {X}% slower than your {X} baseline",
        observation=f"Average service time has crept to {X} minutes per {sale}, up {X}% over {X} weeks, with no volume increase to explain it.",
        reasoning=f"Slow drift without a demand change signals process erosion, not load; left unchecked it both lowers throughput and degrades the experience customers grade you on.",
        conclusion=f"Audit the {X} step where time is leaking and reset the standard before the slip becomes the new normal.",
        expected_effect=f"Restoring baseline speed recovers throughput and protects ~${X}/mo in experience-driven repeats.",
        recommend_when={"state": "speed_of_service_slipping", "min_signal": "service_timing"},
        tags=("experience", "speed", v.family),
    )


def _first_visit_resolution(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"First-visit resolution is low — too many {sale}s need a return trip",
        observation=f"{X}% of {sale}s aren't fully resolved on the first visit, requiring a follow-up for {X} reasons.",
        reasoning=f"A second trip to finish the same job costs the customer time they didn't budget — first-visit resolution is one of the strongest predictors of whether they come back at all.",
        conclusion=f"Equip the first visit to close the {X} most common follow-up causes (parts on hand, scope upfront, right diagnostics).",
        expected_effect=f"Lifting first-visit resolution protects ~${X}/mo in retention and frees return-trip capacity.",
        recommend_when={"state": "first_visit_resolution_low", "min_signal": "rework_log"},
        tags=("experience", "resolution", v.family),
    )


def _complaint_cluster(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"One complaint theme dominates — '{X}' shows up in {X}% of gripes",
        observation=f"Across complaints and feedback, the '{X}' theme accounts for {X}% of all negative mentions, far ahead of the next.",
        reasoning=f"A single dominant complaint theme is a fixable systemic cause, not random noise — and because it recurs, it's silently shaping the word-of-mouth and reviews that gate new {v.sale_unit}s.",
        conclusion=f"Fix the root cause behind the '{X}' theme first; it clears the largest share of dissatisfaction per unit of effort.",
        expected_effect=f"Resolving the dominant theme lifts satisfaction broadly and protects ~${X}/mo in reputation-driven demand.",
        recommend_when={"state": "complaint_theme_cluster", "min_signal": "complaint_log"},
        tags=("experience", "complaints", v.family),
    )


def _negative_review_theme(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your review rating is being dragged by one service theme",
        observation=f"Reviews average {X} stars, and {X}% of the sub-4-star ones cite the same '{X}' service issue.",
        reasoning=f"Prospective customers read the recent negative reviews before booking, so a recurring service theme in them suppresses conversion well beyond the customers who actually experienced it.",
        conclusion=f"Close the '{X}' service gap, then ask satisfied recent customers for reviews to re-weight the public picture.",
        expected_effect=f"Lifting the rating off the {X}-theme drag is worth ~${X}/mo in review-gated new {v.sale_unit}s.",
        recommend_when={"state": "negative_review_theme", "min_signal": "reviews_text"},
        tags=("experience", "reviews", v.family),
    )


def _cleanliness_ambiance(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Cleanliness/ambiance is showing up as a satisfaction drag",
        observation=f"{X}% of feedback mentions cleanliness or ambiance negatively, rising on {X} after peak.",
        reasoning=f"Environment is a baseline expectation — customers rarely praise it but reliably punish its absence, and the dip after peak shows it's a reset-cadence problem, not a one-off.",
        conclusion=f"Add a mid-shift reset on {X} after the rush so the environment never degrades below the expected bar.",
        expected_effect=f"Holding the environment standard protects ~${X}/mo in repeat {v.sale_unit}s sensitive to it.",
        recommend_when={"state": "cleanliness_ambiance_signal", "min_signal": "reviews_text"},
        tags=("experience", "environment", v.family),
    )


def _greeting_gap(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Customers go unacknowledged during your {X} peak",
        observation=f"At peak, {X}% of arriving customers wait {X}+ seconds with no greeting or acknowledgement.",
        reasoning=f"The first few seconds set the tone; an unacknowledged arrival at peak raises perceived wait and walkout risk even when actual service time is fine — it's a cheap fix with outsized felt impact.",
        conclusion=f"Add a simple acknowledge-on-arrival step (eye contact, 'be right with you') during the {X} window.",
        expected_effect=f"Acknowledgement at peak reduces walkouts and protects ~${X}/mo in first-impression-driven {sale}s.",
        recommend_when={"state": "greeting_gap_at_peak", "min_signal": "service_observation"},
        tags=("experience", "greeting", v.family),
    )


def _followup_missing(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"No post-service follow-up — you never close the loop after a {sale}",
        observation=f"{X}% of customers get no follow-up after their {sale}, including the {X}% whose visit had a hiccup.",
        reasoning=f"A short follow-up surfaces silent dissatisfaction before it becomes a bad review or a quiet churn, and signals care that drives rebooking — the absence of it leaves both upside and risk untouched.",
        conclusion=f"Trigger an automated post-{sale} check-in, prioritizing visits flagged with any service issue.",
        expected_effect=f"Closing the loop recovers at-risk customers worth ~${X}/mo and lifts review volume.",
        recommend_when={"state": "post_service_followup_missing", "min_signal": "contact_log"},
        tags=("experience", "followup", v.family),
    )


def _recovery_after_bad(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A bad experience almost always means a lost customer — no recovery play",
        observation=f"Customers with a flagged bad visit return at {X}% versus {X}% baseline, and {X}% get no recovery outreach.",
        reasoning=f"Service recovery is the highest-leverage retention moment — a well-handled fix often makes a customer more loyal than if nothing went wrong — yet without a trigger the bad experience just ends the relationship silently.",
        conclusion=f"Auto-flag bad visits and trigger a same-week recovery gesture (apology + make-good) before the customer churns.",
        expected_effect=f"Recovering even a third of flagged-bad customers is worth ~${X}/mo in retained value.",
        recommend_when={"state": "loyalty_after_bad_experience", "min_signal": "experience_flag"},
        tags=("experience", "recovery", v.family),
    )


def _consistency_across_staff(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    sale = v.sale_unit
    return Built(
        title=f"Experience quality swings too much between {role}s",
        observation=f"Satisfaction/repeat rate ranges from {X}% to {X}% across {role}s for the same {sale} type.",
        reasoning=f"Wide variance means the experience is person-dependent, not systematized — a customer's outcome is a coin flip on who serves them, which makes the brand promise unreliable and caps retention.",
        conclusion=f"Codify what the top {role}s do into a standard and coach the bottom of the range up to it.",
        expected_effect=f"Compressing the variance lifts the average experience and protects ~${X}/mo in repeat {sale}s.",
        recommend_when={"state": "consistency_variance_staff", "min_signal": "experience_flag"},
        tags=("experience", "consistency", v.family),
    )


def _consistency_across_dayparts(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Your {X} daypart delivers a worse experience than the rest",
        observation=f"Satisfaction/accuracy on {X} runs {X}% below your other dayparts for the same {sale}.",
        reasoning=f"A daypart-specific quality dip means the experience isn't consistent across the day — customers who only ever visit then form a worse impression than your average suggests, and you don't see it in blended numbers.",
        conclusion=f"Diagnose the {X} daypart gap (handoff, fatigue, prep state) and bring it up to the standard the rest of the day already hits.",
        expected_effect=f"Leveling the weak daypart protects ~${X}/mo in repeats from those visitors.",
        recommend_when={"state": "consistency_variance_daypart", "min_signal": "experience_flag"},
        tags=("experience", "consistency", v.family),
    )


def _upsell_pushy(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Upselling has tipped into pushy and is denting the experience",
        observation=f"Attach attempts run {X} per visit and feedback citing 'pushy/pressured' has risen to {X}% on {X}.",
        reasoning=f"Past a point, attach effort stops adding revenue and starts subtracting trust — over-attaching trades a small one-time gain for a worse experience and lower return intent.",
        conclusion=f"Cap attach attempts and retrain toward relevant, single-offer suggestions instead of volume pressure.",
        expected_effect=f"Dialing back over-attach protects ~${X}/mo in retention without losing genuine attach revenue.",
        recommend_when={"state": "upsell_over_attach", "min_signal": "reviews_text"},
        tags=("experience", "attach", v.family),
    )


def _checkout_friction(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Checkout/payment friction is the sour note at the end of the visit",
        observation=f"{X}% of feedback cites slow or confusing checkout, and the payment step averages {X} extra minutes on {X}.",
        reasoning=f"The last moment of the visit weighs heavily on the overall memory — friction at checkout undoes an otherwise good experience and is among the easiest things to fix.",
        conclusion=f"Streamline the {X} payment path (pre-auth, tap, at-{v.staff_role} settle) to remove the end-of-visit drag.",
        expected_effect=f"Smoothing checkout protects ~${X}/mo in experience-driven repeat {sale}s.",
        recommend_when={"state": "checkout_friction", "min_signal": "service_timing"},
        tags=("experience", "checkout", v.family),
    )


def _wait_seating_accessibility(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Nowhere comfortable to wait makes your {X} peak feel worse than it is",
        observation=f"At peak {X} customers wait with inadequate seating/accessibility, and feedback flags the wait environment {X}% of the time.",
        reasoning=f"Perceived wait, not just actual wait, drives dissatisfaction — an uncomfortable or inaccessible wait makes the same minutes feel longer and disproportionately hurts customers with accessibility needs.",
        conclusion=f"Improve the {X} peak wait environment (seating, shade/warmth, clear accessibility) to soften perceived wait.",
        expected_effect=f"Better wait experience reduces walkouts and protects ~${X}/mo in peak {v.sale_unit}s.",
        recommend_when={"state": "wait_environment_gap", "min_signal": "service_observation"},
        tags=("experience", "wait", "accessibility", v.family),
    )


def _packaging_presentation(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Packaging/presentation is underwhelming for what you charge",
        observation=f"{X}% of feedback (esp. on {v.channels[-1]} {sale}s) cites packaging or presentation falling short of price.",
        reasoning=f"Presentation is the tangible proof of quality a customer takes away — when it lags the price point, it undercuts perceived value and the photos/word-of-mouth that drive new {sale}s.",
        conclusion=f"Upgrade packaging/presentation on the {X} highest-value or most-shared {sale}s where the gap is widest.",
        expected_effect=f"Closing the presentation gap protects ~${X}/mo in perceived-value-driven repeats and referrals.",
        recommend_when={"state": "packaging_presentation_gap", "min_signal": "reviews_text"},
        tags=("experience", "presentation", v.family),
    )


def _special_request_handling(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Special requests get mishandled — a high-stakes experience moment",
        observation=f"{X}% of {sale}s involve a special request (allergy, custom, accommodation) and {X}% of those generate a complaint.",
        reasoning=f"Special requests are exactly the moments customers remember and tell others about — getting them wrong (especially safety/allergy ones) does outsized reputational and, where regulated, liability damage.",
        conclusion=f"Standardize how special requests are captured and confirmed end-to-end for the {X} highest-stakes types.",
        expected_effect=f"Reliable special-request handling protects ~${X}/mo and removes a tail risk.",
        recommend_when={"state": "special_request_handling", "min_signal": "complaint_log"},
        tags=("experience", "special_request", v.family),
    )


def _returning_recognition(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Your regulars aren't being recognized as regulars",
        observation=f"{X}% of {sale}s are from repeat customers, yet there's no cue to recognize them at the {v.staff_role} or remember their preferences.",
        reasoning=f"Recognition is the cheapest loyalty lever there is — a returning customer treated like a stranger loses the relationship premium that made them valuable, while a remembered preference deepens it.",
        conclusion=f"Surface a returning-customer cue and last-visit preference at point of service so regulars feel known.",
        expected_effect=f"Recognizing regulars lifts repeat frequency and is worth ~${X}/mo in deepened loyalty.",
        recommend_when={"state": "returning_customer_recognition", "min_signal": "transactions"},
        tags=("experience", "recognition", v.family),
    )


def _review_response_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You're leaving reviews unanswered — a public experience signal",
        observation=f"{X}% of reviews go without a response, including {X}% of the negative ones, over the last {X} weeks.",
        reasoning=f"Prospective customers read how a business responds to feedback as a proxy for how it will treat them — unanswered negatives read as not caring, while thoughtful replies recover trust publicly at near-zero cost.",
        conclusion=f"Respond to every review within {X} days, leading with the negatives and naming the specific fix.",
        expected_effect=f"Active review response lifts conversion of review-readers, worth ~${X}/mo in new {v.sale_unit}s.",
        recommend_when={"state": "review_response_gap", "min_signal": "reviews_text"},
        tags=("experience", "reviews", v.family),
    )


def _feedback_capture_missing(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"You can't see your experience — no feedback is captured at all",
        observation=f"There's no systematic feedback step after a {sale}; you learn of problems only when a customer churns or posts a public review.",
        reasoning=f"Without a capture mechanism, dissatisfaction is invisible until it's already cost you the customer or the rating — you're flying blind on the single biggest driver of repeat business.",
        conclusion=f"Add a one-tap post-{sale} feedback prompt so issues surface privately and early, before they become churn or a bad review.",
        expected_effect=f"Just seeing the signal lets you recover at-risk customers worth ~${X}/mo that today leave silently.",
        recommend_when={"state": "feedback_capture_missing", "min_signal": "experience_flag"},
        tags=("experience", "measurement", v.family),
    )


def _complaint_resolution_slow(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Complaints sit too long before anyone resolves them",
        observation=f"Time-to-resolve a complaint averages {X} days, and {X}% never get a documented resolution at all.",
        reasoning=f"Resolution speed, not just outcome, drives whether an upset customer stays — a fast fix can rescue loyalty, while a slow or absent one converts a recoverable complaint into a lost customer and a public review.",
        conclusion=f"Set a {X}-hour first-response SLA on complaints and route the {X} most common types to an owner who can close them.",
        expected_effect=f"Resolving complaints fast recovers ~${X}/mo in otherwise-lost relationships.",
        recommend_when={"state": "complaint_resolution_slow", "min_signal": "complaint_log"},
        tags=("experience", "complaints", v.family),
    )


def _first_visit_onboarding(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"First-timers get a worse, more confusing experience than your regulars",
        observation=f"First-visit customers return at {X}% versus {X}% for second-visit, and their feedback skews toward confusion about {X}.",
        reasoning=f"The first visit is where the relationship is won or lost — when newcomers have to figure out the process regulars already know, their experience suffers exactly when retention is most fragile.",
        conclusion=f"Build a light first-visit onboarding (orient, explain the {X}, set next-step) so a newcomer's first {sale} feels as smooth as a regular's.",
        expected_effect=f"Lifting first-visit return rate is worth ~${X}/mo in customers who currently never come back.",
        recommend_when={"state": "first_visit_onboarding_gap", "min_signal": "transactions"},
        tags=("experience", "onboarding", v.family),
    )


def _handoff_continuity(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    role = v.staff_role
    return Built(
        title=f"Context gets dropped when a {sale} is handed between {role}s",
        observation=f"{X}% of multi-touch {sale}s involve a handoff, and {X}% of complaints trace to information lost across it (repeated questions, missed notes).",
        reasoning=f"Every handoff is a chance to drop the customer's context, forcing them to re-explain and signaling disorganization — continuity, not effort, is what makes a multi-step experience feel seamless.",
        conclusion=f"Standardize a handoff note (preferences, history, where things stand) so the next {role} continues without the customer repeating themselves.",
        expected_effect=f"Closing the handoff gap protects ~${X}/mo in experience-driven repeats on multi-touch {sale}s.",
        recommend_when={"state": "handoff_continuity_gap", "min_signal": "experience_flag"},
        tags=("experience", "continuity", v.family),
    )


def _expectation_setting_gap(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Mismatched expectations drive disappointment that isn't your service's fault",
        observation=f"{X}% of negative feedback stems from a gap between what was expected and delivered (timing, scope, or price) rather than execution.",
        reasoning=f"When the experience was fine but unmet expectations make it feel bad, the lever is communication, not the service — setting accurate expectations upfront converts would-be complaints into satisfied {sale}s.",
        conclusion=f"Set explicit expectations at the {X} points that drive the gap (lead time, scope, final price) before the {sale} begins.",
        expected_effect=f"Closing the expectation gap removes avoidable dissatisfaction worth ~${X}/mo in retention.",
        recommend_when={"state": "expectation_setting_gap", "min_signal": "complaint_log"},
        tags=("experience", "expectations", v.family),
    )


register(
    Archetype(
        key="wait_time_drives_walkout", domain="experience", name="Wait drives walkout",
        build=_wait_walkout, situations=("baseline", "declining", "anomaly"),
        applies_flags=("walk_in_heavy",),
        required_signals=("service_timing", "vision_traffic"),
        required_agents=("ServiceTimingAgent", "TrafficAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ServiceTimingAgent: capture queue/wait duration and balk events (timer or vision dwell) to tie wait length to walkout — wait timing not in POS.",
    ),
    Archetype(
        key="order_accuracy_rework", domain="experience", name="Order accuracy / rework",
        build=_order_accuracy, situations=("baseline", "leaking"),
        applies_keys=("cafe", "qsr", "full_restaurant", "bar", "food_truck", "bakery",
                      "ghost_kitchen", "florist", "hotel_fb"),
        required_signals=("rework_log",),
        required_agents=("ReworkLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReworkLedgerAgent: capture voids/remakes/corrections (from POS void reasons or KDS recall events) and theme them by item/daypart — rework events not yet ingested.",
    ),
    Archetype(
        key="comeback_redo_rate", domain="experience", name="Redo / comeback rate",
        build=_comeback_redo, situations=("baseline", "concentrated"),
        applies_keys=("salon", "barbershop", "nail_salon", "auto_repair", "oil_change",
                      "tire_shop", "tattoo", "hvac", "plumbing", "cleaning", "med_spa"),
        required_signals=("rework_log",),
        required_agents=("ReworkLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReworkLedgerAgent (shared): detect same-customer return-for-redo within a window, attributed to original worker/job type (needs job linkage + comeback flag).",
    ),
    Archetype(
        key="speed_of_service_slipping", domain="experience", name="Speed of service slipping",
        build=_speed_slipping, situations=("baseline", "declining"),
        required_signals=("service_timing",),
        required_agents=("ServiceTimingAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ServiceTimingAgent (shared): trend per-stage service duration over time, controlling for volume, to detect process drift vs load.",
    ),
    Archetype(
        key="first_visit_resolution", domain="experience", name="First-visit resolution",
        build=_first_visit_resolution, situations=("baseline",),
        applies_keys=("auto_repair", "hvac", "plumbing", "dental", "chiro", "physio",
                      "optometry", "vet", "tire_shop", "med_spa"),
        required_signals=("rework_log",),
        required_agents=("ReworkLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReworkLedgerAgent (shared): flag jobs needing a follow-up visit to complete the same scope, themed by cause (parts/diagnosis/scope).",
    ),
    Archetype(
        key="complaint_theme_cluster", domain="experience", name="Dominant complaint theme",
        build=_complaint_cluster, situations=("baseline", "anomaly"),
        required_signals=("complaint_log",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent: ingest and theme-cluster complaints/feedback (free-text source not yet connected) to rank dominant dissatisfaction drivers.",
    ),
    Archetype(
        key="negative_review_theme", domain="experience", name="Negative review theme",
        build=_negative_review_theme, situations=("baseline", "declining"),
        required_signals=("reviews_text",),
        required_agents=("ReviewThemeAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewThemeAgent: pull public review text + ratings and extract recurring service themes in sub-4-star reviews — review ingestion not yet wired.",
    ),
    Archetype(
        key="cleanliness_ambiance_signal", domain="experience", name="Cleanliness / ambiance",
        build=_cleanliness_ambiance, situations=("baseline",),
        applies_families=("food_service", "personal_care", "health_wellness", "fitness",
                          "retail", "hospitality"),
        required_signals=("reviews_text",),
        required_agents=("ReviewThemeAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewThemeAgent (shared): isolate cleanliness/ambiance mentions and correlate to daypart/post-peak timing.",
    ),
    Archetype(
        key="greeting_acknowledgement_gap", domain="experience", name="Greeting gap at peak",
        build=_greeting_gap, situations=("baseline",),
        applies_flags=("walk_in_heavy",),
        required_signals=("service_observation", "vision_traffic"),
        required_agents=("ExperienceSignalAgent", "TrafficAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): detect acknowledge-on-arrival latency from greeter/vision dwell or mystery-shopper input — not currently observed.",
    ),
    Archetype(
        key="post_service_followup_missing", domain="experience", name="No post-service follow-up",
        build=_followup_missing, situations=("baseline", "untapped"),
        applies_flags=("repeat_purchase",),
        required_signals=("contact_log", "transactions"),
        required_agents=("FollowUpAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="FollowUpAgent: detect absence of post-visit outreach per customer and prioritize visits flagged with a service issue (outreach/contact log not yet ingested).",
    ),
    Archetype(
        key="loyalty_after_bad_experience", domain="experience", name="Service recovery untapped",
        build=_recovery_after_bad, situations=("baseline", "leaking"),
        applies_flags=("repeat_purchase",),
        required_signals=("experience_flag", "transactions"),
        required_agents=("ExperienceSignalAgent", "RepeatPurchaseAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): flag bad visits and measure their return rate vs baseline to trigger and size recovery outreach.",
    ),
    Archetype(
        key="consistency_variance_across_staff", domain="experience", name="Consistency across staff",
        build=_consistency_across_staff, situations=("baseline", "concentrated"),
        required_signals=("experience_flag", "transactions"),
        required_agents=("ExperienceSignalAgent", "StaffAttributionAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="StaffAttributionAgent: attribute satisfaction/repeat outcomes to the serving worker (needs employee_id on the visit + an experience signal) to measure per-staff variance.",
    ),
    Archetype(
        key="consistency_across_dayparts", domain="experience", name="Consistency across dayparts",
        build=_consistency_across_dayparts, situations=("baseline",),
        required_signals=("experience_flag",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): segment an experience/accuracy signal by daypart to find a quality dip blended numbers hide.",
    ),
    Archetype(
        key="upsell_felt_pushy", domain="experience", name="Over-attach felt pushy",
        build=_upsell_pushy, situations=("baseline",),
        applies_flags=("tipped",),
        required_signals=("reviews_text", "transactions"),
        required_agents=("ReviewThemeAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewThemeAgent (shared): correlate attach-attempt intensity to 'pushy/pressured' feedback to find the point where attach hurts retention.",
    ),
    Archetype(
        key="checkout_friction", domain="experience", name="Checkout friction",
        build=_checkout_friction, situations=("baseline",),
        required_signals=("service_timing", "reviews_text"),
        required_agents=("ServiceTimingAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ServiceTimingAgent (shared): isolate the payment/checkout step duration from transaction timestamps and pair with friction feedback.",
    ),
    Archetype(
        key="wait_seating_accessibility", domain="experience", name="Wait environment / accessibility",
        build=_wait_seating_accessibility, situations=("baseline",),
        applies_flags=("walk_in_heavy",),
        required_signals=("service_observation",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): capture wait-environment/accessibility feedback (observation or review) to address perceived-wait drivers.",
    ),
    Archetype(
        key="packaging_presentation", domain="experience", name="Packaging / presentation",
        build=_packaging_presentation, situations=("baseline",),
        applies_keys=("cafe", "qsr", "full_restaurant", "bakery", "ghost_kitchen",
                      "florist", "jewelry", "boutique", "bookstore", "dispensary"),
        required_signals=("reviews_text",),
        required_agents=("ReviewThemeAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewThemeAgent (shared): extract packaging/presentation mentions and correlate to price tier and shareability.",
    ),
    Archetype(
        key="special_request_handling", domain="experience", name="Special-request handling",
        build=_special_request_handling, situations=("baseline", "concentrated"),
        applies_keys=("cafe", "qsr", "full_restaurant", "bar", "bakery", "ghost_kitchen",
                      "florist", "salon", "med_spa", "dental", "event_venue", "hotel_fb"),
        required_signals=("complaint_log",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): tag special-request visits (allergy/custom/accommodation) and their complaint outcomes to harden the capture-and-confirm flow.",
    ),
    Archetype(
        key="returning_customer_recognition", domain="experience", name="Regulars not recognized",
        build=_returning_recognition, situations=("baseline", "untapped"),
        applies_flags=("repeat_purchase",),
        required_signals=("transactions",),
        required_agents=("RepeatPurchaseAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="RepeatPurchaseAgent: surface a returning-customer flag + last-visit preference at point of service from transaction history.",
    ),
    Archetype(
        key="review_response_gap", domain="experience", name="Reviews unanswered",
        build=_review_response_gap, situations=("baseline", "untapped"),
        required_signals=("reviews_text",),
        required_agents=("ReviewThemeAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReviewThemeAgent (shared): track response status per review (esp. negatives) and response latency to flag the engagement gap.",
    ),
    Archetype(
        key="feedback_capture_missing", domain="experience", name="No feedback captured",
        build=_feedback_capture_missing, situations=("baseline", "untapped"),
        required_signals=("experience_flag",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): stand up a post-visit feedback capture path so satisfaction becomes a measurable signal at all (none exists today).",
    ),
    Archetype(
        key="complaint_resolution_slow", domain="experience", name="Slow complaint resolution",
        build=_complaint_resolution_slow, situations=("baseline", "leaking"),
        required_signals=("complaint_log",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): track complaint open/resolve timestamps and resolution status to measure time-to-resolve and an SLA breach rate.",
    ),
    Archetype(
        key="first_visit_onboarding_gap", domain="experience", name="First-visit onboarding gap",
        build=_first_visit_onboarding, situations=("baseline",),
        applies_flags=("repeat_purchase",),
        required_signals=("transactions", "experience_flag"),
        required_agents=("RepeatPurchaseAgent", "ExperienceSignalAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="RepeatPurchaseAgent: compare first-visit vs second-visit return rates and pair with first-timer feedback themes to size the onboarding gap.",
    ),
    Archetype(
        key="handoff_continuity_gap", domain="experience", name="Handoff continuity gap",
        build=_handoff_continuity, situations=("baseline", "concentrated"),
        applies_keys=("auto_repair", "hvac", "plumbing", "dental", "physio", "chiro",
                      "med_spa", "spa", "event_venue", "hotel_fb", "full_restaurant", "vet"),
        required_signals=("experience_flag", "complaint_log"),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): flag multi-touch visits with a staff handoff and link dropped-context complaints to the handoff step.",
    ),
    Archetype(
        key="expectation_setting_gap", domain="experience", name="Expectation mismatch",
        build=_expectation_setting_gap, situations=("baseline",),
        applies_keys=("auto_repair", "hvac", "plumbing", "cleaning", "landscaping",
                      "tattoo", "med_spa", "event_venue", "dental", "physio", "salon"),
        required_signals=("complaint_log",),
        required_agents=("ExperienceSignalAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExperienceSignalAgent (shared): classify complaints as expectation-gap vs execution-failure to route the right fix (communication vs service).",
    ),
)
