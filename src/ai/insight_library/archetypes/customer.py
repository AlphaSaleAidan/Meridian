"""
Domain: CUSTOMER / RETENTION (RFM-led).

Each archetype is a distinct reasoning pattern about the customer BASE — who comes
back, who lapses, who concentrates spend, who never returns. Distinctness comes
from the customer-lifecycle lever, not a number: churn-risk is an early-warning
intervention, one-and-done is a second-visit conversion problem, top-spender
concentration is a de-risking problem, win-back is a reactivation-timing problem,
and loyalty underuse is an activation problem. Specialization per vertical changes
what "a customer" and "coming back" even mean (a salon rebook, a dental recall, an
auto-repair return, a gym membership, a grocery basket all decay differently).

CAPABILITY NOTE: nearly every customer insight requires CUSTOMER IDENTITY — the
ability to stitch repeat behavior to one person across visits. The current swarm
holds `anonymous_customer_profiles`, `customer_sessions`, `caller_memory_index`,
and `transactions`, but walk-in transactions are largely UN-linked to a durable
identity. So most archetypes here are PARTIAL/MISSING and spec the new agents
(RFMAgent, CustomerJourneyAgent, ChurnPredictAgent) needed to join those tables
into a per-customer history.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── Churn / lapse ─────────────────────────────────────────────────────────
def _churn_risk_rising(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "emerging": " The deterioration is new — catch it before it becomes a trend.",
        "anomaly": " The jump is sudden, so look for a specific trigger (a service slip, a price change, a new competitor).",
    }.get(situation, "")
    return Built(
        title=f"Churn risk is rising — {X}% of your base is going quiet",
        observation=f"{X}% of previously-active customers haven't returned in {X} days, up from {X}% a quarter ago.",
        reasoning=f"Churn is cheapest to fix early: a customer slowing down still remembers you, so an intervention now costs far less than reacquiring them later at full {v.channels[0]} acquisition cost.{extra}",
        conclusion=f"Trigger a graduated win-back on the at-risk segment — a personal {v.channels[0]} touch before a discount — rather than waiting for them to fully lapse.",
        expected_effect=f"Catching even a fraction of pre-churn customers protects ~${X}/mo in retained {unit} revenue.",
        recommend_when={"state": "churn_risk_rising", "min_signal": "customer_history"},
        tags=("customer", "churn", "retention", v.family),
    )


def _at_risk_pre_churn_signal(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"A pre-churn warning pattern fires {X} days before customers leave",
        observation=f"Customers who lapse first show a tell — a stretched gap, a smaller {unit}, a dropped add-on — about {X} days before they go silent.",
        reasoning=f"A leading churn signal turns retention from reactive to preventive: intervening on the behavior (not the silence) catches customers while intent still exists, which a lapsed-list campaign cannot.",
        conclusion=f"Score active customers on the early-warning pattern and trigger a light, personal {v.channels[0]} touch the moment it fires — well before they qualify as lapsed.",
        expected_effect=f"Pre-empting churn at the signal is worth ~${X}/mo more than recovering customers after they've already gone.",
        recommend_when={"state": "pre_churn_signal", "min_signal": "customer_history"},
        tags=("customer", "churn", "early_warning", v.family),
    )


def _win_back_lapsed(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"{X} lapsed customers are worth a win-back — they bought before",
        observation=f"{X} customers who once averaged {X} {unit}s/quarter haven't returned in {X}+ days and sit unworked.",
        reasoning=f"Lapsed-but-known customers convert far better than cold prospects: they've already chosen you once, so reactivation skips the trust-building that new-customer {v.channels[0]} spend pays for.",
        conclusion=f"Run a timed win-back ladder on the lapsed list — reminder, then a reason, then an offer — segmented by how valuable each customer was, not a flat blast.",
        expected_effect=f"Reactivating even {X}% of the lapsed list is worth ~${X}/mo at known historical value.",
        recommend_when={"state": "lapsed_unworked", "min_signal": "customer_history"},
        tags=("customer", "winback", "reactivation", v.family),
    )


def _frequency_decay(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your regulars are slowing down — visits down {X}% per customer",
        observation=f"Active customers now buy {X} {unit}s/quarter, down from {X} a year ago, even though the customer count held.",
        reasoning=f"Falling frequency is a silent revenue leak: the base looks stable on a headcount, but each customer is worth less, so top-line erodes without an obvious churn event to flag it.",
        conclusion=f"Rebuild the visit habit on your active base — a cadence-timed nudge, a frequency reward, or a standing reason-to-return — before slowing turns into lapsing.",
        expected_effect=f"Restoring even part of lost frequency is worth ~${X}/mo across the active base.",
        recommend_when={"state": "frequency_decay", "min_signal": "customer_history"},
        tags=("customer", "frequency", "retention", v.family),
    )


def _visit_recency_cliff(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"There's a recency cliff at {X} days — past it, customers rarely return",
        observation=f"Customers who go {X} days without a {unit} return at only {X}%, versus {X}% for those who come back within the window.",
        reasoning=f"A sharp recency cliff defines your retention deadline: every day a customer drifts past it, win-back odds collapse, so the action is to intervene strictly before the cliff, not after.",
        conclusion=f"Set the win-back trigger just inside the {X}-day cliff and prioritize customers approaching it, instead of working a generic lapsed list.",
        expected_effect=f"Intervening before the cliff instead of after roughly doubles save rate — worth ~${X}/mo.",
        recommend_when={"state": "recency_cliff", "min_signal": "customer_history"},
        tags=("customer", "recency", "retention", v.family),
    )


def _dormant_high_value_customer(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"{X} high-value customers have gone dormant",
        observation=f"{X} customers who once ranked in your top {X}% by spend (~${X} each) haven't returned in {X}+ days.",
        reasoning=f"Dormant high-value customers are the highest-ROI save you have: each is worth multiples of an average customer, so a handful reactivated outperforms dozens of new {v.channels[0]} acquisitions.",
        conclusion=f"Work these by hand, not by campaign — a personal outreach from a {v.staff_role}/owner and a tailored reason to return, treating each as an account, not a list entry.",
        expected_effect=f"Reactivating a few dormant VIPs is worth ~${X}/mo given their outsized historical spend.",
        recommend_when={"state": "dormant_high_value", "min_signal": "customer_history"},
        tags=("customer", "vip", "winback", v.family),
    )


def _lapsed_seasonal_return(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your seasonal customers aren't coming back this cycle",
        observation=f"{X}% of customers who bought during last year's {X} season have not returned for the current one — a worse return rate than the prior {X} cycles.",
        reasoning=f"Seasonal customers run on an annual habit: if you miss the re-entry window, you lose the whole cycle, not just a visit — and a generic always-on campaign won't catch a once-a-year buyer at the right moment.",
        conclusion=f"Time a season-entry win-back to last year's return date for that cohort, via {v.channels[0]}, before the season's demand peaks.",
        expected_effect=f"Re-activating lapsed seasonal buyers protects ~${X} of this cycle's seasonal revenue.",
        recommend_when={"state": "seasonal_customer_lapse", "min_signal": "customer_history"},
        tags=("customer", "seasonal", "winback", v.family),
        # seasonal verticals
    )


# ── Acquisition / first-visit conversion ──────────────────────────────────
def _new_customer_share_falling(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"New-customer share is falling — {X}% of {unit}s vs {X}% before",
        observation=f"First-time customers are now {X}% of {unit}s, down from {X}% a year ago; revenue is leaning harder on the existing base.",
        reasoning=f"A shrinking new-customer share is a slow-motion risk: even healthy retention can't offset a drying top-of-funnel forever, and the gap only shows up later as an aging, shrinking base.",
        conclusion=f"Rebuild acquisition deliberately — a referral push on happy regulars plus a first-visit offer on {v.channels[-1]} — rather than assuming the base will self-replenish.",
        expected_effect=f"Restoring new-customer inflow protects the base's future value, worth ~${X}/mo in forward {unit}s.",
        recommend_when={"state": "new_customer_share_falling", "min_signal": "customer_history"},
        tags=("customer", "acquisition", "funnel", v.family),
    )


def _one_and_done_cohort(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"{X}% of new customers never come back",
        observation=f"Of customers acquired in the last {X} months, {X}% bought once and never returned — a large one-and-done cohort.",
        reasoning=f"One-and-done is a conversion problem, not an acquisition one: you've already paid to bring them in, so a weak first experience or no follow-up wastes the most expensive part of the funnel.",
        conclusion=f"Close the second-visit gap — a post-first-visit {v.channels[0]} thank-you with a reason to return within {X} days — before spending more on acquiring more one-timers.",
        expected_effect=f"Converting even a slice of one-timers to repeat is worth ~${X}/mo at near-zero added acquisition cost.",
        recommend_when={"state": "one_and_done", "min_signal": "customer_history"},
        tags=("customer", "first_visit", "retention", v.family),
    )


def _second_visit_conversion_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your second-visit rate is the weak link — only {X}% return once",
        observation=f"{X}% of first-timers come back for a second {unit}, but {X}% of those go on to a third — the drop-off is concentrated at visit two.",
        reasoning=f"The first-to-second visit is the make-or-break of loyalty: once a customer returns once, long-run retention jumps, so the single highest-leverage point in the lifecycle is converting visit one into visit two.",
        conclusion=f"Engineer the second visit specifically — a first-visit follow-up and a next-visit incentive that expires inside the typical return window, not a general loyalty program.",
        expected_effect=f"Lifting second-visit conversion compounds through the lifecycle — worth ~${X}/mo in retained value.",
        recommend_when={"state": "second_visit_gap", "min_signal": "customer_history"},
        tags=("customer", "second_visit", "retention", v.family),
    )


def _new_customer_aov_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"New customers spend {X}% less than regulars — and stay that way",
        observation=f"A first {unit} averages ${X} versus ${X} for an established customer, and the gap doesn't close for {X} visits.",
        reasoning=f"A persistent first-visit value gap means new customers aren't being introduced to your full range: they anchor low and stay low, so onboarding — not discounting — is the lever.",
        conclusion=f"Build a deliberate onboarding path that surfaces higher-value {unit}s and attach early, so new customers ramp to base value faster instead of plateauing low.",
        expected_effect=f"Ramping new customers to base spend sooner is worth ~${X}/mo as cohorts mature.",
        recommend_when={"state": "new_customer_value_gap", "min_signal": "customer_history"},
        tags=("customer", "onboarding", "aov", v.family),
    )


# ── RFM / value structure ─────────────────────────────────────────────────
def _top_spender_concentration(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "concentrated": " The dependence is severe enough to be a single-point-of-failure — de-risk it deliberately.",
    }.get(situation, "")
    return Built(
        title=f"Your top {X}% of customers drive {X}% of revenue",
        observation=f"The top {X}% of customers by spend account for {X}% of {unit} revenue; the long tail is shallow.",
        reasoning=f"High spend concentration cuts both ways: it's efficient to serve, but losing a few top accounts would gut revenue — so it's both a retention priority and a diversification signal.{extra}",
        conclusion=f"Protect the top tier with explicit VIP treatment while deliberately deepening the mid-tier (the next {X}%) so the base isn't one defection from a hole.",
        expected_effect=f"Securing the top tier and growing the mid-tier de-risks ~${X}/mo of concentrated revenue.",
        recommend_when={"state": "spend_concentration", "min_signal": "customer_history"},
        tags=("customer", "rfm", "concentration", v.family),
    )


def _rfm_segment_neglect(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You treat every customer the same — your RFM segments need different moves",
        observation=f"Your base splits into champions, at-risk, new, and lapsed, but all {X} get the same (or no) outreach.",
        reasoning=f"One message for all segments wastes both ends: champions don't need a discount and lapsed customers won't move on a generic note, so undifferentiated outreach under-monetizes the strong and under-saves the weak.",
        conclusion=f"Run segment-specific plays — reward champions, nudge at-risk, onboard new, win back lapsed — instead of a single broadcast.",
        expected_effect=f"Segment-tuned outreach beats one-size-fits-all by ~${X}/mo across the base.",
        recommend_when={"state": "rfm_undifferentiated", "min_signal": "customer_history"},
        tags=("customer", "rfm", "segmentation", v.family),
    )


def _ltv_by_cohort(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your customer lifetime value differs {X}x by acquisition cohort",
        observation=f"Customers acquired via {X} reach ~${X} lifetime value while those from {X} reach only ${X}, yet acquisition spend is split evenly.",
        reasoning=f"When LTV varies sharply by source/cohort, flat acquisition spend overpays for low-value channels and underfeeds high-value ones — the unit economics live in the cohort, not the average.",
        conclusion=f"Reallocate acquisition toward the channels/cohorts that produce the highest LTV, and fix or cut the low-LTV ones — judged on lifetime value, not first-{unit} cost.",
        expected_effect=f"Shifting spend toward high-LTV cohorts is worth ~${X}/mo in better-returning acquisition.",
        recommend_when={"state": "ltv_cohort_spread", "min_signal": "customer_history"},
        tags=("customer", "ltv", "cohort", v.family),
    )


def _high_value_segment_shrinking(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your high-value segment is shrinking — down {X}% in {X} months",
        observation=f"The count of customers in your top spend tier fell from {X} to {X}, while mid- and low-tier counts held.",
        reasoning=f"A shrinking top tier is an early margin warning: high-value customers carry disproportionate profit, so their slow erosion hurts the bottom line well before total customer count reflects it.",
        conclusion=f"Investigate why top-tier customers are downgrading or leaving, and stand up explicit retention for the tier (recognition, access, tailored {unit}s) before the segment thins further.",
        expected_effect=f"Stabilizing the high-value tier protects ~${X}/mo of disproportionately profitable revenue.",
        recommend_when={"state": "high_value_shrinking", "min_signal": "customer_history"},
        tags=("customer", "rfm", "value_tier", v.family),
    )


def _price_tier_downgrade(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    premium = "premium tier" if "high_ticket" in v.flags else "premium mix"
    return Built(
        title=f"Returning customers are trading down — premium share off {X} points",
        observation=f"Repeat customers' share of {premium} {unit}s fell from {X}% to {X}%, while their visit frequency held.",
        reasoning=f"Trading down without leaving is a quiet margin leak: the customer is still loyal, so it's not churn — it's a value-perception or merchandising gap pulling them toward cheaper {unit}s.",
        conclusion=f"Re-anchor value for repeat customers — reintroduce the premium {unit}s, bundle, or guide the {v.staff_role} to recommend up — rather than treating it as price resistance to discount away.",
        expected_effect=f"Reversing the downgrade trend is worth ~${X}/mo in recovered per-customer margin.",
        recommend_when={"state": "price_tier_downgrade", "min_signal": "customer_history"},
        tags=("customer", "downgrade", "margin", v.family),
        # high_ticket / retail
    )


# ── Repeat / frequency mechanics ──────────────────────────────────────────
def _repeat_rate_below_benchmark(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your repeat rate ({X}%) is below where it should be",
        observation=f"Only {X}% of customers buy a second {unit} within {X} days, under the typical bar for a {v.name.lower()}.",
        reasoning=f"For a repeat-driven business, the repeat rate IS the economic engine: a few points of repeat compound into far more lifetime value than equivalent acquisition, so a soft repeat rate caps the whole model.",
        conclusion=f"Make repeat the default — a return reason at every {unit} (next-visit hook, replenishment reminder, loyalty step) timed to the natural cycle via {v.channels[0]}.",
        expected_effect=f"Each point of repeat-rate lift is worth ~${X}/mo in compounding repeat revenue.",
        recommend_when={"state": "repeat_rate_low", "min_signal": "customer_history"},
        tags=("customer", "repeat", "retention", v.family),
        # repeat_purchase
    )


def _declining_basket_from_regulars(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your regulars' baskets are shrinking — down {X}% per visit",
        observation=f"Repeat customers' average {unit} fell from ${X} to ${X} over {X} months while their visit frequency held steady.",
        reasoning=f"A shrinking basket from loyal customers is pure margin erosion hiding behind stable traffic: they still come, but buy less per trip, so attach and merchandising — not retention — is the gap.",
        conclusion=f"Rebuild basket on the loyal base — bring back the dropped add-on/category, refresh the {v.staff_role} attach prompt, or bundle — instead of chasing more visits.",
        expected_effect=f"Restoring regulars' basket size is worth ~${X}/mo at no added acquisition cost.",
        recommend_when={"state": "basket_decline_regulars", "min_signal": "customer_history"},
        tags=("customer", "basket", "attach", v.family),
        # repeat_purchase
    )


def _wallet_share_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your customers buy one thing from you and the rest elsewhere",
        observation=f"{X}% of repeat customers only ever buy from a single category/service, though you offer {X}+ they could use.",
        reasoning=f"Single-category loyalty is untapped wallet share: the trust to cross-sell already exists, so the gap is that customers don't know — or aren't prompted about — what else you do, not that they buy it elsewhere by choice.",
        conclusion=f"Cross-introduce deliberately — surface a complementary {unit} at the right moment via {v.staff_role} or {v.channels[0]}, sequenced to each customer's existing behavior.",
        expected_effect=f"Expanding wallet share by even one category per customer is worth ~${X}/mo.",
        recommend_when={"state": "wallet_share_gap", "min_signal": "customer_history"},
        tags=("customer", "cross_sell", "wallet_share", v.family),
    )


# ── Appointment / membership specific ─────────────────────────────────────
def _rebook_rate_decay(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    kpi = v.core_kpis[0]
    if v.key in ("dental", "optometry", "vet", "chiro", "physio"):
        frame = f"recall/next-{unit} not being booked before the patient leaves"
        move = f"book the next recall at checkout and confirm it via {v.channels[0]} ahead of the due date"
    elif v.key in ("auto_repair", "tire_shop"):
        frame = f"no next-service scheduled, so the customer drifts to whoever's convenient next time"
        move = f"schedule the next service interval at pickup and remind before it's due"
    else:
        frame = f"the next {unit} not being secured at the chair before the client walks out"
        move = f"pre-book the next {unit} at checkout while the {v.staff_role} relationship is fresh"
    return Built(
        title=f"Your rebook rate is decaying — {X}% leave without the next {unit} booked",
        observation=f"Rebook-at-visit ({kpi}) fell from {X}% to {X}%; the gap is {frame}.",
        reasoning=f"For an appointment business, rebooking at the point of service is the cheapest retention there is: a client who leaves unbooked is exposed to every competitor before their next need, while a booked one is locked to your {v.staff_role}.",
        conclusion=f"Make rebooking the default close of every visit — {move} — rather than relying on the customer to come back on their own.",
        expected_effect=f"Each point of rebook recovery is worth ~${X}/mo in locked-in future {unit}s.",
        recommend_when={"state": "rebook_decay", "min_signal": "bookings"},
        tags=("customer", "rebook", "retention", v.family),
        # appointment_based
    )


def _membership_churn(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Membership churn is rising — {X}% cancel within {X} months",
        observation=f"{X}% of members lapse before month {X}, and {X}% of cancellations come from members who'd stopped using the membership weeks earlier.",
        reasoning=f"Membership churn is usage-driven: a member who stops showing up cancels next, so the leak is engagement (unused membership) long before the cancel click — a price/retention offer at cancel-time is too late.",
        conclusion=f"Watch usage, not just billing — re-engage members whose activity drops with a personal {v.channels[0]} nudge during the lull, before they decide to cancel.",
        expected_effect=f"Cutting early membership churn is worth ~${X}/mo in retained recurring revenue.",
        recommend_when={"state": "membership_churn", "min_signal": "membership_status"},
        tags=("customer", "membership", "churn", v.family),
        # membership
    )


def _subscription_attach(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Few of your repeat buyers are on a subscription — {X}% attach",
        observation=f"Only {X}% of customers who buy the same replenishable {unit} on a cycle are on auto-ship/subscription; the rest reorder manually or lapse.",
        reasoning=f"A manual reorder is a churn opportunity every cycle; a subscription converts a recurring need into locked recurring revenue and removes the competitor's window between purchases.",
        conclusion=f"Offer subscription at the moment of a repeat purchase — auto-replenish on the items customers already rebuy on a cadence — rather than as a generic signup.",
        expected_effect=f"Converting habitual rebuyers to subscription is worth ~${X}/mo in locked recurring {unit}s.",
        recommend_when={"state": "subscription_attach_low", "min_signal": "customer_history"},
        tags=("customer", "subscription", "recurring", v.family),
        # membership / pet_store
    )


# ── Loyalty / referral / channel ──────────────────────────────────────────
def _loyalty_program_underused(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your loyalty program is underused — {X}% of sales go unattributed",
        observation=f"Only {X}% of {unit}s are tied to a loyalty/identified customer; enrolled members redeem at just {X}%.",
        reasoning=f"An underused loyalty program fails twice: low enrollment means you can't see who your customers are (no targeting), and low redemption means the earned reward isn't pulling repeat visits — it's cost without leverage.",
        conclusion=f"Fix activation, not the reward size — make enrollment frictionless at checkout and prompt redemption via {v.channels[0]} so the program actually drives identified repeat behavior.",
        expected_effect=f"Lifting enrollment and redemption turns the program into a real repeat lever — worth ~${X}/mo.",
        recommend_when={"state": "loyalty_underused", "min_signal": "customer_history"},
        tags=("customer", "loyalty", "activation", v.family),
        # repeat_purchase
    )


def _referral_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your happiest customers aren't referring — referral is near zero",
        observation=f"Only {X}% of new customers come from referral, despite {X}% of your base being repeat/satisfied customers.",
        reasoning=f"Referral is your lowest-cost, highest-trust acquisition channel, and a satisfied base is a standing asset — leaving it unworked means paying full {v.channels[-1]} cost for customers you could earn through a simple ask.",
        conclusion=f"Make the ask systematic — prompt happy customers to refer at a high-satisfaction moment, with a two-sided reason, rather than hoping word-of-mouth happens on its own.",
        expected_effect=f"Activating referral on a happy base is worth ~${X}/mo in low-cost, high-retention acquisition.",
        recommend_when={"state": "referral_untapped", "min_signal": "customer_history"},
        tags=("customer", "referral", "acquisition", v.family),
    )


def _referral_source_concentration(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Most new customers come from one source — {X}% from {X}",
        observation=f"{X}% of new customers trace to a single channel/referrer, with the rest scattered thin.",
        reasoning=f"Acquisition concentrated in one source is fragile: an algorithm change, a referrer leaving, or a price hike on that channel would choke your top-of-funnel overnight — diversification is risk management, not vanity.",
        conclusion=f"Protect and deepen the lead source while deliberately building a second channel to backstop it, instead of riding a single pipe.",
        expected_effect=f"Diversifying acquisition de-risks ~${X}/mo of new-customer flow against a single-source shock.",
        recommend_when={"state": "acquisition_concentration", "min_signal": "customer_history"},
        tags=("customer", "acquisition", "concentration", v.family),
    )


def _channel_migration(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    a, b = v.channels[0], v.channels[-1]
    return Built(
        title=f"Your customers are migrating from {a} to {b}",
        observation=f"The share of {unit}s through {b} rose from {X}% to {X}% over {X} months as {a} declined, with the same customers switching.",
        reasoning=f"A channel migration changes your cost-to-serve and your relationship: if customers move to a {b} you under-serve (or that carries higher fees/lower attach), revenue can hold while margin and loyalty quietly erode.",
        conclusion=f"Meet customers on the rising channel — bring its experience, attach, and margin up to par with {a} — rather than defending a channel they're leaving.",
        expected_effect=f"Managing the migration protects ~${X}/mo in margin and attach that a passive shift would leak.",
        recommend_when={"state": "channel_migration", "min_signal": "customer_history"},
        tags=("customer", "channel", "migration", v.family),
    )


def _discount_dependency(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"A segment of your base only buys on discount — {X}% of repeat {unit}s",
        observation=f"{X}% of repeat purchases occur during a promo, and that segment's full-price visit rate is near zero.",
        reasoning=f"Discount-trained customers erode margin and reset price expectations: every promo to retain them costs more than they return, and it teaches the rest of the base to wait for the next deal.",
        conclusion=f"Wean the segment off promo dependency — shift their reason-to-return to value/loyalty rather than price, and stop blanket discounts that subsidize customers who'd pay full freight.",
        expected_effect=f"Reducing discount dependency is worth ~${X}/mo in recovered margin without losing genuine demand.",
        recommend_when={"state": "discount_dependency", "min_signal": "customer_history"},
        tags=("customer", "discount", "margin", v.family),
    )


def _cohort_retention_flattening(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Newer cohorts retain worse than older ones — the curve is dropping",
        observation=f"Customers acquired {X} months ago retained at {X}% by month {X}; the latest cohort is tracking to only {X}% at the same age.",
        reasoning=f"A falling cohort-retention curve is the earliest reliable warning of a deteriorating business: it shows up in new cohorts long before blended metrics move, so acting now prevents a baked-in future decline.",
        conclusion=f"Diagnose what changed for recent cohorts (onboarding, quality, mix, competition) and fix the experience for new customers before the weaker curve becomes your whole base.",
        expected_effect=f"Restoring new-cohort retention to the historical curve protects ~${X}/mo of future revenue.",
        recommend_when={"state": "cohort_retention_decline", "min_signal": "customer_history"},
        tags=("customer", "cohort", "retention", v.family),
    )


# ── Registration ──────────────────────────────────────────────────────────
# Shared upgrade specs (customer identity is the common blocker):
_IDENTITY_UPGRADE = (
    "CustomerJourneyAgent + RFMAgent: stitch a durable per-customer history by "
    "resolving identity across transactions ↔ anonymous_customer_profiles ↔ "
    "customer_sessions ↔ caller_memory_index (loyalty id / phone / card token / "
    "session fingerprint), then compute recency-frequency-monetary per customer. "
    "Walk-in transactions are largely identity-less today, so this must be built "
    "before the insight can fill."
)
_CHURN_UPGRADE = (
    "ChurnPredictAgent (on top of CustomerJourneyAgent/RFMAgent): model lapse "
    "probability and the leading pre-churn behavior pattern from the stitched "
    "per-customer history; emits an at-risk score and an intervention window."
)

register(
    Archetype(
        key="churn_risk_rising", domain="customer", name="Rising churn risk",
        build=_churn_risk_rising,
        situations=("baseline", "emerging", "anomaly"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent", "ChurnPredictAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " " + _CHURN_UPGRADE,
    ),
    Archetype(
        key="at_risk_pre_churn_signal", domain="customer", name="Pre-churn early warning",
        build=_at_risk_pre_churn_signal,
        situations=("baseline",),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "ChurnPredictAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHURN_UPGRADE + " Requires the stitched history from " + _IDENTITY_UPGRADE,
    ),
    Archetype(
        key="win_back_lapsed", domain="customer", name="Win back lapsed",
        build=_win_back_lapsed,
        situations=("baseline", "leaking"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE,
    ),
    Archetype(
        key="frequency_decay", domain="customer", name="Visit frequency decay",
        build=_frequency_decay,
        situations=("baseline", "declining"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE,
    ),
    Archetype(
        key="visit_recency_cliff", domain="customer", name="Recency cliff",
        build=_visit_recency_cliff,
        situations=("baseline",),
        required_signals=("customer_history",),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " The cliff is found by survival analysis on inter-visit gaps from the stitched history.",
    ),
    Archetype(
        key="dormant_high_value_customer", domain="customer", name="Dormant VIP",
        build=_dormant_high_value_customer,
        situations=("baseline", "concentrated"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Requires per-customer monetary ranking to isolate the top tier among the lapsed.",
    ),
    Archetype(
        key="lapsed_seasonal_return", domain="customer", name="Lapsed seasonal customer",
        build=_lapsed_seasonal_return,
        situations=("seasonal_peak", "seasonal_trough"),
        applies_flags=("seasonal",),
        required_signals=("customer_history", "daily_revenue"),
        required_agents=("CustomerJourneyAgent", "SeasonalityAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus SeasonalityAgent to define each season window and align cohorts to their prior-year return date.",
    ),
    Archetype(
        key="new_customer_share_falling", domain="customer", name="New-customer share falling",
        build=_new_customer_share_falling,
        situations=("baseline", "declining"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " First-vs-returning classification needs the per-customer first-seen date.",
    ),
    Archetype(
        key="one_and_done_cohort", domain="customer", name="One-and-done cohort",
        build=_one_and_done_cohort,
        situations=("baseline", "leaking"),
        required_signals=("customer_history",),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE,
    ),
    Archetype(
        key="second_visit_conversion_gap", domain="customer", name="Second-visit gap",
        build=_second_visit_conversion_gap,
        situations=("baseline",),
        required_signals=("customer_history",),
        required_agents=("CustomerJourneyAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Visit-number sequencing per customer is required to isolate the first→second drop-off.",
    ),
    Archetype(
        key="new_customer_aov_gap", domain="customer", name="New-customer value gap",
        build=_new_customer_aov_gap,
        situations=("baseline",),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Requires per-customer visit-number to compare first-{unit} value vs mature value.",
    ),
    Archetype(
        key="top_spender_concentration", domain="customer", name="Top-spender concentration",
        build=_top_spender_concentration,
        situations=("baseline", "concentrated"),
        required_signals=("customer_history", "transactions"),
        required_agents=("RFMAgent", "CustomerJourneyAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Concentration is computed from per-customer monetary totals.",
    ),
    Archetype(
        key="rfm_segment_neglect", domain="customer", name="Undifferentiated RFM",
        build=_rfm_segment_neglect,
        situations=("baseline",),
        required_signals=("customer_history", "transactions"),
        required_agents=("RFMAgent", "CustomerJourneyAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " RFMAgent then buckets the stitched base into champions/at-risk/new/lapsed segments.",
    ),
    Archetype(
        key="ltv_by_cohort", domain="customer", name="LTV by cohort",
        build=_ltv_by_cohort,
        situations=("baseline",),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent", "AttributionAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus AttributionAgent to tag each customer's acquisition source/cohort (source is not captured at first transaction today).",
    ),
    Archetype(
        key="high_value_segment_shrinking", domain="customer", name="Shrinking high-value tier",
        build=_high_value_segment_shrinking,
        situations=("baseline", "declining"),
        required_signals=("customer_history", "transactions"),
        required_agents=("RFMAgent", "CustomerJourneyAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Track top-tier membership count over time from per-customer monetary ranking.",
    ),
    Archetype(
        key="price_tier_downgrade", domain="customer", name="Customers trading down",
        build=_price_tier_downgrade,
        situations=("baseline", "declining"),
        applies_flags=("high_ticket",),
        applies_families=("retail",),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Requires per-customer premium-vs-value mix over time (item tier on transactions).",
    ),
    Archetype(
        key="repeat_rate_below_benchmark", domain="customer", name="Repeat rate below benchmark",
        build=_repeat_rate_below_benchmark,
        situations=("baseline",),
        applies_flags=("repeat_purchase",),
        required_signals=("customer_history",),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE,
    ),
    Archetype(
        key="declining_basket_from_regulars", domain="customer", name="Regulars' basket shrinking",
        build=_declining_basket_from_regulars,
        situations=("baseline", "declining"),
        applies_flags=("repeat_purchase",),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Basket trend requires repeat-customer ticket history (line items on transactions).",
    ),
    Archetype(
        key="wallet_share_gap", domain="customer", name="Untapped wallet share",
        build=_wallet_share_gap,
        situations=("baseline", "untapped"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "BasketAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus BasketAgent to map per-customer category coverage from line items.",
    ),
    Archetype(
        key="rebook_rate_decay", domain="customer", name="Rebook-rate decay",
        build=_rebook_rate_decay,
        situations=("baseline", "declining"),
        applies_flags=("appointment_based",),
        required_signals=("bookings", "customer_history"),
        required_agents=("BookingAgent", "CustomerJourneyAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingAgent has appointment records with a booked identity, so rebook-at-visit is measurable, but linking a missed rebook to the same returning customer later still needs " + _IDENTITY_UPGRADE,
    ),
    Archetype(
        key="membership_churn", domain="customer", name="Membership churn",
        build=_membership_churn,
        situations=("baseline", "emerging"),
        applies_flags=("membership",),
        required_signals=("membership_status", "customer_history"),
        required_agents=("MembershipAgent", "ChurnPredictAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="MembershipAgent: member roster + billing status is available, so realized churn is measurable; the usage-based EARLY warning needs per-member visit/usage events joined to membership_status (usage is not yet linked to the membership id).",
    ),
    Archetype(
        key="subscription_attach", domain="customer", name="Subscription attach",
        build=_subscription_attach,
        situations=("baseline", "untapped"),
        applies_flags=("membership",),
        applies_keys=("pet_store", "grocery"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "SubscriptionAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus SubscriptionAgent to detect a per-customer replenishment cadence on the same SKU vs. existing subscription enrollment.",
    ),
    Archetype(
        key="loyalty_program_underused", domain="customer", name="Loyalty underused",
        build=_loyalty_program_underused,
        situations=("baseline",),
        applies_flags=("repeat_purchase",),
        required_signals=("customer_history", "transactions"),
        required_agents=("LoyaltyAgent", "CustomerJourneyAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LoyaltyAgent: enrollment + redemption events exist where a loyalty program is configured, so attach/redemption rates are measurable; tying unattributed (anonymous) sales back to the program still depends on " + _IDENTITY_UPGRADE,
    ),
    Archetype(
        key="referral_untapped", domain="customer", name="Referral untapped",
        build=_referral_untapped,
        situations=("baseline", "untapped"),
        required_signals=("customer_history",),
        required_agents=("CustomerJourneyAgent", "AttributionAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus AttributionAgent to capture acquisition source (referral vs other) at first transaction — not recorded today.",
    ),
    Archetype(
        key="referral_source_concentration", domain="customer", name="Acquisition concentration",
        build=_referral_source_concentration,
        situations=("baseline", "concentrated"),
        required_signals=("customer_history",),
        required_agents=("AttributionAgent", "CustomerJourneyAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AttributionAgent: capture and store acquisition source per new customer (referrer/channel/campaign). No source attribution is recorded at acquisition today. Builds on " + _IDENTITY_UPGRADE,
    ),
    Archetype(
        key="channel_migration", domain="customer", name="Channel migration",
        build=_channel_migration,
        situations=("baseline", "emerging"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "ChannelAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus ChannelAgent to tag each transaction's channel and trend per-customer channel mix over time.",
    ),
    Archetype(
        key="discount_dependency", domain="customer", name="Discount dependency",
        build=_discount_dependency,
        situations=("baseline", "leaking"),
        required_signals=("customer_history", "transactions"),
        required_agents=("CustomerJourneyAgent", "PromoAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Plus PromoAgent to flag each transaction as promo vs full-price and measure a customer's full-price visit rate.",
    ),
    Archetype(
        key="cohort_retention_flattening", domain="customer", name="Cohort retention decline",
        build=_cohort_retention_flattening,
        situations=("baseline", "declining"),
        required_signals=("customer_history",),
        required_agents=("CustomerJourneyAgent", "RFMAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_IDENTITY_UPGRADE + " Cohort curves require per-customer acquisition month + retained-by-month from the stitched history.",
    ),
)
