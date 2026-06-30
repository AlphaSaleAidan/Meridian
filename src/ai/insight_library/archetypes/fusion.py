"""
Domain: FUSION / CROSS-DOMAIN.

Every archetype here JOINS two or more data sources that today live apart, and the
value is exactly that join: a stockout matters only when it lands on a forecasted
peak; a missed call matters only in dollars; understaffing matters only where the
camera also saw the walkout. These are the richest, highest-value insights in the
library — and by construction none of them is FULL, because no single existing
agent spans both sides of the join.

So for fusion the `swarm_upgrade` field is the deliverable, not a footnote. Each
one names a concrete fusion agent and the EXACT join it must perform
(inputs → join key → output signal), so the product owner can read this file as a
buildable backlog of "upgrade the swarm" work, ordered by the revenue the join
unlocks.

Distinctness comes from the *pair* of domains and the causal link between them,
never from a number — a weather×revenue insight and a weather×inventory insight
reason about genuinely different levers even though both read the weather feed.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register

# Families with a physical floor (for the vision-bearing fusions).
FLOOR_FAMILIES = ("food_service", "retail", "personal_care", "automotive", "fitness")
NO_GHOST = ("ghost_kitchen",)
# Families that take phone business and lose money when calls drop.
PHONE_FAMILIES = ("food_service", "personal_care", "health_wellness", "home_services", "automotive", "hospitality")


# ── 1. Footfall × conversion × staffing → walkouts when thin ──────────────
def _footfall_conv_staffing(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Understaffing turns footfall into walkouts",
        observation=f"In hours where entries-per-{v.staff_role} top {X}, vision conversion falls {X}pts and walkouts rise to {X}/hr.",
        reasoning=f"Three signals only mean something together: the camera proves the traffic was there, the schedule proves the floor was thin, and POS proves the {unit}s never landed. Any one alone is ambiguous; joined, they isolate lost sales caused specifically by coverage, not demand.",
        conclusion=f"Staff to a footfall ceiling: add a {v.staff_role} whenever forecast entries-per-head cross {X} in the {X} window.",
        expected_effect=f"Converting the staffing-driven walkouts recovers ~${X}/mo on existing traffic.",
        recommend_when={"state": "understaffed_walkouts", "min_signal": "vision_traffic"},
        tags=("fusion", "footfall", "staffing", v.family),
    )


# ── 2. Weather × revenue ──────────────────────────────────────────────────
def _weather_revenue(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Weather moves your revenue more than your calendar does",
        observation=f"{X} days lift {unit} revenue {X}% while {X} days drop it {X}% — a swing larger than your weekday/weekend gap.",
        reasoning=f"For {v.name}, weather is a demand driver you currently react to instead of plan around; once revenue is regressed on the forecast, tomorrow's weather becomes a staffing, prep, and promo input rather than a surprise that lands on the P&L.",
        conclusion=f"Pre-position to the 3-day forecast: scale {v.staff_role} hours and inventory up on favorable days, protect margin on adverse ones.",
        expected_effect=f"Acting on the forecast instead of reacting is worth ~${X}/mo in captured upside and avoided waste.",
        recommend_when={"state": "weather_revenue_sensitive", "min_signal": "hourly_revenue"},
        tags=("fusion", "weather", "revenue", v.family),
    )


# ── 3. Phone-missed × revenue ─────────────────────────────────────────────
def _phone_missed_revenue(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Missed calls are silent lost revenue",
        observation=f"{X} calls/day go unanswered, mostly in the {X} window; your phone-order/booking rate implies ~{X} lost {unit}s among them.",
        reasoning=f"A missed call is invisible to POS — there's no record of the sale that never happened — so it never shows up in revenue review. Joining call logs to average {unit} value converts a dropped-call count into a dollar figure, which is the only way it competes for attention against visible problems.",
        conclusion=f"Cover the unanswered window (overflow line, callback, or a {v.staff_role} dedicated to phones at {X}) and track recovered {unit}s.",
        expected_effect=f"Answering the missed-call window recovers ~${X}/mo in otherwise-untracked demand.",
        recommend_when={"state": "missed_calls_lost_revenue", "min_signal": "call_logs"},
        tags=("fusion", "phone", "revenue", v.family),
    )


# ── 4. Inventory × demand forecast → stockout on a peak ───────────────────
def _stockout_on_peak(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A stockout is about to hit your forecasted peak",
        observation=f"On-hand for {X} covers {X} days of normal sales, but the forecast shows a {X}% demand spike on {X} — depletion lands mid-peak.",
        reasoning=f"Inventory level alone looks fine and the forecast alone is abstract; joined, they reveal a timing collision — you'll run out exactly when demand is highest, turning a routine reorder into peak-day lost sales plus disappointed {v.sale_unit} customers who may not return.",
        conclusion=f"Pull the reorder forward / expedite {X} now so cover clears the forecasted peak with a buffer.",
        expected_effect=f"Avoiding the peak stockout protects ~${X}/mo of high-demand sales (and the repeat business behind them).",
        recommend_when={"state": "stockout_meets_forecast_peak", "min_signal": "inventory_levels"},
        tags=("fusion", "inventory", "forecast", v.family),
    )


# ── 5. Loyalty × margin → best customers buy low-margin ───────────────────
def _loyalty_margin(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your best customers buy your worst-margin items",
        observation=f"Your top {X}% of loyalty spenders concentrate {X}% of their baskets in your lowest-margin {X} category.",
        reasoning=f"Revenue rank and profit rank diverge: the customers you most reward are subsidized into your thinnest products, so loyalty spend grows the top line while doing little for the bottom. POS sees revenue, the margin table sees profit — only the join sees that your loyalty program is steering volume to the wrong shelf.",
        conclusion=f"Re-aim loyalty rewards and {v.staff_role} recommendations for top customers toward higher-margin alternatives in {X}.",
        expected_effect=f"Shifting even part of top-customer mix upmargin is worth ~${X}/mo in profit at flat revenue.",
        recommend_when={"state": "loyal_low_margin_mix", "min_signal": "loyalty_customers"},
        tags=("fusion", "loyalty", "margin", v.family),
    )


# ── 6. Staff × product attach → who actually upsells ──────────────────────
def _staff_attach(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Some {v.staff_role}s upsell {X}x more than others",
        observation=f"Attach/add-on rate ranges from {X}% to {X}% across {v.staff_role}s on identical traffic and {X} mix.",
        reasoning=f"Attach is a learnable behavior, not luck — but you can only coach it once transaction line-items are attributed to the {v.staff_role} who rang them. The join turns a vague 'be more salesy' into a named gap: your bottom quartile is leaving a known dollar amount on every ticket your top quartile captures.",
        conclusion=f"Have the top attachers' script taught to the bottom quartile and re-measure attach by {v.staff_role} in {X} weeks.",
        expected_effect=f"Lifting the bottom quartile to median attach is worth ~${X}/mo.",
        recommend_when={"state": "attach_rate_variance", "min_signal": "transactions"},
        tags=("fusion", "staffing", "attach", v.family),
    )


# ── 7. Daypart × inventory → prep mismatch ────────────────────────────────
def _daypart_prep(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"What you prep doesn't match when it sells",
        observation=f"You prep {X} for the day up front, but {X}% of {X} demand lands after {X} — early items waste, late items run short.",
        reasoning=f"Prep is committed against an average day while sales arrive by daypart; without joining the by-hour sales curve to the prep plan, the same shift simultaneously over-prepares slow items (waste) and under-prepares the peak (lost sales). Two opposite errors hiding inside one 'we made enough' total.",
        conclusion=f"Split prep to the daypart curve: smaller early batch for {X}, a timed second batch ahead of the {X} peak.",
        expected_effect=f"Matching prep to the daypart curve cuts waste and lost sales for ~${X}/mo combined.",
        recommend_when={"state": "prep_demand_mismatch", "min_signal": "inventory_levels"},
        tags=("fusion", "daypart", "inventory", v.family),
    )


# ── 8. Footfall × weather → weather elasticity of traffic ─────────────────
def _footfall_weather(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You can predict tomorrow's foot traffic from the forecast",
        observation=f"Vision entries swing {X}% between {X} and {X} weather, with a {X}-day lag on some conditions.",
        reasoning=f"Door-counter history plus the weather feed turns footfall from something you observe after the fact into something you forecast a day out. For {v.name} this is upstream of staffing, prep, and promo — knowing traffic before it arrives is what makes every other plan proactive instead of reactive.",
        conclusion=f"Feed the weather-adjusted entry forecast into the next-day schedule and order so coverage matches expected door traffic.",
        expected_effect=f"Forecast-driven coverage avoids both over- and under-staffing for ~${X}/mo.",
        recommend_when={"state": "weather_drives_footfall", "min_signal": "vision_traffic"},
        tags=("fusion", "footfall", "weather", v.family),
    )


# ── 9. Booking lead-time × no-show ────────────────────────────────────────
def _leadtime_noshow(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Last-minute bookings no-show the most",
        observation=f"{v.sale_unit.title()}s booked under {X}h ahead no-show at {X}% versus {X}% for those booked {X}+ days out.",
        reasoning=f"Lead time is a risk signal hiding in the booking record: short-lead bookings carry weak commitment, so treating every booking identically over-protects safe ones and under-protects risky ones. Joining lead time to no-show outcome lets you price the risk instead of eating it.",
        conclusion=f"Require a deposit or confirmation step only on sub-{X}h bookings, and overbook those slots by a measured factor.",
        expected_effect=f"Recovering no-showed capacity is worth ~${X}/mo in otherwise-idle {v.staff_role} time.",
        recommend_when={"state": "leadtime_predicts_noshow", "min_signal": "bookings"},
        tags=("fusion", "booking", "no_show", v.family),
    )


# ── 10. Payment type × basket ─────────────────────────────────────────────
def _payment_basket(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"How customers pay predicts how much they spend",
        observation=f"{X}-paid {v.sale_unit}s average ${X}, versus ${X} for {X} — a {X}% basket gap on the same floor.",
        reasoning=f"Tender type is a free behavioral segment already sitting in the payments stream; joined to basket value it reveals which payment path correlates with bigger spend, which tells you where to remove friction (or add an incentive) to nudge customers toward the higher-basket behavior.",
        conclusion=f"Promote the high-basket tender at the point of sale (speed, a small incentive) and steer the {v.staff_role} prompt accordingly.",
        expected_effect=f"Shifting mix toward the high-basket tender is worth ~${X}/mo.",
        recommend_when={"state": "payment_basket_gap", "min_signal": "payments"},
        tags=("fusion", "payments", "basket", v.family),
    )


# ── 11. Event/holiday × staffing ──────────────────────────────────────────
def _event_staffing(v: Vertical, situation: str) -> Built:
    extra = " A known seasonal high is on the calendar — lock coverage now, before the schedule sets to a normal week." if situation == "seasonal_peak" else ""
    return Built(
        title=f"Local events spike demand and you're scheduled for a normal day",
        observation=f"On {X} local events your {v.sale_unit} volume jumps {X}%, but the schedule those days matches an average {X}.",
        reasoning=f"The event calendar and the staffing plan are maintained separately, so predictable demand spikes meet flat coverage — you under-serve the busiest, most profitable days of the month while paying normal labor on quiet ones. The fix is a join, not more labor.{extra}",
        conclusion=f"Auto-flag scheduled {v.staff_role} coverage against the event calendar and require an uplift on flagged days.",
        expected_effect=f"Staffing to event demand captures ~${X}/mo of otherwise-missed spike revenue.",
        recommend_when={"state": "event_staffing_gap", "min_signal": "events_calendar"},
        tags=("fusion", "events", "staffing", v.family),
    )


# ── 12. Queue × abandonment × revenue ─────────────────────────────────────
def _queue_revenue(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Put a dollar figure on your queue",
        observation=f"At peak, vision logs {X} balks while wait sits at {X}s; at your ${X} average {unit}, that's ~${X}/day walking out of line.",
        reasoning=f"Wait time and balk counts are operational metrics nobody acts on until they're monetized; joining them to average {unit} value turns 'the line is long sometimes' into a daily dollar loss that can be compared head-to-head against the cost of another register or {v.staff_role}.",
        conclusion=f"Open a second service point whenever wait crosses {X}s — the join shows it pays for itself above that threshold.",
        expected_effect=f"Eliminating peak balks recovers ~${X}/mo, net of the added coverage.",
        recommend_when={"state": "queue_cost_quantified", "min_signal": "vision_traffic"},
        tags=("fusion", "queue", "revenue", v.family),
    )


# ── 13. Customer recency × campaign timing ────────────────────────────────
def _recency_campaign(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your campaigns fire at the wrong point in the customer's cycle",
        observation=f"Median repurchase cycle is {X} days, but campaigns send on a fixed {X} calendar — many land while customers are still satisfied or already lapsed.",
        reasoning=f"A win-back sent too early wastes margin on someone who'd have returned anyway; sent too late it reaches someone already gone. Joining per-customer recency to the campaign calendar lets you time outreach to the moment of fading intent, which is when a nudge actually changes behavior.",
        conclusion=f"Trigger campaigns off individual recency (at ~{X}% of each customer's typical cycle) instead of a fixed date.",
        expected_effect=f"Recency-timed outreach lifts reactivation for ~${X}/mo at the same send cost.",
        recommend_when={"state": "campaign_timing_mismatch", "min_signal": "loyalty_customers"},
        tags=("fusion", "recency", "campaign", v.family),
    )


# ── 14. Vision demographics × product mix ─────────────────────────────────
def _demo_product(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Merchandise to who walks in, not who you imagine",
        observation=f"Vision shows {X}% of visitors in the {X} segment, but {X} (your {v.core_kpis[0]} driver) is merchandised for a different one.",
        reasoning=f"This joins who the camera sees to what the POS sells: the segment actually entering is under-served by the front assortment, so they convert below potential while inventory tuned for an absent segment ages. Neither the vision feed nor the product mix shows it alone — only the cross.",
        conclusion=f"Re-weight front-of-store and buying toward the real visitor segment for {X} weeks and watch segment-level conversion.",
        expected_effect=f"Matching assortment to actual visitor mix is worth ~${X}/mo.",
        recommend_when={"state": "demo_product_mismatch", "min_signal": "vision_visits"},
        tags=("fusion", "demographics", "merchandising", v.family),
    )


# ── 15. Peak × supplier lead time ─────────────────────────────────────────
def _peak_supplier(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your supplier lead time is longer than your warning of the peak",
        observation=f"The forecast flags a {X} demand peak {X} days out, but {X}'s supplier needs {X} days to deliver — the order window has already closed by the time the peak is visible.",
        reasoning=f"A forecast is useless if it arrives inside the lead time. Joining each supplier's lead time to the demand forecast computes the real 'order-by' date per item, exposing peaks you can still act on versus ones you must pre-commit to now — a distinction invisible when forecast and procurement live apart.",
        conclusion=f"Set per-item order-by alerts at (forecast peak date − supplier lead time) and pre-commit {X} before its window closes.",
        expected_effect=f"Hitting the order-by window on peak items protects ~${X}/mo of peak sales.",
        recommend_when={"state": "leadtime_exceeds_warning", "min_signal": "inventory_levels"},
        tags=("fusion", "supplier", "forecast", v.family),
    )


# ── 16. Weather × inventory (perishable waste) ────────────────────────────
def _weather_waste(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You over-prep perishables on slow-weather days",
        observation=f"On {X} days, perishable {X} waste runs {X}% versus {X}% on normal days, because prep was set before the forecast.",
        reasoning=f"Perishable commitment is irreversible and weather is the demand driver, so a join of the forecast to the prep/order plan prevents loss before it's baked in — distinct from weather×revenue (which chases upside), this one protects margin on the downside by simply making less.",
        conclusion=f"Scale perishable prep/orders down to the adverse-weather forecast for {X} the day before.",
        expected_effect=f"Forecast-trimmed perishable prep cuts waste ~${X}/mo with no service impact on slow days.",
        recommend_when={"state": "weather_perishable_waste", "min_signal": "inventory_levels"},
        tags=("fusion", "weather", "waste", v.family),
    )


# ── 17. Reviews/reputation × conversion ───────────────────────────────────
def _reputation_revenue(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Review dips show up in your sales a few weeks later",
        observation=f"Rating moves of {X} stars precede {X}% swings in new-customer {v.sale_unit}s with a ~{X}-week lag.",
        reasoning=f"Reputation and revenue are tracked on different dashboards, so the causal lag between them goes unseen; joining the review timeline to new-customer sales makes reputation a leading indicator you can defend, turning a rating drop into an early revenue warning rather than a vanity metric.",
        conclusion=f"Treat a sustained rating dip as a revenue alert: trigger a service fix + review-recovery push the week it appears.",
        expected_effect=f"Defending reputation-driven traffic protects ~${X}/mo of new-customer revenue.",
        recommend_when={"state": "reputation_leads_revenue", "min_signal": "reviews"},
        tags=("fusion", "reviews", "revenue", v.family),
    )


# ── 18. Online orders × in-store pickup staffing ──────────────────────────
def _online_pickup_staffing(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Online pickup load collides with your thinnest floor coverage",
        observation=f"Online/pickup {v.sale_unit}s peak at {X}, but {v.staff_role} coverage is set to the in-store curve — fulfillment steals from the floor at {X}.",
        reasoning=f"Two demand streams (digital and walk-in) draw on one labor pool, and they peak at different times. Without joining the online order curve to the in-store schedule, pickup fulfillment quietly cannibalizes floor service exactly when both are busy — degrading both channels at once.",
        conclusion=f"Schedule a dedicated fulfillment role across the online peak so pickup doesn't pull the {v.staff_role} off the floor.",
        expected_effect=f"Protecting both channels at their joint peak is worth ~${X}/mo.",
        recommend_when={"state": "omnichannel_labor_collision", "min_signal": "online_orders"},
        tags=("fusion", "omnichannel", "staffing", v.family),
    )


# ── 19. Promo × margin (discount cannibalization) ─────────────────────────
def _promo_margin(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your promotion discounted sales that would have happened anyway",
        observation=f"During the {X} promo, {X} units moved at {X}% off, but baseline-adjusted incremental lift was only {X}% — the rest was margin given to existing demand.",
        reasoning=f"A promo's gross units look great until you join them to the margin table and a baseline; the cross separates true incremental sales from cannibalized full-price ones, exposing whether the discount bought new demand or just discounted demand you already had.",
        conclusion=f"Gate future {X} promos on incrementality: cap discount depth and target lapsed/new customers, not the full base.",
        expected_effect=f"Cutting cannibalized discount protects ~${X}/mo in margin.",
        recommend_when={"state": "promo_cannibalization", "min_signal": "promotions"},
        tags=("fusion", "promo", "margin", v.family),
    )


# ── 20. Membership usage × churn ──────────────────────────────────────────
def _membership_churn(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Falling visit frequency predicts the cancellation before it happens",
        observation=f"Members who drop below {X} visits/{X} cancel within {X} days at {X}x the rate of active members.",
        reasoning=f"Churn shows up in billing only after the member is already gone; joining visit/usage telemetry to the membership roster turns declining engagement into an early-warning score, so intervention happens while the relationship is still salvageable rather than at the cancel click.",
        conclusion=f"Trigger a win-back (a {v.staff_role} check-in, a re-onboarding offer) the moment a member crosses the low-usage threshold.",
        expected_effect=f"Saving at-risk members before they lapse protects ~${X}/mo of recurring revenue.",
        recommend_when={"state": "usage_predicts_churn", "min_signal": "membership_usage"},
        tags=("fusion", "membership", "churn", v.family),
    )


# ── 21. No-show × utilization × revenue ───────────────────────────────────
def _noshow_utilization(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"No-shows leave your {v.staff_role} capacity idle and unbilled",
        observation=f"{X}% no-show rate leaves {X} {v.core_kpis[1]}-hours empty/week — capacity that was reserved, staffed, and never earned.",
        reasoning=f"A no-show is worse than an empty slot you could have sold: the {v.staff_role} is on the clock, the room/chair/bay is committed, and the revenue is zero. Joining no-show events to utilization and revenue quantifies the idle-capacity cost, which justifies deposits or overbooking far better than the no-show count alone.",
        conclusion=f"Backfill no-show-prone slots with a standby list or measured overbooking, and require deposits on the riskiest.",
        expected_effect=f"Reclaiming idle capacity from no-shows is worth ~${X}/mo.",
        recommend_when={"state": "noshow_idle_capacity", "min_signal": "bookings"},
        tags=("fusion", "no_show", "utilization", v.family),
    )


# ── 22. Phone-missed × daypart × staffing ─────────────────────────────────
def _phone_daypart_staffing(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Calls drop exactly when the floor is busiest",
        observation=f"{X}% of missed calls cluster in the {X} window — the same hours vision shows peak footfall and the {v.staff_role} is heads-down.",
        reasoning=f"Missed calls aren't random; joining call logs to the footfall curve and the schedule shows the phone goes unanswered because the same understaffed peak is absorbing the in-store rush. One root cause (peak coverage) is bleeding two channels, which only the three-way join reveals.",
        conclusion=f"Route phones to an overflow/callback during the in-store peak, or add a {v.staff_role} who owns the phone at {X}.",
        expected_effect=f"Recovering peak-window missed calls is worth ~${X}/mo on top of the in-store fix.",
        recommend_when={"state": "missed_calls_at_peak", "min_signal": "call_logs"},
        tags=("fusion", "phone", "staffing", v.family),
    )


# ── 23. Product mix × margin × traffic ────────────────────────────────────
def _mix_margin_traffic(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"High traffic is pushing your lowest-margin items",
        observation=f"Your top-traffic hours over-index on {X} (your thinnest margin) — {X}% of peak {v.sale_unit}s, versus {X}% of margin.",
        reasoning=f"Volume and profit diverge by hour: the camera-confirmed peak drives mix toward fast, low-margin items, so your busiest hours generate revenue but thin profit. Joining the traffic curve to product margin shows where a merchandising or upsell nudge converts raw volume into actual money.",
        conclusion=f"Promote a higher-margin alternative at peak (placement, a {v.staff_role} prompt) to lift peak-hour margin mix.",
        expected_effect=f"Improving peak-hour margin mix is worth ~${X}/mo at the same traffic.",
        recommend_when={"state": "peak_low_margin_mix", "min_signal": "transactions"},
        tags=("fusion", "margin", "traffic", v.family),
    )


# ── 24. Weather × menu/category shift ─────────────────────────────────────
def _weather_mix(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Weather flips which categories sell — prep the other one",
        observation=f"On {X} days, {X} category share jumps {X}pts while {X} falls — but prep/stock is held flat across conditions.",
        reasoning=f"This is a mix shift, not a volume shift: joining the weather feed to category-level sales shows the same customers buying different things by condition, so flat prep over-makes the wrong category and under-makes the right one — a margin and waste problem distinct from weather's effect on total revenue.",
        conclusion=f"Shift the day's prep/stock toward the weather-favored category using the 1-day forecast.",
        expected_effect=f"Aligning category prep to weather mix is worth ~${X}/mo in waste avoided and sales captured.",
        recommend_when={"state": "weather_shifts_mix", "min_signal": "transactions"},
        tags=("fusion", "weather", "mix", v.family),
    )


# ── 25. Returns × product × margin ────────────────────────────────────────
def _returns_margin(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A few SKUs quietly erase their own margin in returns",
        observation=f"{X} accounts for {X}% of return volume; netted against its margin, its true contribution is {X}% below its gross.",
        reasoning=f"Returns are recorded as a lump and rarely netted back to the SKU that caused them; joining return line-items to product margin reveals items whose sticker margin is an illusion once returns, restocking, and handling are subtracted — sometimes a 'good seller' that loses money per net unit.",
        conclusion=f"Fix or delist the worst net-margin returners (sizing guidance, supplier swap, or drop) after confirming the cause.",
        expected_effect=f"Eliminating margin-negative return offenders protects ~${X}/mo.",
        recommend_when={"state": "returns_erode_margin", "min_signal": "returns"},
        tags=("fusion", "returns", "margin", v.family),
    )


# ── 26. Tips × staff performance × retention ──────────────────────────────
def _tip_retention(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your best earners are scheduled into your lowest-tip shifts",
        observation=f"Tip-per-hour varies {X}x by shift; {X} of your strongest {v.staff_role}s work the low-tip {X} block and turn over at {X}x the rate.",
        reasoning=f"Tip income is a retention driver you don't control directly but can schedule around; joining tip data to the {v.staff_role} roster and turnover exposes that you're parking top talent in low-tip windows — a self-inflicted churn risk on the people you most need, invisible until tips and the schedule are crossed.",
        conclusion=f"Rotate strong {v.staff_role}s through high-tip shifts equitably and watch retention on the historically low-tip block.",
        expected_effect=f"Reducing avoidable turnover among top {v.staff_role}s is worth ~${X}/mo in re-hire and ramp cost.",
        recommend_when={"state": "tip_inequity_churn", "min_signal": "tips"},
        tags=("fusion", "tips", "retention", v.family),
    )


# ── 27. Booking lead-time × booking value ─────────────────────────────────
def _leadtime_value(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your most valuable bookings are made furthest ahead — protect them",
        observation=f"{v.sale_unit.title()}s booked {X}+ days out average ${X}, versus ${X} for same-week bookings — and they're the easiest to lose to a slow response.",
        reasoning=f"Lead time correlates with value here: long-lead bookings are bigger, higher-intent jobs, so a missed deposit step or slow confirmation on them costs far more than on a walk-in. Joining lead time to booking value tells you where to spend your best responsiveness, instead of treating all inquiries the same.",
        conclusion=f"Fast-track and deposit-secure long-lead, high-value inquiries with a dedicated {v.staff_role} response SLA.",
        expected_effect=f"Protecting high-value long-lead bookings is worth ~${X}/mo.",
        recommend_when={"state": "leadtime_predicts_value", "min_signal": "bookings"},
        tags=("fusion", "booking", "value", v.family),
    )


# ── 28. Labor cost × revenue × footfall (true efficiency) ─────────────────
def _labor_efficiency(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your true labor efficiency hides until you join cost, sales, and traffic",
        observation=f"The {X} block looks productive on revenue, but per dollar of {v.staff_role} cost and per entrant it ranks {X} of your dayparts.",
        reasoning=f"Revenue-per-hour flatters busy expensive hours and punishes lean quiet ones; only joining scheduled labor cost, revenue, and vision footfall together yields revenue-per-labor-dollar-per-entrant — the metric that says whether an hour is actually efficient or just loud. The three-way ratio reranks your day.",
        conclusion=f"Rank dayparts by the joined efficiency ratio and reallocate {v.staff_role} hours from the worst-ranked to the best.",
        expected_effect=f"Reallocating to truly efficient hours is worth ~${X}/mo at flat total labor.",
        recommend_when={"state": "labor_efficiency_misread", "min_signal": "hourly_revenue"},
        tags=("fusion", "labor", "efficiency", v.family),
    )


# ── 29. Loyalty × recency × spend trend (lapsing VIPs) ────────────────────
def _vip_churn(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your VIPs are quietly fading before they leave",
        observation=f"{X} top-decile customers have stretched their visit gap {X}% and cut spend {X}% over {X} months — still 'active' but trending out.",
        reasoning=f"A VIP rarely cancels; they erode. Joining loyalty rank to recency and spend trend catches the slow fade while it's reversible — distinct from membership churn (a binary cancel), this is a high-value-customer early-warning on people who still buy but less, where a timely touch has outsized payback.",
        conclusion=f"Flag fading top-decile customers and trigger a personal {v.staff_role} outreach or tailored offer before the gap sets.",
        expected_effect=f"Re-engaging fading VIPs protects ~${X}/mo given their outsized lifetime value.",
        recommend_when={"state": "vip_fade", "min_signal": "loyalty_customers"},
        tags=("fusion", "loyalty", "recency", v.family),
    )


# ── 30. Occupancy × capacity × revenue (peak ceiling) ─────────────────────
def _capacity_revenue(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your peak revenue is capped by the room, not by demand",
        observation=f"At peak, occupancy holds at {X}% of capacity for {X} minutes while entries flatten and revenue plateaus despite rising passerby demand.",
        reasoning=f"Joining vision occupancy, a capacity constant, and revenue shows a hard ceiling: the store fills, turns customers away, and revenue stops climbing even though demand outside is still growing. This is a throughput-limited ceiling — distinct from a conversion problem — and it tells you the lever is faster turnover or more capacity, not more marketing.",
        conclusion=f"Lift the ceiling at peak (faster turns, a second service point, or extended peak hours) rather than driving more traffic into a full room.",
        expected_effect=f"Raising the peak throughput ceiling is worth ~${X}/mo of demand currently turned away.",
        recommend_when={"state": "capacity_revenue_ceiling", "min_signal": "vision_traffic"},
        tags=("fusion", "occupancy", "revenue", v.family),
    )


register(
    Archetype(
        key="fusion_footfall_conv_staffing", domain="fusion", name="Understaffing → walkouts",
        build=_footfall_conv_staffing, situations=("baseline", "seasonal_peak"),
        required_signals=("vision_traffic", "schedule_shifts", "transactions"),
        required_agents=("FootfallLaborFusionAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="FootfallLaborFusionAgent: join vision_traffic.entries + .conversion_rate to schedule_shifts headcount on store-hour, regress conversion/walkouts on entries-per-staff → emit 'staffing_walkout_loss' signal (vision + schedule exist separately; the join is new).",
    ),
    Archetype(
        key="fusion_weather_revenue", domain="fusion", name="Weather drives revenue",
        build=_weather_revenue, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("hourly_revenue", "weather_feed"),
        required_agents=("WeatherRevenueAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherRevenueAgent: ingest a weather feed (forecast + actuals), join to hourly_revenue on date/location, regress revenue on conditions → emit 'weather_revenue_elasticity' + a 3-day revenue forecast (no weather source ingested yet — new feed).",
    ),
    Archetype(
        key="fusion_phone_missed_revenue", domain="fusion", name="Missed calls = lost revenue",
        build=_phone_missed_revenue, situations=("baseline",),
        required_signals=("call_logs", "transactions"),
        required_agents=("PhoneRevenueRecoveryAgent",),
        applies_families=PHONE_FAMILIES,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PhoneRevenueRecoveryAgent: ingest call_logs (answered/missed + timestamps), multiply missed-call count by phone-channel conversion × avg ticket → emit 'missed_call_revenue_loss' by daypart (call logs not yet ingested — new telephony source).",
    ),
    Archetype(
        key="fusion_stockout_on_peak", domain="fusion", name="Stockout meets forecast peak",
        build=_stockout_on_peak, situations=("baseline", "seasonal_peak"),
        required_signals=("inventory_levels", "demand_forecast"),
        required_agents=("StockoutForecastAgent",),
        applies_flags=("inventory_heavy",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StockoutForecastAgent: join inventory_levels (on-hand + depletion rate) to demand_forecast per SKU, project depletion date against forecasted peak date → emit 'stockout_on_peak' alert (inventory exists; SKU-level forecast join is the upgrade).",
    ),
    Archetype(
        key="fusion_loyalty_margin", domain="fusion", name="Top customers buy low margin",
        build=_loyalty_margin, situations=("baseline",),
        required_signals=("loyalty_customers", "product_margin", "transactions"),
        required_agents=("LoyaltyMarginAgent",),
        applies_flags=("repeat_purchase",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LoyaltyMarginAgent: join loyalty_customers spend rank to transaction line-items to product_margin → emit per-decile margin-mix so top spenders' profit contribution is ranked (product_margin table not yet ingested).",
    ),
    Archetype(
        key="fusion_staff_attach", domain="fusion", name="Who actually upsells",
        build=_staff_attach, situations=("baseline",),
        required_signals=("transactions", "schedule_shifts"),
        required_agents=("StaffAttachAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="StaffAttachAgent: attribute transaction line-items to the ringing/serving employee (employee_id on transactions or shift-overlap join), compute attach rate per staff → emit 'attach_rate_by_staff' (employee attribution not yet available).",
    ),
    Archetype(
        key="fusion_daypart_prep", domain="fusion", name="Prep vs daypart mismatch",
        build=_daypart_prep, situations=("baseline",),
        required_signals=("inventory_levels", "hourly_revenue"),
        required_agents=("PrepDemandAgent",),
        applies_flags=("perishable",), exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PrepDemandAgent: join the by-hour sales curve (hourly_revenue/transactions) to the prep/inventory plan per item → emit a daypart-batched prep schedule that minimizes waste + stockout (sales curve exists; prep-plan join is the upgrade).",
    ),
    Archetype(
        key="fusion_footfall_weather", domain="fusion", name="Forecast tomorrow's footfall",
        build=_footfall_weather, situations=("baseline",),
        required_signals=("vision_traffic", "weather_feed"),
        required_agents=("WeatherFootfallAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherFootfallAgent: join vision_traffic.entries history to the weather feed on date/location, fit a lagged elasticity model → emit a next-day entry forecast feeding scheduling/ordering (no weather feed ingested yet).",
    ),
    Archetype(
        key="fusion_leadtime_noshow", domain="fusion", name="Lead time predicts no-show",
        build=_leadtime_noshow, situations=("baseline",),
        required_signals=("bookings",),
        required_agents=("BookingRiskAgent",),
        applies_flags=("appointment_based",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingRiskAgent: join each booking's lead time (created_at → appointment_at) to its no-show outcome → emit a per-slot no-show risk score driving deposit/overbook rules (bookings exist; lead-time→outcome model is the upgrade).",
    ),
    Archetype(
        key="fusion_payment_basket", domain="fusion", name="Payment type vs basket",
        build=_payment_basket, situations=("baseline",),
        required_signals=("payments", "transactions"),
        required_agents=("PaymentBasketAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PaymentBasketAgent: join the payments stream (tender type) to transaction basket value on transaction_id → emit avg basket by tender and the steerable gap (payments + transactions exist; tender↔basket join is the upgrade).",
    ),
    Archetype(
        key="fusion_event_staffing", domain="fusion", name="Events vs staffing",
        build=_event_staffing, situations=("baseline", "seasonal_peak"),
        required_signals=("events_calendar", "schedule_shifts", "transactions"),
        required_agents=("EventStaffingAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="EventStaffingAgent: ingest a local events/holiday calendar, join event dates to historical sales uplift and to scheduled headcount → emit 'event_coverage_gap' per upcoming flagged day (events_calendar not yet ingested).",
    ),
    Archetype(
        key="fusion_queue_revenue", domain="fusion", name="Queue cost in dollars",
        build=_queue_revenue, situations=("baseline", "seasonal_peak"),
        required_signals=("vision_traffic", "transactions"),
        required_agents=("QueueRevenueAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="QueueRevenueAgent: join vision_traffic.queue_wait_avg_sec + balk counts to avg ticket → emit '$/day lost to queue' and the wait threshold where a second register pays for itself (queue wait exists; balk×ticket monetization is the upgrade).",
    ),
    Archetype(
        key="fusion_recency_campaign", domain="fusion", name="Campaign timing vs recency",
        build=_recency_campaign, situations=("baseline",),
        required_signals=("loyalty_customers", "campaigns"),
        required_agents=("RecencyCampaignAgent",),
        applies_flags=("repeat_purchase",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RecencyCampaignAgent: join per-customer repurchase recency to campaign send/response logs → emit a per-customer optimal-send window keyed to fading intent (campaign send/response logs not yet ingested).",
    ),
    Archetype(
        key="fusion_demo_product", domain="fusion", name="Visitor demographics vs mix",
        build=_demo_product, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("DemographicMerchAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DemographicMerchAgent: join coarse vision demographic estimates to product-mix/space allocation per store → emit assortment-vs-audience mismatch by segment (demographic vision estimation not yet enabled — privacy-gated).",
    ),
    Archetype(
        key="fusion_peak_supplier", domain="fusion", name="Lead time vs peak warning",
        build=_peak_supplier, situations=("baseline", "seasonal_peak"),
        required_signals=("demand_forecast", "inventory_levels", "supplier_leadtime"),
        required_agents=("SupplierLeadAgent",),
        applies_flags=("inventory_heavy",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="SupplierLeadAgent: join per-supplier lead time to demand_forecast peak dates, compute order-by = peak_date − lead_time per SKU → emit 'order_by_alert' (supplier lead time per SKU not yet ingested).",
    ),
    Archetype(
        key="fusion_weather_waste", domain="fusion", name="Weather-driven perishable waste",
        build=_weather_waste, situations=("baseline", "seasonal_trough"),
        required_signals=("weather_feed", "inventory_levels"),
        required_agents=("WeatherWasteAgent",),
        applies_flags=("perishable",), exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherWasteAgent: join the weather forecast to perishable prep/order plans and historical waste → emit a forecast-trimmed prep quantity per item the day before (weather feed not yet ingested).",
    ),
    Archetype(
        key="fusion_reputation_revenue", domain="fusion", name="Reviews lead revenue",
        build=_reputation_revenue, situations=("baseline", "declining"),
        required_signals=("reviews", "transactions"),
        required_agents=("ReputationRevenueAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReputationRevenueAgent: ingest review/rating timeline, join (lagged) to new-customer transaction counts → emit a rating→revenue lead indicator with the fitted lag (review feed not yet ingested).",
    ),
    Archetype(
        key="fusion_online_pickup_staffing", domain="fusion", name="Online pickup vs floor staffing",
        build=_online_pickup_staffing, situations=("baseline",),
        required_signals=("online_orders", "schedule_shifts"),
        required_agents=("OmnichannelLaborAgent",),
        applies_flags=("delivery_capable",), exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="OmnichannelLaborAgent: join the online/pickup order curve to schedule_shifts floor coverage on store-hour → emit hours where fulfillment load exceeds spare floor labor (online_orders + schedule exist; the dual-demand join is new).",
    ),
    Archetype(
        key="fusion_promo_margin", domain="fusion", name="Promo cannibalization",
        build=_promo_margin, situations=("baseline",),
        required_signals=("promotions", "product_margin", "transactions"),
        required_agents=("PromoMarginAgent",),
        applies_flags=("inventory_heavy",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PromoMarginAgent: join promotion periods to baseline-adjusted unit lift and product_margin → emit incremental-vs-cannibalized split and net margin per promo (promotions + product_margin not yet ingested).",
    ),
    Archetype(
        key="fusion_membership_churn", domain="fusion", name="Usage predicts churn",
        build=_membership_churn, situations=("baseline",),
        required_signals=("membership_usage", "loyalty_customers"),
        required_agents=("MembershipChurnAgent",),
        applies_flags=("membership",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MembershipChurnAgent: join visit/usage telemetry to the membership roster + cancellation outcomes → emit a low-usage early-warning churn score per member (usage telemetry per member not yet ingested).",
    ),
    Archetype(
        key="fusion_noshow_utilization", domain="fusion", name="No-shows idle capacity",
        build=_noshow_utilization, situations=("baseline",),
        required_signals=("bookings", "transactions"),
        required_agents=("UtilizationRecoveryAgent",),
        applies_flags=("appointment_based",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="UtilizationRecoveryAgent: join no-show events to chair/bay/room utilization and the revenue that slot would have earned → emit '$ idle capacity from no-shows' driving overbook/deposit policy (bookings exist; utilization×revenue cost join is the upgrade).",
    ),
    Archetype(
        key="fusion_phone_daypart_staffing", domain="fusion", name="Missed calls at peak",
        build=_phone_daypart_staffing, situations=("baseline",),
        required_signals=("call_logs", "vision_traffic", "schedule_shifts"),
        required_agents=("PhoneStaffingAgent",),
        applies_families=("food_service", "personal_care", "automotive"), exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PhoneStaffingAgent: join missed-call timestamps to vision footfall peaks and schedule_shifts coverage → emit 'calls dropped due to in-store peak' linking one root cause to two channels (call logs not yet ingested).",
    ),
    Archetype(
        key="fusion_mix_margin_traffic", domain="fusion", name="Peak traffic low margin",
        build=_mix_margin_traffic, situations=("baseline",),
        required_signals=("transactions", "product_margin", "vision_traffic"),
        required_agents=("MixMarginTrafficAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MixMarginTrafficAgent: join the vision/sales traffic curve to product_margin per hour → emit peak-hour margin-mix and the upsell target that converts volume to profit (product_margin not yet ingested).",
    ),
    Archetype(
        key="fusion_weather_mix", domain="fusion", name="Weather shifts category mix",
        build=_weather_mix, situations=("baseline",),
        required_signals=("weather_feed", "transactions"),
        required_agents=("WeatherMixAgent",),
        applies_flags=("perishable",), exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherMixAgent: join the weather feed to category-level sales share → emit the weather-conditioned mix shift driving daily prep/stock reallocation (weather feed not yet ingested).",
    ),
    Archetype(
        key="fusion_returns_margin", domain="fusion", name="Returns erase margin",
        build=_returns_margin, situations=("baseline",),
        required_signals=("returns", "product_margin"),
        required_agents=("ReturnsMarginAgent",),
        applies_families=("retail",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReturnsMarginAgent: join return line-items back to the SKU and net against product_margin + handling cost → emit true net margin per SKU and margin-negative returners (returns + product_margin not yet ingested).",
    ),
    Archetype(
        key="fusion_tip_retention", domain="fusion", name="Tip inequity vs retention",
        build=_tip_retention, situations=("baseline",),
        required_signals=("tips", "schedule_shifts"),
        required_agents=("TipEquityAgent",),
        applies_flags=("tipped",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TipEquityAgent: join tip-per-hour to the staff roster and turnover outcomes → emit shift-level tip inequity and its correlation with attrition among top performers (tip data per shift not yet ingested).",
    ),
    Archetype(
        key="fusion_leadtime_value", domain="fusion", name="Lead time predicts value",
        build=_leadtime_value, situations=("baseline",),
        required_signals=("bookings", "transactions"),
        required_agents=("LeadValueAgent",),
        applies_keys=("hvac", "plumbing", "event_venue", "med_spa", "tattoo", "auto_repair"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LeadValueAgent: join booking lead time to the realized job/booking value → emit value-by-lead-time so high-value long-lead inquiries get a response SLA (bookings exist; lead-time→value join is the upgrade).",
    ),
    Archetype(
        key="fusion_labor_efficiency", domain="fusion", name="True labor efficiency",
        build=_labor_efficiency, situations=("baseline",),
        required_signals=("hourly_revenue", "schedule_shifts", "vision_traffic"),
        required_agents=("LaborEfficiencyFusionAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LaborEfficiencyFusionAgent: join scheduled labor cost + hourly_revenue + vision entries per hour → emit revenue-per-labor-dollar-per-entrant and a reranked daypart efficiency table (all three exist separately; the three-way ratio is new).",
    ),
    Archetype(
        key="fusion_vip_churn", domain="fusion", name="Fading VIPs",
        build=_vip_churn, situations=("baseline", "declining"),
        required_signals=("loyalty_customers", "transactions"),
        required_agents=("VIPChurnAgent",),
        applies_flags=("repeat_purchase",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VIPChurnAgent: join loyalty top-decile rank to recency + spend-trend slope → emit a fading-VIP early-warning list before the cancel/lapse (loyalty + transactions exist; the recency×spend-trend fade model is the upgrade).",
    ),
    Archetype(
        key="fusion_capacity_revenue", domain="fusion", name="Peak revenue ceiling",
        build=_capacity_revenue, situations=("baseline", "seasonal_peak"),
        required_signals=("vision_traffic", "hourly_revenue"),
        required_agents=("CapacityRevenueAgent",),
        applies_families=FLOOR_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CapacityRevenueAgent: join vision_traffic.occupancy + a capacity constant + hourly_revenue → detect minutes where occupancy saturates while revenue plateaus and entries flatten → emit 'throughput_revenue_ceiling' (occupancy + revenue exist; the saturation-plateau join is new).",
    ),
)
