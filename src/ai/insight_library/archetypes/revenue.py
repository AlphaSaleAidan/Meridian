"""
Domain: REVENUE.

Each archetype is a distinct reasoning pattern about the top line: its level,
trend, mix, concentration, growth, intra-week/intra-month composition, average
ticket, and revenue extracted per unit of capacity. Distinctness is structural,
never numeric — two patterns that differ only by a threshold are the SAME
archetype with a different `{x}`.

Specialization per vertical changes the lever, the KPI, and the action: a cafe's
"raise the average ticket" is an attach/upsell move on a $5 drink, a salon's is a
service-tier / retail-attach move on an appointment, an auto shop's is an
approved-estimate move on a repair order, an HVAC's is a membership/first-visit
close. The reasoning is genuinely different, not a relabel.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── small specialization helpers ─────────────────────────────────────────
def _capacity_unit(v: Vertical) -> str:
    """The physical unit that bounds revenue for this vertical."""
    if v.key in ("auto_repair", "oil_change", "tire_shop"):
        return "bay"
    if v.key == "car_wash":
        return "lane"
    if v.key in ("spa", "med_spa", "physio", "chiro", "dental", "optometry", "vet"):
        return "room"
    if v.key in ("gym", "crossfit", "yoga_studio"):
        return "class slot"
    if v.key in ("salon", "barbershop", "nail_salon", "tattoo"):
        return "chair"
    if "table_service" in v.flags:
        return "seat"
    if v.key == "event_venue":
        return "date"
    return "station"


def _ticket_lever(v: Vertical, situation: str) -> str:
    """Vertical-specific way to move the value of one sale."""
    if v.family == "food_service":
        return f"a {v.core_kpis[-1] if v.core_kpis else 'attach'} push — pair every {v.sale_unit} with a high-margin add-on at the {v.staff_role} prompt"
    if v.family in ("personal_care", "health_wellness"):
        return f"a service-tier + retail-attach script so each {v.sale_unit} carries an upgrade or take-home product"
    if v.family == "retail":
        return f"a basket-builder placement (impulse + bundle) so each {v.sale_unit} adds a unit"
    if v.family == "automotive":
        return f"a multi-point inspection that lifts the approved-estimate value of each {v.sale_unit}"
    if v.family == "home_services":
        return f"a good/better/best estimate so each {v.sale_unit} presents a premium option"
    return f"an upsell prompt at the point of the {v.sale_unit}"


def _channel_pick(v: Vertical) -> str:
    """The channel most likely to be over-concentrated for this vertical."""
    if "delivery" in v.channels:
        return "delivery"
    if "online" in v.channels:
        return "online"
    if "booking" in v.channels:
        return "booking"
    if "drive_thru" in v.channels:
        return "drive-thru"
    return v.channels[0]


# ── archetypes ───────────────────────────────────────────────────────────
def _declining_trend(v: Vertical, situation: str) -> Built:
    kpi = v.core_kpis[0]
    if situation == "anomaly":
        conclusion = (
            f"Treat the {X}-week drop as a break, not a trend: check for a one-off cause "
            f"(a lost {v.sale_unit} source, a {kpi} swing, a local disruption) before changing the plan."
        )
        effect = f"Pinpointing the cause this week protects the ~${X}/mo run-rate from compounding."
    else:
        conclusion = (
            f"Counter the slide where it started — {_ticket_lever(v, situation)} — and re-test {kpi} weekly "
            f"rather than discounting across the board."
        )
        effect = f"Arresting the {X}%/mo decline preserves ~${X}/mo before it compounds into a cash problem."
    return Built(
        title=f"Revenue has fallen {X}% over the last {X} weeks",
        observation=f"Weekly {v.sale_unit} revenue dropped from ${X} to ${X} across {X} consecutive weeks — a real trend, not noise.",
        reasoning=f"A sustained top-line decline at {v.name} compounds: fixed {v.staff_role} and occupancy costs stay flat while the contribution that covers them shrinks, so margin erodes faster than revenue.",
        conclusion=conclusion,
        expected_effect=effect,
        recommend_when={"state": "declining_revenue_trend", "min_signal": "daily_revenue"},
        tags=("revenue", "trend", "decline", v.family),
    )


def _surging_trend(v: Vertical, situation: str) -> Built:
    cap = _capacity_unit(v)
    return Built(
        title=f"Revenue is surging {X}% — capitalize before it plateaus",
        observation=f"Weekly {v.sale_unit} revenue climbed {X}% over {X} weeks, with the gain concentrated in {X}.",
        reasoning=f"Demand is outrunning your current setup: if {v.staff_role} hours and {cap} availability don't scale with it, the surge converts into wait, turn-aways, and a hard revenue ceiling instead of growth.",
        conclusion=f"Lock the gain in — add {cap} capacity and {v.staff_role} hours into the rising window, and capture contact info now so the new {v.sale_unit} demand becomes repeat.",
        expected_effect=f"Scaling with the surge instead of capping it is worth an extra ~${X}/mo while the tailwind lasts.",
        recommend_when={"state": "surging_revenue_trend", "min_signal": "daily_revenue"},
        tags=("revenue", "trend", "growth", v.family),
    )


def _concentration_one_day(v: Vertical, situation: str) -> Built:
    if situation == "concentrated":
        conclusion = (
            f"De-risk it: a single bad {X} (weather, closure, a competitor event) takes out {X}% of the week, "
            f"so build a second peak — drive {v.sale_unit} demand into your weakest day with a standing offer."
        )
    else:
        conclusion = f"Lean in where it's strongest: staff and stock {X} fully, then test moving its winning format onto your flat days."
    return Built(
        title=f"{X}% of your revenue lands on a single day ({X})",
        observation=f"{X} alone produces ${X} of weekly revenue while your slowest day produces ${X} — a {X}x spread.",
        reasoning=f"Revenue riding on one day is fragile and caps growth: {v.staff_role} capacity and {_capacity_unit(v)} availability are saturated that day (no upside) and idle the rest (paid, unproductive).",
        conclusion=conclusion,
        expected_effect=f"Shifting even {X}% of the peak-day demand to a flat day adds ~${X}/mo without new capacity.",
        recommend_when={"state": "single_day_concentration", "min_signal": "daily_revenue"},
        tags=("revenue", "concentration", "day_of_week", v.family),
    )


def _concentration_product_class(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"One product class drives {X}% of revenue",
        observation=f"The {X} category produces ${X} — {X}% of revenue — while {X} other categories together make {X}%.",
        reasoning=f"Single-category dependence at {v.name} is a supply and margin risk: a price hike, stockout, or trend shift in {X} hits most of the top line at once, and {v.staff_role}s aren't trained to redirect demand elsewhere.",
        conclusion=f"Protect it and broaden it — secure {X} supply/pricing, then grow the #2 category with a {v.staff_role} cross-sell so no single class exceeds {X}% of revenue.",
        expected_effect=f"Lifting the #2 category by {X}% diversifies ~${X}/mo of concentration risk into resilient revenue.",
        recommend_when={"state": "product_class_concentration", "min_signal": "product_performance"},
        tags=("revenue", "concentration", "mix", v.family),
        applies_flags=("inventory_heavy",),
    )


def _avg_ticket_erosion(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Average {v.sale_unit} value has eroded {X}%",
        observation=f"Average {v.sale_unit} value slid from ${X} to ${X} even though {v.sale_unit} count held steady at {X}/wk.",
        reasoning=f"Flat traffic with a falling ticket means each visit buys less — a mix/attach problem, not a demand problem. The same {v.staff_role} effort and {_capacity_unit(v)} turn now yields less, so per-visit economics quietly decay.",
        conclusion=f"Rebuild ticket value with {_ticket_lever(v, situation)}; measure recovery against the ${X} baseline weekly.",
        expected_effect=f"Restoring ${X} of the lost ticket across {X} weekly {v.sale_unit}s recovers ~${X}/mo at near-zero added cost.",
        recommend_when={"state": "average_ticket_erosion", "min_signal": "transactions"},
        tags=("revenue", "average_ticket", "mix", v.family),
    )


def _avg_ticket_expansion(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Room to raise the average {v.sale_unit} — demand isn't price-sensitive here",
        observation=f"Your average {v.sale_unit} is ${X}, but {X}% of {v.sale_unit}s already buy the premium option and reorder rate held flat the last {X} price tests.",
        reasoning=f"When customers absorb price without dropping frequency, you're leaving margin on the table: at {v.name} the {v.sale_unit} value can rise faster than volume falls, so a measured increase flows almost entirely to contribution.",
        conclusion=f"Test a {X}% lift on the most-ordered {v.sale_unit} (or add a clearly-better premium tier) for {X} weeks and watch volume; roll back only if {v.sale_unit} count falls more than {X}%.",
        expected_effect=f"A {X}% ticket lift that holds volume adds ~${X}/mo straight to the bottom line.",
        recommend_when={"state": "ticket_expansion_headroom", "min_signal": "transactions"},
        tags=("revenue", "average_ticket", "pricing", v.family),
    )


def _weekday_weekend_imbalance(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your weekdays and weekends are badly out of balance",
        observation=f"Weekends produce ${X}/day vs weekdays at ${X}/day — a {X}x gap — yet you run nearly the same {v.staff_role} schedule both.",
        reasoning=f"A lopsided week wastes capacity twice: weekends hit a {_capacity_unit(v)} ceiling (lost demand) while weekdays burn fixed {v.staff_role} and occupancy cost against thin {v.sale_unit} flow.",
        conclusion=f"Build a weekday reason-to-visit (a midweek {v.sale_unit} offer or {v.core_kpis[0]} driver) and add weekend {_capacity_unit(v)} capacity — converge the two toward your blended average.",
        expected_effect=f"Closing half the weekday gap adds ~${X}/mo from already-paid-for fixed capacity.",
        recommend_when={"state": "weekday_weekend_imbalance", "min_signal": "daily_revenue"},
        tags=("revenue", "composition", "day_of_week", v.family),
    )


def _revenue_per_capacity(v: Vertical, situation: str) -> Built:
    cap = _capacity_unit(v)
    util = next((k for k in v.core_kpis if "util" in k or "fill" in k or "turn" in k), v.core_kpis[0])
    return Built(
        title=f"Revenue per {cap} is below what your space can yield",
        observation=f"Each {cap} generates ${X}/day against a realistic ${X} potential; {util} sits at {X}% vs a healthy {X}%.",
        reasoning=f"The {cap} is your scarcest asset at {v.name} — rent and {v.staff_role} cost are paid per {cap} whether it's productive or not, so under-yielded {cap}s are pure margin leakage, not a volume problem you can't fix.",
        conclusion=f"Lift yield per {cap}: tighten {v.sale_unit} duration/turn, fill the gaps with {v.core_kpis[0]}, and price the highest-demand {cap}-time at a premium before adding any new {cap}.",
        expected_effect=f"Closing the {cap}-yield gap on existing space is worth ~${X}/mo with zero added rent.",
        recommend_when={"state": "low_revenue_per_capacity_unit", "min_signal": "capacity_config"},
        tags=("revenue", "capacity", "yield", v.family),
        applies_flags=(),
        applies_families=("food_service", "personal_care", "health_wellness", "fitness", "automotive", "hospitality"),
    )


def _single_customer_dependence(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"One customer accounts for {X}% of revenue",
        observation=f"Your top account books ${X} — {X}% of revenue — and your top {X} customers together make {X}%.",
        reasoning=f"Concentrated customer revenue is existential at {v.name}: losing one {v.sale_unit} relationship erases a quarter of the business overnight, and that account knows it holds pricing leverage over you.",
        conclusion=f"Reduce the dependence deliberately — protect the anchor with a service agreement, and run a {X}-week acquisition push so no single customer exceeds {X}% of revenue.",
        expected_effect=f"Diversifying ${X} of concentrated revenue removes a single-point-of-failure worth {X}% of the business.",
        recommend_when={"state": "single_customer_dependence", "min_signal": "customer_revenue"},
        tags=("revenue", "concentration", "customer", v.family),
        applies_flags=("high_ticket",),
        applies_families=("home_services", "hospitality", "automotive"),
    )


def _flat_revenue_rising_costs(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Flat revenue, rising costs — your margin is being squeezed",
        observation=f"Revenue held at ${X}/mo for {X} months while {v.staff_role} wages and {v.core_kpis[-1] if v.core_kpis else 'input'} costs rose {X}%.",
        reasoning=f"Stable top line is not safe when costs climb underneath it: at {v.name} the gap between a frozen {v.sale_unit} price and rising input cost comes straight out of contribution, so profit falls even though sales look fine.",
        conclusion=f"Reopen the price/cost gap — a {X}% {v.sale_unit} price step plus a menu/mix trim of the lowest-margin items — rather than chasing volume that won't cover the new cost base.",
        expected_effect=f"Restoring the eroded margin point is worth ~${X}/mo even with revenue dead flat.",
        recommend_when={"state": "margin_squeeze_flat_revenue", "min_signal": "daily_revenue"},
        tags=("revenue", "margin", "pricing", v.family),
    )


def _intra_month_skew(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Revenue is front/back-loaded within the month",
        observation=f"The first half of the month produces {X}% of revenue and the second half {X}% — a swing that repeats every month.",
        reasoning=f"Predictable intra-month skew is a cash-timing risk at {v.name}: payroll and supplier terms hit on a fixed cadence, so a thin half-month forces avoidable cash crunches even when the monthly total is healthy.",
        conclusion=f"Smooth the trough — time a {v.sale_unit} promotion or {v.core_kpis[0]} push into the weak half, and align supplier/payroll dates to the cash curve.",
        expected_effect=f"Smoothing the cycle frees ~${X} of working capital and avoids ${X} in crunch-driven costs.",
        recommend_when={"state": "intra_month_revenue_skew", "min_signal": "daily_revenue"},
        tags=("revenue", "composition", "cashflow", v.family),
    )


def _event_spike_unprepared(v: Vertical, situation: str) -> Built:
    cap = _capacity_unit(v)
    return Built(
        title=f"Holiday/event revenue spikes hit you unprepared",
        observation=f"Around {X}, {v.sale_unit} demand jumps {X}% for {X} days, but {v.staff_role} hours and inventory stayed at normal levels last cycle.",
        reasoning=f"A known, repeating spike you don't staff or stock for is captured demand thrown away: at {v.name} the {cap} ceiling and stockouts cap the very window with the year's best margin.",
        conclusion=f"Pre-plan the next spike — pre-order inventory, pre-book {v.staff_role} hours, and pre-sell where you can ({_channel_pick(v)}), so the peak is provisioned before it arrives.",
        expected_effect=f"Fully capturing the spike instead of capping it is worth ~${X} in that single window.",
        recommend_when={"state": "event_spike_unprepared", "min_signal": "daily_revenue"},
        tags=("revenue", "seasonal", "event", v.family),
        applies_flags=("seasonal",),
    )


def _refund_adjusted_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Refunds and voids are quietly eating {X}% of revenue",
        observation=f"Gross revenue is ${X} but refunds/voids total ${X} ({X}%), concentrated in {X} {v.sale_unit}s and {X} {v.staff_role}(s).",
        reasoning=f"Refunds are a double loss at {v.name}: you eat the {v.sale_unit} cost AND a dissatisfied customer, and a refund clustered on one product or {v.staff_role} usually signals a fixable quality/process defect, not random chance.",
        conclusion=f"Attack the cluster — fix the top refund-driving {v.sale_unit}/{v.staff_role} root cause rather than treating refunds as cost of doing business.",
        expected_effect=f"Halving the refund rate recovers ~${X}/mo of net revenue plus the retained customers behind it.",
        recommend_when={"state": "refund_revenue_leak", "min_signal": "refunds"},
        tags=("revenue", "net_revenue", "leakage", v.family),
        swarm_capability=SwarmCapability.MISSING,
    )


def _discount_net_erosion(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Discounts and comps are eroding net revenue more than they earn",
        observation=f"Discounts/comps ran ${X} ({X}% of gross) but the discounted {v.sale_unit}s show no better repeat rate than full-price ones.",
        reasoning=f"A discount only pays for itself if it buys incremental volume or loyalty; at {v.name} discounting demand that would have bought anyway just transfers margin to the customer for nothing.",
        conclusion=f"Tighten discounting to where it earns its keep — gate offers to new {v.sale_unit}s or slow windows, and kill blanket markdowns that hit full-price-willing buyers.",
        expected_effect=f"Reclaiming half the unproductive discount is worth ~${X}/mo of recovered margin.",
        recommend_when={"state": "discount_net_erosion", "min_signal": "discounts"},
        tags=("revenue", "net_revenue", "pricing", v.family),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DiscountAttributionAgent: join discounts/comps to transactions and customer repeat behavior to separate incremental discounts from margin-giveaway discounts.",
    )


def _new_vs_repeat_split(v: Vertical, situation: str) -> Built:
    if situation == "leaking":
        conclusion = (
            f"Your repeat base is thinning — plug it first: a {v.core_kpis[0]} / win-back flow to lapsing "
            f"customers protects the cheap revenue before you spend to acquire new {v.sale_unit}s."
        )
    else:
        conclusion = (
            f"Rebalance toward repeat — capture contact at the {v.sale_unit} and run a return offer; "
            f"repeat revenue at {v.name} costs a fraction of new-customer acquisition."
        )
    return Built(
        title=f"Revenue leans too hard on new customers ({X}% new vs {X}% repeat)",
        observation=f"{X}% of revenue comes from first-time {v.sale_unit}s and only {X}% from returning customers — repeat share is falling {X}% per quarter.",
        reasoning=f"A business that lives on new customers is on a treadmill: acquisition is the most expensive revenue there is, and at {v.name} a thin repeat base means every month restarts near zero instead of compounding.",
        conclusion=conclusion,
        expected_effect=f"Lifting repeat share by {X} points converts ~${X}/mo of expensive new revenue into cheap recurring revenue.",
        recommend_when={"state": "new_vs_repeat_imbalance", "min_signal": "customer_segments"},
        tags=("revenue", "mix", "retention", v.family),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CustomerCohortAgent: classify transactions as new vs returning via customer_id/contact and track repeat-revenue share over time.",
    )


def _week_volatility(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Week-to-week revenue is highly volatile (±{X}%)",
        observation=f"Weekly revenue swings between ${X} and ${X} with no clear seasonal cause — a coefficient of variation around {X}%.",
        reasoning=f"Unpredictable swings are operationally expensive at {v.name}: you can't right-size {v.staff_role} hours or inventory against a moving target, so you overspend in thin weeks and miss demand in fat ones.",
        conclusion=f"Find and dampen the driver — identify what separates fat from thin weeks ({v.core_kpis[0]}, {_channel_pick(v)}, weather), then build a baseline demand floor so the swing narrows.",
        expected_effect=f"Cutting variance lets you trim ~${X}/mo of buffer overspend and stop missing peaks.",
        recommend_when={"state": "weekly_revenue_volatility", "min_signal": "weekly_revenue"},
        tags=("revenue", "volatility", v.family),
    )


def _daypart_imbalance(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"One daypart carries the business while others run empty",
        observation=f"The {X} daypart produces {X}% of daily revenue; the {X} daypart produces {X}% on the same fixed cost base.",
        reasoning=f"At {v.name} you pay rent and a {v.staff_role} floor across all open hours — a dead daypart is fully-loaded cost against almost no {v.sale_unit}s, the cheapest revenue you could add because the doors are already open.",
        conclusion=f"Build a reason-to-visit for the dead daypart (a daypart-specific {v.sale_unit} or {v.core_kpis[-1] if v.core_kpis else 'offer'}) before touching the peak that's already maxed.",
        expected_effect=f"Lifting the weak daypart to even half the peak adds ~${X}/mo on already-paid-for hours.",
        recommend_when={"state": "daypart_revenue_imbalance", "min_signal": "hourly_revenue"},
        tags=("revenue", "composition", "daypart", v.family),
        applies_families=("food_service", "retail", "hospitality"),
    )


def _capacity_ceiling(v: Vertical, situation: str) -> Built:
    cap = _capacity_unit(v)
    util = next((k for k in v.core_kpis if "util" in k or "fill" in k or "turn" in k), v.core_kpis[0])
    return Built(
        title=f"You're hitting a {cap} ceiling — revenue can't grow without more capacity",
        observation=f"{util} runs at {X}% during peak windows and {v.sale_unit} demand is being turned away ${X}/wk; revenue has flatlined at ${X}/mo.",
        reasoning=f"When the {cap} is full at peak, marketing and pricing can't add revenue — only capacity can. At {v.name} the flat top line isn't weak demand, it's a hard physical ceiling.",
        conclusion=f"Add throughput at the constraint — extend the peak window, speed {v.sale_unit} turn, or add a {cap} — then re-test demand; don't spend on acquisition that has nowhere to land.",
        expected_effect=f"Adding {X}% peak {cap} capacity converts turned-away demand into ~${X}/mo of new revenue.",
        recommend_when={"state": "capacity_revenue_ceiling", "min_signal": "capacity_config"},
        tags=("revenue", "capacity", "ceiling", v.family),
        applies_families=("food_service", "personal_care", "health_wellness", "fitness", "automotive", "hospitality"),
    )


def _channel_concentration(v: Vertical, situation: str) -> Built:
    ch = _channel_pick(v)
    return Built(
        title=f"{X}% of revenue flows through one channel ({ch})",
        observation=f"{ch} produces ${X} — {X}% of revenue — and that share has grown {X} points while other channels stalled.",
        reasoning=f"Channel concentration hands a third party pricing power: at {v.name} a {ch} fee hike, ranking change, or outage hits most of the top line at once, and the channel — not you — owns the customer relationship.",
        conclusion=f"Diversify the channel mix — convert {ch} customers to a direct/owned channel and grow a second channel so no single one exceeds {X}% of revenue.",
        expected_effect=f"Shifting {X}% of {ch} volume to a direct channel protects ~${X}/mo of fee/dependence risk.",
        recommend_when={"state": "channel_revenue_concentration", "min_signal": "channel_revenue"},
        tags=("revenue", "concentration", "channel", v.family),
        applies_flags=("delivery_capable",),
    )


def _growth_lever_decomposition(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Diagnose your revenue change: traffic or ticket?",
        observation=f"Revenue moved {X}% but {v.sale_unit} count moved {X}% and average {v.sale_unit} value moved {X}% — the two pull in different directions.",
        reasoning=f"Revenue = {v.sale_unit}s × value, and the right action depends entirely on which factor drives the change: at {v.name} a traffic problem needs demand generation while a ticket problem needs mix/pricing — confusing them wastes the fix.",
        conclusion=f"Treat the dominant lever: if {v.sale_unit} count is the drag, invest in {v.core_kpis[0]} / {_channel_pick(v)} demand; if ticket is the drag, deploy {_ticket_lever(v, situation)}.",
        expected_effect=f"Targeting the actual driver instead of guessing recovers ~${X}/mo with one focused move.",
        recommend_when={"state": "revenue_driver_diagnosis", "min_signal": "transactions"},
        tags=("revenue", "diagnosis", "growth", v.family),
    )


def _price_tier_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You're missing a price tier — customers have nowhere to trade up",
        observation=f"{X}% of {v.sale_unit}s cluster at your single ${X} price point with no clearly-better premium option above it.",
        reasoning=f"Without a higher tier, the {X}% of customers willing to pay more can't, so you leave their extra willingness-to-pay unclaimed; at {v.name} a good/better/best ladder also makes the middle option look like the smart buy (anchoring).",
        conclusion=f"Introduce a premium {v.sale_unit} tier above the current one (and optionally an entry tier) so each customer self-selects to their willingness-to-pay.",
        expected_effect=f"If {X}% of {v.sale_unit}s step up to a {X}%-higher tier, that adds ~${X}/mo at full margin.",
        recommend_when={"state": "missing_price_tier", "min_signal": "product_performance"},
        tags=("revenue", "pricing", "mix", v.family),
    )


def _membership_underpenetration(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Recurring revenue is under-built — too few customers are on a {v.sale_unit} plan",
        observation=f"Only {X}% of customers are on a membership/plan; the other {X}% pay per-visit despite visiting {X}+ times a quarter.",
        reasoning=f"Recurring revenue is the most valuable kind — predictable, higher lifetime value, lower churn — and at {v.name} frequent per-visit customers are the cheapest possible conversions you're simply not asking.",
        conclusion=f"Convert high-frequency per-visit customers to a plan at the point of the {v.sale_unit}, and make the plan the default-recommended option for anyone past {X} visits.",
        expected_effect=f"Converting {X}% of frequent visitors to plans turns ~${X}/mo of variable revenue into predictable recurring revenue.",
        recommend_when={"state": "recurring_revenue_underpenetration", "min_signal": "customer_segments"},
        tags=("revenue", "recurring", "membership", v.family),
        applies_flags=("membership",),
    )


def _seasonal_cliff(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A seasonal revenue cliff is approaching",
        observation=f"Revenue drops from ${X}/mo to ${X}/mo entering {X} every year — a {X}% seasonal cliff that lasts {X} months.",
        reasoning=f"A predictable trough is a cash-management problem, not a surprise: at {v.name} fixed {v.staff_role} and occupancy costs continue while {v.sale_unit} revenue falls, so an unmanaged off-season drains the cash the peak built.",
        conclusion=f"Pre-position for the trough — build a counter-seasonal {v.sale_unit} line or pre-sell ({_channel_pick(v)}) during the peak, and flex {v.staff_role} cost down before the cliff, not after.",
        expected_effect=f"Smoothing the off-season protects ~${X} of peak-built cash from the trough.",
        recommend_when={"state": "seasonal_revenue_cliff", "min_signal": "monthly_revenue"},
        tags=("revenue", "seasonal", "cashflow", v.family),
        applies_flags=("seasonal",),
    )


def _revenue_per_labor_hour(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Revenue per {v.staff_role}-hour is below your break-even line",
        observation=f"You generate ${X} of revenue per {v.staff_role}-labor-hour against a ${X} break-even; the gap is worst in the {X} window.",
        reasoning=f"Revenue per labor hour is the productivity ratio that decides profitability at {v.name}: below break-even, every additional {v.staff_role} hour costs more than the {v.sale_unit}s it produces, regardless of how busy it looks.",
        conclusion=f"Lift the ratio at the worst window — either raise {v.sale_unit} throughput/value per hour ({_ticket_lever(v, situation)}) or re-time {v.staff_role} hours toward productive windows.",
        expected_effect=f"Bringing the weak window to break-even recovers ~${X}/mo of labor-productivity loss.",
        recommend_when={"state": "low_revenue_per_labor_hour", "min_signal": "schedule_shifts"},
        tags=("revenue", "productivity", "labor", v.family),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="RevenuePerLaborAgent: join hourly_revenue to schedule_shifts to compute revenue/labor-hour by window against a configurable break-even.",
    )


def _slow_mover_drag(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Slow-moving stock is dragging revenue and tying up cash",
        observation=f"{X}% of SKUs produce only {X}% of revenue and have sat {X}+ days; they occupy {X}% of shelf/space and ${X} of working capital.",
        reasoning=f"Dead stock costs twice at {v.name}: the cash is frozen in product that isn't selling AND the {_capacity_unit(v)}/shelf it occupies could hold faster-moving {v.sale_unit}s that actually turn.",
        conclusion=f"Clear the long tail — markdown or return the bottom {X}% of SKUs and reallocate the space and cash to your proven top movers.",
        expected_effect=f"Recycling ${X} of dead-stock capital into top movers lifts revenue ~${X}/mo and frees cash.",
        recommend_when={"state": "slow_mover_revenue_drag", "min_signal": "inventory_levels"},
        tags=("revenue", "inventory", "mix", v.family),
        applies_flags=("inventory_heavy",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StockVelocityAgent: join inventory_levels to product_performance to rank SKUs by days-on-hand and revenue contribution.",
    )


def _peak_day_expansion(v: Vertical, situation: str) -> Built:
    cap = _capacity_unit(v)
    return Built(
        title=f"Your busiest day repeatedly maxes out — expand it specifically",
        observation=f"{X} hits {X}% {_capacity_unit(v)} utilization and turns away ${X} of {v.sale_unit} demand every week, while other days have slack.",
        reasoning=f"A single day that consistently sells out is the clearest expansion signal at {v.name}: the demand is proven and recurring, so adding capacity there is the lowest-risk revenue investment you can make.",
        conclusion=f"Add capacity to that day only — extend {X} hours, add a {cap}, or add {v.staff_role} coverage just for {X} — rather than blanket changes across the week.",
        expected_effect=f"Capturing the turned-away demand on your proven peak day adds ~${X}/mo.",
        recommend_when={"state": "peak_day_capacity_expansion", "min_signal": "daily_revenue"},
        tags=("revenue", "capacity", "expansion", v.family),
        applies_families=("food_service", "personal_care", "health_wellness", "automotive", "hospitality"),
    )


def _advance_booking_untapped(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Advance bookings/pre-orders are an untapped revenue stream",
        observation=f"Only {X}% of {v.sale_unit}s are booked/ordered in advance; the rest are same-day, leaving demand unforecastable and deposits uncollected.",
        reasoning=f"Advance commitment is free working capital and a demand signal at {v.name}: a deposit locks revenue, lets you pre-buy inputs and pre-staff, and cuts no-shows — value you forgo by staying purely walk-up.",
        conclusion=f"Stand up an advance channel ({_channel_pick(v)}) with a deposit on the highest-demand {v.sale_unit}s, and nudge repeat customers to pre-book their next one at checkout.",
        expected_effect=f"Pulling {X}% of demand into advance bookings secures ~${X}/mo earlier and cuts no-show loss.",
        recommend_when={"state": "advance_booking_untapped", "min_signal": "bookings"},
        tags=("revenue", "untapped", "cashflow", v.family),
        applies_families=("personal_care", "health_wellness", "hospitality", "food_service", "home_services"),
    )


def _mom_growth_stall(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Month-over-month growth has stalled to near zero",
        observation=f"MoM revenue growth decelerated from {X}% to {X}% over {X} months and is now flat at ${X}/mo — not falling, but no longer compounding.",
        reasoning=f"A stall is a leading indicator, not a steady state: at {v.name} it usually means the current playbook (the channel, the {v.sale_unit} mix, the customer base) has saturated, and continuing it just holds the line while costs creep up.",
        conclusion=f"Open a new growth vector rather than pushing the tapped one harder — a new {_channel_pick(v)} segment, a new {v.sale_unit} line, or a {v.core_kpis[0]} program — and measure incrementality.",
        expected_effect=f"Re-igniting even {X}% MoM growth compounds to ~${X}/mo within two quarters.",
        recommend_when={"state": "growth_stall", "min_signal": "monthly_revenue"},
        tags=("revenue", "trend", "growth", v.family),
    )


def _bestseller_stockout_loss(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your best-selling {v.sale_unit} keeps stocking out — direct revenue loss",
        observation=f"Your #1 {v.sale_unit} was unavailable {X}% of open hours last month, each stockout costing an estimated ${X} in lost sales.",
        reasoning=f"Stocking out your proven winner is the most expensive inventory mistake at {v.name}: it loses the guaranteed sale, sends the customer to a substitute (or a competitor), and trains them not to rely on you.",
        conclusion=f"Protect the hero {v.sale_unit} with a safety-stock floor and a reorder trigger sized to its true velocity — never let the proven seller run dry to save carrying cost.",
        expected_effect=f"Eliminating hero stockouts recovers ~${X}/mo of guaranteed, highest-confidence revenue.",
        recommend_when={"state": "bestseller_stockout", "min_signal": "inventory_levels"},
        tags=("revenue", "inventory", "leakage", v.family),
        applies_flags=("inventory_heavy",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StockoutImpactAgent: cross inventory_levels zero-on-hand windows with product_performance velocity to quantify lost-sale revenue.",
    )


def _attach_revenue_leak(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Low attach rate is leaving easy revenue on the counter",
        observation=f"Only {X}% of {v.sale_unit}s include an add-on/attach despite a natural pairing available; peers run {X}%.",
        reasoning=f"The attach is the cheapest revenue in the business at {v.name}: the customer is already buying and the {v.staff_role} is already engaged, so a missed attach is margin you could have had for one sentence of effort.",
        conclusion=f"Make the attach a default prompt — train every {v.staff_role} to offer the pairing on each {v.sale_unit}, and place the add-on at the decision point; measure attach rate weekly.",
        expected_effect=f"Lifting attach to {X}% across {X} weekly {v.sale_unit}s adds ~${X}/mo at near-pure margin.",
        recommend_when={"state": "low_attach_revenue_leak", "min_signal": "transactions"},
        tags=("revenue", "attach", "average_ticket", v.family),
        applies_families=("food_service", "retail", "personal_care", "health_wellness", "automotive"),
    )


def _high_ticket_close_rate(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Low close rate on high-value {v.sale_unit}s is capping revenue",
        observation=f"Only {X}% of quoted/consulted high-value {v.sale_unit}s convert; {X}% of estimates over ${X} go unsold.",
        reasoning=f"At {v.name} the bottleneck isn't lead volume, it's conversion: each lost high-ticket {v.sale_unit} is hundreds or thousands of dollars, so a few points of close-rate dwarf any traffic gain you could buy.",
        conclusion=f"Tighten the close — follow up every open estimate within {X} hours, offer financing/good-better-best, and coach the {v.staff_role} on objection handling rather than chasing more quotes.",
        expected_effect=f"Lifting close rate by {X} points on existing quotes is worth ~${X}/mo with zero added lead spend.",
        recommend_when={"state": "low_high_ticket_close_rate", "min_signal": "transactions"},
        tags=("revenue", "conversion", "high_ticket", v.family),
        applies_flags=("high_ticket",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="QuoteConversionAgent: track estimates/consults to close from booking + transaction data to compute close rate and unsold-quote value.",
    )


def _low_value_txn_drag(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A flood of tiny {v.sale_unit}s is dragging down average value",
        observation=f"{X}% of {v.sale_unit}s are under ${X} and together make only {X}% of revenue while consuming the same {v.staff_role} time as full-value ones.",
        reasoning=f"Sub-scale transactions can be unprofitable at {v.name}: the fixed handling cost per {v.sale_unit} ({v.staff_role} time, packaging, payment fee) can exceed the margin on a tiny ticket, so volume here loses money.",
        conclusion=f"Lift the floor — set a minimum {v.sale_unit} or a small-order fee, and bundle low-value items so the smallest tickets clear their handling cost.",
        expected_effect=f"Right-sizing the smallest {X}% of {v.sale_unit}s recovers ~${X}/mo of handling-cost loss.",
        recommend_when={"state": "low_value_transaction_drag", "min_signal": "transactions"},
        tags=("revenue", "average_ticket", "margin", v.family),
    )


def _off_peak_demand_fill(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Off-peak windows are empty revenue you could fill cheaply",
        observation=f"Your {X} off-peak window runs {X}% below capacity while peak turns demand away; the doors and {v.staff_role}s are already there.",
        reasoning=f"Unlike adding peak capacity, filling off-peak demand at {v.name} needs no new fixed cost — the {_capacity_unit(v)} and {v.staff_role} are paid for, so incremental off-peak {v.sale_unit}s are almost all contribution.",
        conclusion=f"Pull price-sensitive demand into the trough — an off-peak {v.sale_unit} rate or {v.core_kpis[0]} incentive — to shift demand from the maxed peak into the empty window.",
        expected_effect=f"Filling the off-peak window to half capacity adds ~${X}/mo with no new fixed cost.",
        recommend_when={"state": "off_peak_demand_fill", "min_signal": "hourly_revenue"},
        tags=("revenue", "yield", "off_peak", v.family),
        applies_families=("personal_care", "health_wellness", "fitness", "automotive", "hospitality", "food_service"),
    )


register(
    Archetype(
        key="declining_revenue_trend", domain="revenue", name="Declining revenue trend",
        build=_declining_trend, situations=("baseline", "anomaly"),
        required_signals=("daily_revenue", "weekly_revenue"),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="surging_revenue_trend", domain="revenue", name="Surging revenue — capitalize",
        build=_surging_trend, situations=("baseline", "emerging"),
        required_signals=("daily_revenue", "weekly_revenue"),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="single_day_concentration", domain="revenue", name="Revenue concentrated in one day",
        build=_concentration_one_day, situations=("baseline", "concentrated"),
        required_signals=("daily_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="product_class_concentration", domain="revenue", name="Revenue concentrated in one product class",
        build=_concentration_product_class, situations=("baseline", "concentrated"),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
        applies_flags=("inventory_heavy",),
    ),
    Archetype(
        key="average_ticket_erosion", domain="revenue", name="Average ticket erosion",
        build=_avg_ticket_erosion, situations=("baseline", "declining"),
        required_signals=("transactions", "daily_revenue"),
        required_agents=("RevenueAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="ticket_expansion_headroom", domain="revenue", name="Average-ticket expansion headroom",
        build=_avg_ticket_expansion, situations=("baseline", "untapped"),
        required_signals=("transactions", "product_performance"),
        required_agents=("RevenueAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PriceSensitivityAgent: correlate historical price changes to volume/repeat to estimate elasticity and safe price-lift headroom per product.",
    ),
    Archetype(
        key="weekday_weekend_imbalance", domain="revenue", name="Weekday vs weekend imbalance",
        build=_weekday_weekend_imbalance, situations=("baseline",),
        required_signals=("daily_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="low_revenue_per_capacity_unit", domain="revenue", name="Revenue per capacity unit below potential",
        build=_revenue_per_capacity, situations=("baseline",),
        required_signals=("capacity_config", "daily_revenue", "bookings"),
        required_agents=("RevenueAnalyzer", "CapacityAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CapacityYieldAgent: ingest capacity_config (seats/chairs/bays/rooms) and join to revenue + utilization to compute revenue-per-unit vs achievable potential.",
        applies_families=("food_service", "personal_care", "health_wellness", "fitness", "automotive", "hospitality"),
    ),
    Archetype(
        key="single_customer_dependence", domain="revenue", name="Single-customer revenue dependence",
        build=_single_customer_dependence, situations=("baseline", "concentrated"),
        required_signals=("customer_revenue", "transactions"),
        required_agents=("CustomerAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CustomerConcentrationAgent: aggregate transactions by customer_id to rank revenue share and flag single-account dependence.",
        applies_flags=("high_ticket",),
        applies_families=("home_services", "hospitality", "automotive"),
    ),
    Archetype(
        key="margin_squeeze_flat_revenue", domain="revenue", name="Flat revenue, rising costs",
        build=_flat_revenue_rising_costs, situations=("baseline",),
        required_signals=("daily_revenue", "monthly_revenue"),
        required_agents=("RevenueAnalyzer",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="MarginTrendAgent: pair revenue series with cost/COGS and labor series to surface the price/cost gap (cost inputs not yet ingested — add source).",
    ),
    Archetype(
        key="intra_month_revenue_skew", domain="revenue", name="Intra-month revenue skew",
        build=_intra_month_skew, situations=("baseline",),
        required_signals=("daily_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="event_spike_unprepared", domain="revenue", name="Holiday/event spike unprepared",
        build=_event_spike_unprepared, situations=("baseline", "seasonal_peak"),
        required_signals=("daily_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
        applies_flags=("seasonal",),
    ),
    Archetype(
        key="refund_revenue_leak", domain="revenue", name="Refund-adjusted revenue gap",
        build=_refund_adjusted_gap, situations=("baseline", "leaking"),
        required_signals=("refunds", "transactions"),
        required_agents=("RevenueAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RefundAnalyzer: ingest refunds/voids and attribute them to product/staff to separate net revenue from gross and surface defect clusters.",
    ),
    Archetype(
        key="discount_net_erosion", domain="revenue", name="Discount/comp net-revenue erosion",
        build=_discount_net_erosion, situations=("baseline", "leaking"),
        required_signals=("discounts", "transactions", "customer_segments"),
        required_agents=("RevenueAnalyzer", "CustomerAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DiscountAttributionAgent: join discounts/comps to transactions and repeat behavior to split incremental from margin-giveaway discounting.",
    ),
    Archetype(
        key="new_vs_repeat_imbalance", domain="revenue", name="New vs repeat revenue split",
        build=_new_vs_repeat_split, situations=("baseline", "leaking"),
        required_signals=("customer_segments", "transactions"),
        required_agents=("CustomerAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CustomerCohortAgent: classify transactions new vs returning via customer_id/contact and track repeat-revenue share.",
    ),
    Archetype(
        key="weekly_revenue_volatility", domain="revenue", name="Week-to-week revenue volatility",
        build=_week_volatility, situations=("baseline", "volatile"),
        required_signals=("weekly_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="daypart_revenue_imbalance", domain="revenue", name="Daypart revenue imbalance",
        build=_daypart_imbalance, situations=("baseline",),
        required_signals=("hourly_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
        applies_families=("food_service", "retail", "hospitality"),
    ),
    Archetype(
        key="capacity_revenue_ceiling", domain="revenue", name="Capacity-utilization revenue ceiling",
        build=_capacity_ceiling, situations=("baseline",),
        required_signals=("capacity_config", "hourly_revenue", "bookings"),
        required_agents=("CapacityAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CapacityYieldAgent (shared): detect peak-window utilization at/over threshold with turned-away demand to flag a hard revenue ceiling.",
        applies_families=("food_service", "personal_care", "health_wellness", "fitness", "automotive", "hospitality"),
    ),
    Archetype(
        key="channel_revenue_concentration", domain="revenue", name="Channel revenue concentration",
        build=_channel_concentration, situations=("baseline", "concentrated"),
        required_signals=("channel_revenue", "transactions"),
        required_agents=("ChannelAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMixAgent: tag transactions by channel (walk-in/online/delivery/booking) to compute per-channel revenue share and trend.",
        applies_flags=("delivery_capable",),
    ),
    Archetype(
        key="revenue_driver_diagnosis", domain="revenue", name="Growth-lever decomposition (traffic vs ticket)",
        build=_growth_lever_decomposition, situations=("baseline",),
        required_signals=("transactions", "daily_revenue"),
        required_agents=("RevenueAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="missing_price_tier", domain="revenue", name="Missing price tier",
        build=_price_tier_gap, situations=("baseline", "untapped"),
        required_signals=("product_performance", "transactions"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="recurring_revenue_underpenetration", domain="revenue", name="Recurring-revenue underpenetration",
        build=_membership_underpenetration, situations=("baseline", "untapped"),
        required_signals=("customer_segments", "transactions"),
        required_agents=("CustomerAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="MembershipPenetrationAgent: identify high-frequency per-visit customers (via customer_id visit cadence) eligible for plan conversion.",
        applies_flags=("membership",),
    ),
    Archetype(
        key="seasonal_revenue_cliff", domain="revenue", name="Seasonal revenue cliff",
        build=_seasonal_cliff, situations=("baseline", "seasonal_trough"),
        required_signals=("monthly_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
        applies_flags=("seasonal",),
    ),
    Archetype(
        key="low_revenue_per_labor_hour", domain="revenue", name="Revenue per labor-hour below break-even",
        build=_revenue_per_labor_hour, situations=("baseline",),
        required_signals=("hourly_revenue", "schedule_shifts"),
        required_agents=("RevenueAnalyzer", "StaffingAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="RevenuePerLaborAgent: join hourly_revenue to schedule_shifts to compute revenue/labor-hour by window against a configurable break-even.",
    ),
    Archetype(
        key="slow_mover_revenue_drag", domain="revenue", name="Slow-mover revenue drag",
        build=_slow_mover_drag, situations=("baseline",),
        required_signals=("inventory_levels", "product_performance"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StockVelocityAgent: join inventory_levels to product_performance to rank SKUs by days-on-hand vs revenue contribution.",
        applies_flags=("inventory_heavy",),
    ),
    Archetype(
        key="peak_day_capacity_expansion", domain="revenue", name="Peak-day capacity expansion",
        build=_peak_day_expansion, situations=("baseline",),
        required_signals=("daily_revenue", "capacity_config"),
        required_agents=("RevenueAnalyzer", "CapacityAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CapacityYieldAgent (shared): flag the recurring peak day where utilization saturates and quantify turned-away demand.",
        applies_families=("food_service", "personal_care", "health_wellness", "automotive", "hospitality"),
    ),
    Archetype(
        key="advance_booking_untapped", domain="revenue", name="Advance-booking/pre-order untapped",
        build=_advance_booking_untapped, situations=("baseline", "untapped"),
        required_signals=("bookings", "transactions"),
        required_agents=("RevenueAnalyzer", "BookingAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="AdvanceDemandAgent: separate advance vs same-day transactions and measure deposit capture + no-show reduction potential.",
        applies_families=("personal_care", "health_wellness", "hospitality", "food_service", "home_services"),
    ),
    Archetype(
        key="growth_stall", domain="revenue", name="Month-over-month growth stall",
        build=_mom_growth_stall, situations=("baseline",),
        required_signals=("monthly_revenue",),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="bestseller_stockout", domain="revenue", name="Best-seller stockout revenue loss",
        build=_bestseller_stockout_loss, situations=("baseline", "leaking"),
        required_signals=("inventory_levels", "product_performance"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StockoutImpactAgent: cross inventory_levels zero-on-hand windows with product velocity to quantify lost-sale revenue.",
        applies_flags=("inventory_heavy",),
    ),
    Archetype(
        key="low_attach_revenue_leak", domain="revenue", name="Low attach-rate revenue leak",
        build=_attach_revenue_leak, situations=("baseline", "untapped"),
        required_signals=("transactions", "product_performance"),
        required_agents=("RevenueAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
        applies_families=("food_service", "retail", "personal_care", "health_wellness", "automotive"),
    ),
    Archetype(
        key="low_high_ticket_close_rate", domain="revenue", name="Low close rate on high-value sales",
        build=_high_ticket_close_rate, situations=("baseline", "leaking"),
        required_signals=("transactions", "bookings"),
        required_agents=("RevenueAnalyzer", "ConversionAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="QuoteConversionAgent: track estimates/consults to close from bookings + transactions to compute close rate and unsold-quote value.",
        applies_flags=("high_ticket",),
    ),
    Archetype(
        key="low_value_transaction_drag", domain="revenue", name="Low-value transaction drag",
        build=_low_value_txn_drag, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="off_peak_demand_fill", domain="revenue", name="Off-peak demand fill",
        build=_off_peak_demand_fill, situations=("baseline",),
        required_signals=("hourly_revenue", "capacity_config"),
        required_agents=("RevenueAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CapacityYieldAgent (shared): identify off-peak windows running below a utilization floor while peak saturates, for demand-shifting offers.",
        applies_families=("personal_care", "health_wellness", "fitness", "automotive", "hospitality", "food_service"),
    ),
)
