"""
Domain: LOCAL MARKET / EXTERNAL CONTEXT.

Every other domain reasons about what happens INSIDE the four walls (staffing,
inventory, pricing, the camera on the floor). This domain reasons about the world
OUTSIDE them — the concert down the block, the rain on Saturday, the competitor
who just opened, the school that let out for summer, the payday everyone in the
neighborhood shares — and relates the merchant's own numbers to it.

Each archetype is a distinct reasoning pattern about ONE external force and how it
couples to demand. Specialization per vertical changes the coupling: weather hits
a car wash and a food truck hard but a dental office not at all; tourism reshapes
a hotel-F&B daypart but is noise to a plumber; a university term swing is life or
death for a campus cafe and irrelevant to a landscaper. So a car-wash weather
insight and a tire-shop weather insight are genuinely different stories, not a
relabel.

Honesty about the swarm: this is the explicit "upgrade the swarm" domain. Almost
none of these signals exist today — there is no events feed, no weather feed, no
competitor map, no census join, no local benchmark. So nearly every archetype is
swarm_capability=MISSING and ships with a precise spec for the upgrade agent that
would ingest the external source and join it to the merchant's revenue. The few
PARTIAL cases are ones where the internal half already exists (revenue rhythm,
geo+date math) and only the external join is the upgrade. The join key is always
geography and/or date — that is what turns an outside fact into an inside number.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register

# ── Targeting sets ─────────────────────────────────────────────────────────
NO_GHOST = ("ghost_kitchen",)  # a ghost kitchen has no storefront, street, or window
# Verticals whose demand swings hard with the weather.
WEATHER_KEYS = ("car_wash", "food_truck", "landscaping", "tire_shop", "florist")
# Verticals exposed to outdoor air quality (patio / sidewalk / open-air work).
OUTDOOR_KEYS = ("car_wash", "food_truck", "landscaping", "entertainment", "event_venue", "cafe")
# Verticals whose mix is reshaped by visitors-from-elsewhere.
TOURISM_KEYS = ("hotel_fb", "entertainment", "full_restaurant", "cafe", "bar", "food_truck")
# Verticals where a local crowd's night out is the product.
NIGHTLIFE_KEYS = ("bar", "full_restaurant", "entertainment", "hotel_fb")
# Verticals that move with commuting / fuel / shift cycles.
COMMUTE_KEYS = ("cafe", "qsr", "convenience", "bakery", "food_truck")


# ── 1. A nearby event you could ride ────────────────────────────────────────
def _event_tie_in(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    when = {
        "emerging": " A new recurring event has just appeared on the local calendar — claim it before competitors notice the lift.",
        "untapped": " This event has run for {x} cycles next to you and your revenue has never moved with it — pure unworked upside.".replace("{x}", X),
        "seasonal_peak": " The event season is approaching — pre-build the capacity now, not on the day.",
    }.get(situation, "")
    return Built(
        title=f"A {X} event nearby moves {X} people past your door — and you don't ride it",
        observation=f"On the {X} days an event runs within {X} of you, your {unit} volume is {X}% {X} than a matched non-event day.",
        reasoning=f"An event is borrowed demand: someone else paid to gather a crowd a short walk from your {v.channels[0]} door, so the marginal cost of capturing them is near zero. Either you already get an uncaptured spillover, or the crowd flows right past — both are levers your POS can't see because the cause sits outside it.{when}",
        conclusion=f"Build an event playbook: pre-stage {unit} capacity and {v.staff_role} coverage on event days and put a crowd-specific offer in front of the foot traffic the event creates.",
        expected_effect=f"Turning the {X} annual event days into planned peaks is worth ~${X}/yr on demand you pay nothing to create.",
        recommend_when={"state": "event_spillover_unworked", "min_signal": "local_events"},
        tags=("localmarket", "events", "opportunity", v.family),
    )


# ── 2. A nearby event that takes your regulars away ─────────────────────────
def _event_conflict(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " This break appeared suddenly against a new event on the calendar — investigate before reading it as a demand problem." if situation == "anomaly" else ""
    return Built(
        title=f"Big local events quietly cost you your regulars",
        observation=f"On major-event days your {unit} volume drops {X}% even though the area is busier — your base customers stay home or go to the event instead.",
        reasoning=f"Not every nearby crowd is your crowd. A festival or stadium night pulls your regulars' attention and parking elsewhere, and for a routine-driven {v.name} that substitution shows up as a dip, not a spike. Read blind, it looks like you had a bad day; in truth an external event displaced your demand.{extra}",
        conclusion=f"Stop fighting event days head-on: shift labor down, pre-sell or pre-book your regulars around the event, and protect margin instead of chasing walk-ups who aren't coming.",
        expected_effect=f"Right-sizing the {X} conflicting event days a year avoids ~${X}/yr in wasted labor and waste on demand that was never going to show.",
        recommend_when={"state": "event_displaces_regulars", "min_signal": "local_events"},
        tags=("localmarket", "events", "risk", v.family),
    )


# ── 3. Competitor density in your radius ────────────────────────────────────
def _competitor_proximity(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    if "high_ticket" in v.flags:
        lever = f"lean into being a destination — reputation, expertise, and {v.core_kpis[0]} — where proximity matters least"
        why = f"high-ticket buyers travel for the right {v.staff_role}, so density pressures price and trust more than convenience"
    elif "walk_in_heavy" in v.flags:
        lever = f"win the convenience fight — speed, hours, and a reason-to-pass-them at the {v.channels[0]} moment"
        why = f"a walk-in customer picks the nearest acceptable option, so each same-radius rival is a direct splitter of the same foot traffic"
    else:
        lever = f"differentiate on the {v.core_kpis[0]} lever rather than competing on sameness"
        why = "a dense cluster of similar shops commoditizes the category and compresses everyone's pricing power"
    return Built(
        title=f"{X} direct competitors sit within {X} of you",
        observation=f"Your trade-area radius holds {X} businesses selling the same {unit}, a density {X}% above the regional norm for {v.name}.",
        reasoning=f"Competitor proximity sets the ceiling on your pricing and share before you do anything inside the store: {why}. Your POS can't see them, so this constraint is invisible until the outside map is joined to your numbers.",
        conclusion=f"Given the cluster, {lever}.",
        expected_effect=f"Positioning correctly against {X} same-radius rivals defends ~${X}/mo of share otherwise split away.",
        recommend_when={"state": "high_competitor_density", "min_signal": "competitor_map"},
        tags=("localmarket", "competition", "positioning", v.family),
    )


# ── 4. A competitor just opened ─────────────────────────────────────────────
def _competitor_new_opening(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The dip aligns exactly with the opening date — this is a cause, not a coincidence." if situation == "anomaly" else ""
    return Built(
        title=f"A new competitor opened {X} away — and your {X} cohort is bleeding",
        observation=f"Since a same-category business opened within {X}, your {unit} volume is down {X}%, concentrated in your {X} customer cohort.",
        reasoning=f"A new opening is a one-time trial-stealing event: novelty pulls your customers to try the new option, and the first {X} weeks decide who comes back. For {v.name} the at-risk group is the price- or convenience-led cohort, not your loyal core — so a blanket panic discount over-pays to defend customers who weren't leaving.{extra}",
        conclusion=f"Run a targeted win-back at the at-risk cohort during the opening's novelty window — a reason-to-return tied to your {v.core_kpis[0]} edge — and leave your loyal base alone.",
        expected_effect=f"Defending the trial-vulnerable cohort through the opening window protects ~${X}/mo that would otherwise churn permanently.",
        recommend_when={"state": "competitor_just_opened", "min_signal": "competitor_map"},
        tags=("localmarket", "competition", "retention", v.family),
    )


# ── 5. A competitor closed — capture the orphans ────────────────────────────
def _competitor_closure(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The closure is recent and their customers are actively re-choosing right now — the capture window is open and short." if situation == "emerging" else ""
    return Built(
        title=f"A competitor near you closed — their customers are up for grabs",
        observation=f"A same-category business within {X} shut in the last {X} weeks, releasing an estimated {X} displaced customers/week into your trade area.",
        reasoning=f"A closure is the cheapest growth event there is: demand that already exists and is actively shopping for a new home. The orphaned customers will settle into a new routine within weeks, so whoever reaches them during the re-choosing window keeps them — and after it closes, the share is locked for years.{extra}",
        conclusion=f"Move now: a welcome offer aimed at the closed shop's neighborhood and a {v.staff_role} ready to convert the trial visit into a repeat {unit}.",
        expected_effect=f"Capturing even {X}% of the displaced demand adds ~${X}/mo of customers you didn't have to create.",
        recommend_when={"state": "competitor_closed_nearby", "min_signal": "competitor_map"},
        tags=("localmarket", "competition", "opportunity", v.family),
    )


# ── 6. A competitor is running a promotion ──────────────────────────────────
def _competitor_promotion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your soft weeks line up with a nearby competitor's promotions",
        observation=f"Your {unit} dips of {X}% cluster on the same weeks a competitor within {X} runs a visible price promotion.",
        reasoning=f"A rival's promotion is a temporary, external pull on the same shoppers — matching it blindly trains your customers to wait for discounts and torches margin, while ignoring it cedes the trial. For {v.name}, the right answer depends on whether the promoted item overlaps your {v.core_kpis[0]} strength or not, which you can only judge once you can see their offer next to your calendar.",
        conclusion=f"Respond by exception, not reflex: counter only when the promoted {unit} overlaps your core, otherwise hold price and lean on a non-price reason-to-choose-you.",
        expected_effect=f"Replacing reflexive match-discounting with selective response protects ~${X}/mo of margin on overlapping weeks.",
        recommend_when={"state": "competitor_promo_pressure", "min_signal": "competitor_promotions"},
        tags=("localmarket", "competition", "pricing", v.family),
    )


# ── 7. Your revenue tracks the weather ──────────────────────────────────────
def _weather_correlation(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    if v.key == "car_wash":
        driver = "dry, warm days drive wash volume, and the days right after rain spike as road grime accumulates"
        play = "pre-stage attendants and a post-rain push the moment the forecast clears"
    elif v.key == "tire_shop":
        driver = "the first cold snap and first snow trigger a wave of seasonal tire and winterization demand"
        play = "pre-order seasonal inventory and book bays ahead of the first forecast cold front"
    elif v.key in ("landscaping", "food_truck"):
        driver = "rain and extreme heat suppress outdoor demand, while mild dry days over-fill it"
        play = "flex crew/route scheduling to the forecast instead of a fixed weekly plan"
    elif v.key == "florist":
        driver = "heat compresses perishable shelf life and reshapes which stems sell, independent of the calendar"
        play = "buy cooler/shorter-vase-life stock ahead of heat and discount at-risk inventory before it wilts"
    else:
        driver = "weather shifts how much of your category customers want on a given day"
        play = "align staffing and perishable ordering to the forecast rather than the day of week"
    return Built(
        title=f"~{X}% of your daily swing is the weather, not your operation",
        observation=f"Daily {unit} volume correlates {X} with local conditions: {driver}.",
        reasoning=f"For {v.name}, weather is a first-order demand driver yet it's completely absent from your data, so good and bad days get mis-attributed to the team or the menu. Separating the weather-explained swing from the controllable swing is the difference between managing the business and blaming it.",
        conclusion=f"Treat the forecast as a planning input: {play}.",
        expected_effect=f"Forecast-aligned staffing and ordering cut both waste and missed peaks for ~${X}/mo of recovered margin.",
        recommend_when={"state": "weather_sensitive_demand", "min_signal": "weather_feed"},
        tags=("localmarket", "weather", v.family),
    )


# ── 8. Act on tomorrow's forecast (forward-looking) ─────────────────────────
def _weather_forecast_prestage(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You learn the weather hurt you after the day, not before it",
        observation=f"Your worst {X}% of days are predictable from the prior-day forecast, yet staffing and {unit} prep are set to a fixed template that ignores it.",
        reasoning=f"The historical correlation only pays off if it's acted on forward: a known-bad forecast should pull labor and perishable prep down a day ahead, and a known-great one should pull them up. Reacting after the fact means you've already overstaffed the washout or undersupplied the rush — the loss is locked before you open.",
        conclusion=f"Wire the next-day forecast into the schedule and prep sheet: a rule that adjusts {v.staff_role} hours and {unit} prep up or down when the forecast crosses a threshold.",
        expected_effect=f"Pre-staging to forecast instead of reacting saves ~${X}/mo in labor on bad days and captures the good ones.",
        recommend_when={"state": "forecast_not_actioned", "min_signal": "weather_forecast"},
        tags=("localmarket", "weather", "planning", v.family),
    )


# ── 9. Rain washout (outdoor demand) ────────────────────────────────────────
def _rain_washout(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Rain doesn't just slow you — it relocates your demand",
        observation=f"On rain days your {unit} volume falls {X}%, but the following {X} dry days run {X}% above normal as deferred demand returns.",
        reasoning=f"For an outdoor-dependent {v.name}, rain rarely destroys demand — it postpones it. Customers who skipped come back when it clears, so a rain day plus its rebound is one event, not two. Treating the rain day as lost and the rebound as a surprise mis-staffs both ends.",
        conclusion=f"Manage rain as a deferral: cut cost on the wet day, then pre-stage extra {v.staff_role} capacity for the rebound window instead of being caught short.",
        expected_effect=f"Smoothing the rain-then-rebound cycle recovers ~${X}/mo of demand that's currently dropped on the wet day and fumbled on the dry one.",
        recommend_when={"state": "rain_demand_deferral", "min_signal": "weather_feed"},
        tags=("localmarket", "weather", "demand_shift", v.family),
    )


# ── 10. Heat surge ──────────────────────────────────────────────────────────
def _heat_surge(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " A heat wave is forecast — this is the moment to pre-stage, not after the first sold-out afternoon." if situation == "seasonal_peak" else ""
    return Built(
        title=f"Heat waves spike demand you're not provisioned for",
        observation=f"When temperatures cross {X}, your {unit} demand jumps {X}% and concentrates in the {X} window, but supply and staffing stay flat.",
        reasoning=f"Extreme heat is an external demand shock with a clear trigger: it pulls forward the heat-relevant part of your mix and crowds it into the cooler hours of the day. Provisioned for an average day, a {v.name} stocks out or queues out exactly when willingness-to-buy peaks.{extra}",
        conclusion=f"Set a heat protocol: when the forecast crosses the threshold, deepen heat-relevant {unit} supply and add {v.staff_role} coverage in the surge window.",
        expected_effect=f"Provisioning for forecast heat captures ~${X}/mo currently lost to stockouts and queues on the hottest days.",
        recommend_when={"state": "heat_demand_surge", "min_signal": "weather_feed"},
        tags=("localmarket", "weather", "capacity", v.family),
    )


# ── 11. Seasonal tourism swing ──────────────────────────────────────────────
def _tourism_swing(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    when = {
        "seasonal_peak": " The in-season is approaching — staff and stock to the visitor surge before it arrives, not after.",
        "seasonal_trough": " The off-season is coming — protect cash by shrinking to the local base, not the peak footprint.",
    }.get(situation, "")
    return Built(
        title=f"Your demand rises and falls with tourist season, not your effort",
        observation=f"Your {unit} volume swings {X}% between the local tourism high and low season, tracking visitor inflow rather than anything you change.",
        reasoning=f"For {v.name} in a visitor-exposed area, a large share of demand is non-resident and seasonal, so the same operation looks brilliant in-season and broken off-season. Planning the year to one average over- and under-resources both halves; you need two operating modes keyed to the visitor calendar.",
        conclusion=f"Run two playbooks: a peak mode (max {v.staff_role} capacity, visitor-skewed mix) and a lean off-season mode (local-base hours and cost) switched by the tourism calendar.{when}",
        expected_effect=f"Matching capacity to the visitor calendar is worth ~${X}/yr across captured peak and protected trough.",
        recommend_when={"state": "tourism_seasonality", "min_signal": "tourism_index"},
        tags=("localmarket", "tourism", "seasonality", v.family),
    )


# ── 12. Tourist vs local mix ────────────────────────────────────────────────
def _tourism_vs_local_mix(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Tourists and locals buy differently — you serve them the same",
        observation=f"An estimated {X}% of your {unit}s come from visitors, who skew toward {X} purchases, while locals drive your repeat {v.core_kpis[0]}.",
        reasoning=f"These are two businesses sharing a roof: visitors are one-shot, discovery-led, and price-tolerant, while locals are repeat, loyalty-led, and the off-season lifeline. A single playbook either over-discounts loyal locals or fails to upsell once-only visitors. The split is invisible until an external visitor-share signal separates them.",
        conclusion=f"Segment the two: a discovery/upsell path for visitors and a loyalty/repeat path for locals, and protect the local base that carries the off-season.",
        expected_effect=f"Right-serving each segment lifts visitor ticket and local frequency for ~${X}/mo combined.",
        recommend_when={"state": "tourist_local_mismatch", "min_signal": "tourism_index"},
        tags=("localmarket", "tourism", "segmentation", v.family),
    )


# ── 13. Neighborhood demographics vs your mix ───────────────────────────────
def _demographic_fit(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your product mix is aimed at a neighborhood you're not in",
        observation=f"Census data for your trade area skews {X} on income/age/household, but your {unit} mix and {v.core_kpis[0]} push target a different profile.",
        reasoning=f"The people who can actually walk to a {v.name} are fixed by geography; the assortment is a choice. When the two diverge, you under-serve the customers you have while marketing to ones who aren't there — a structural mismatch that no in-store tactic fixes because the cause is the neighborhood, not the floor.",
        conclusion=f"Re-weight mix, price tier, and messaging toward the actual trade-area demographic for {X} weeks and measure conversion against the current baseline.",
        expected_effect=f"Aligning the offer to who's actually nearby is worth ~${X}/mo in better-matched demand.",
        recommend_when={"state": "demographic_product_mismatch", "min_signal": "demographics_geo"},
        tags=("localmarket", "demographics", "merchandising", v.family),
    )


# ── 14. Foot traffic vs area benchmark ──────────────────────────────────────
def _foot_traffic_benchmark(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your block's foot traffic is up but your sales aren't",
        observation=f"Mobility data shows pedestrian volume past your location ran {X}% {X} year-over-year, while your {unit} count stayed flat.",
        reasoning=f"Area foot traffic is the size of the pond; your sales are the fish you catch. A flat catch against a growing pond means a capture problem — your storefront, hours, or offer isn't converting the rising passersby — which looks like 'steady business' until the external traffic trend reveals the missed lift.",
        conclusion=f"Treat the traffic growth as recoverable demand: test storefront pull-in and hours against the hours mobility data says the foot traffic actually grew.",
        expected_effect=f"Capturing your historical share of the traffic growth is worth ~${X}/mo on demand already walking past.",
        recommend_when={"state": "foot_traffic_vs_sales_gap", "min_signal": "mobility_traffic"},
        tags=("localmarket", "foot_traffic", "benchmark", v.family),
        # storefront-dependent → exclude ghost kitchen
    )


# ── 15. Market-share proxy in radius ────────────────────────────────────────
def _market_share_proxy(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You hold an estimated {X}% of spend in your own radius",
        observation=f"Against anonymized category spend within {X} of you, your {unit} revenue implies a {X}% local share — {X} the typical share for a {v.name} of your footprint.",
        reasoning=f"Absolute revenue can't tell you whether you're winning; share against the addressable spend in your radius can. A low share in a high-spend area is upside left on the table, while a high share in a thin area means growth has to come from basket, not new customers — opposite strategies you can't choose between without the external denominator.",
        conclusion=f"Pick the strategy your share implies: chase new-customer reach if share is low, or deepen {v.core_kpis[0]} and basket if share is already high.",
        expected_effect=f"Targeting the right growth lever for your share position is worth ~${X}/mo versus a misaimed push.",
        recommend_when={"state": "local_share_position", "min_signal": "local_benchmark"},
        tags=("localmarket", "market_share", "benchmark", v.family),
    )


# ── 16. Regional price positioning ──────────────────────────────────────────
def _regional_price_positioning(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You're priced {X} the local market without meaning to be",
        observation=f"Across comparable {v.name}s within {X}, your {unit} price sits in the {X} of the local range, a position you set in isolation rather than against the market.",
        reasoning=f"Price is read relative to nearby alternatives, not in absolute terms: priced unknowingly below the local band you leave margin on the table and signal lower quality, and above it without a visible reason you lose price-led shoppers. Either way the position was an accident because the competitive price set was never in view.",
        conclusion=f"Set price deliberately against the local band — move toward the value-justified position and pair any premium with a visible {v.core_kpis[0]} reason.",
        expected_effect=f"Correcting an accidental price position is worth ~${X}/mo in recovered margin or recaptured volume.",
        recommend_when={"state": "price_position_vs_market", "min_signal": "competitor_pricing"},
        tags=("localmarket", "pricing", "competition", v.family),
    )


# ── 17. Region-specific holiday calendar ────────────────────────────────────
def _localized_holiday(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Local holidays move your demand and you plan to the national calendar",
        observation=f"Your {unit} volume spikes or drops {X}% on {X} regional observances that aren't on the standard holiday calendar your planning uses.",
        reasoning=f"Demand follows the calendar your customers actually live by — local festivals, regional public holidays, cultural observances — not the generic one. Planning a {v.name} to the national calendar means staffing and stocking wrong on exactly the days the neighborhood's behavior changes most, every year, predictably.",
        conclusion=f"Load the region-specific calendar into planning and pre-set {v.staff_role} coverage and {unit} supply for each local observance.",
        expected_effect=f"Planning to the real local calendar is worth ~${X}/yr across the observances currently mis-staffed.",
        recommend_when={"state": "local_holiday_blindspot", "min_signal": "calendar_context"},
        tags=("localmarket", "calendar", "seasonality", v.family),
    )


# ── 18. Local pay cycle ─────────────────────────────────────────────────────
def _payday_cycle(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {X} mix swings with the neighborhood's pay cycle",
        observation=f"Your {unit} volume and basket rise in the days after common local paydays and thin out before them, a {X}% swing across the pay cycle.",
        reasoning=f"Discretionary spend near a {v.name} is gated by when the surrounding workforce gets paid. Post-payday windows tolerate upsell and premium mix; pre-payday windows want value and smaller baskets. Running one offer all month under-monetizes the flush days and over-prices the lean ones.",
        conclusion=f"Phase the offer to the cycle: push premium {unit}s and add-ons post-payday and value/entry options pre-payday, timed to the local pay calendar.",
        expected_effect=f"Phasing offers to the pay cycle is worth ~${X}/mo over a flat all-month approach.",
        recommend_when={"state": "paycycle_demand_swing", "min_signal": "calendar_context"},
        tags=("localmarket", "calendar", "pricing", v.family),
    )


# ── 19. School calendar impact ──────────────────────────────────────────────
def _school_calendar(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " Back-to-school is approaching — provision for the pattern shift before it lands." if situation == "seasonal_peak" else ""
    return Built(
        title=f"School term vs break flips your daily pattern",
        observation=f"Your {unit} dayparts shift {X}% between school-term weeks and breaks — the morning/afternoon shape that holds in term inverts over summer and holidays.",
        reasoning=f"A {v.name} near families or schools runs on the school clock: drop-off and pickup create term-time peaks that vanish on breaks, replaced by a different all-day rhythm. Staffing the same template year-round means overstaffing dead term-time troughs and missing the reshaped break-time demand.",
        conclusion=f"Keep two daypart templates — term and break — and switch {v.staff_role} coverage and {unit} prep on the school calendar's dates.{extra}",
        expected_effect=f"Matching the schedule to the school calendar is worth ~${X}/yr across the misaligned weeks.",
        recommend_when={"state": "school_calendar_pattern_shift", "min_signal": "calendar_context"},
        tags=("localmarket", "calendar", "scheduling", v.family),
    )


# ── 20. University term impact ──────────────────────────────────────────────
def _university_term(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    when = {
        "seasonal_trough": " Term is ending and the student base is about to leave — shrink to the year-round base before the cliff, not after.",
        "seasonal_peak": " Move-in is approaching — the student demand returns in a single week; pre-stage for it.",
    }.get(situation, "")
    return Built(
        title=f"When the university empties, so does your demand",
        observation=f"Your {unit} volume drops {X}% during reading week, breaks, and summer, then returns almost overnight at term start — a student-driven cliff, not a gradual season.",
        reasoning=f"A campus-adjacent {v.name} has a demand base that physically leaves town on the academic calendar. Unlike a smooth season, it's a step function: full one week, gone the next. Smoothing labor and leases against an annual average bleeds cash in the empty months and gets caught short at move-in.",
        conclusion=f"Plan to the academic step-function: flex {v.staff_role} hours and {unit} supply hard at term boundaries and build a non-student demand line for the empty stretches.{when}",
        expected_effect=f"Managing the term cliff instead of averaging through it is worth ~${X}/yr in avoided idle cost and captured move-in surge.",
        recommend_when={"state": "university_term_cliff", "min_signal": "calendar_context"},
        tags=("localmarket", "calendar", "seasonality", v.family),
    )


# ── 21. Commuter flow pattern ───────────────────────────────────────────────
def _commuter_pattern(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You're on a commute path and only catch one direction of it",
        observation=f"Mobility data shows a {X} morning inbound and {X} evening outbound flow past you, but your {unit}s concentrate in just one of the two waves.",
        reasoning=f"A {v.name} on a commuter corridor has two distinct demand windows with different missions — fast grab on the way in, considered stop on the way out. Catching only one means the other wave flows past unmonetized, usually because the offer or format fits one mission and not the other.",
        conclusion=f"Build for the missed wave: a fast {unit} format and {v.staff_role} setup for the rushed direction, or a dwell-friendly one for the relaxed direction, matched to which flow you're losing.",
        expected_effect=f"Capturing the second commute wave is worth ~${X}/mo on traffic already passing your door twice a day.",
        recommend_when={"state": "commuter_flow_one_sided", "min_signal": "mobility_traffic"},
        tags=("localmarket", "commuter", "daypart", v.family),
    )


# ── 22. Construction / road closure ─────────────────────────────────────────
def _road_closure(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The drop is sharp and dated to the closure's start — this is access, not demand." if situation == "anomaly" else ""
    return Built(
        title=f"Roadwork is choking access to you — and it reads as a sales slump",
        observation=f"Since construction or a closure started within {X} of you, {unit} volume is down {X}%, concentrated in the dayparts that depend on through-traffic and parking.",
        reasoning=f"A closure attacks access, not appetite: customers still want what you sell but can't easily reach you, so the dip is temporary and geographic, not a demand failure. Misread as weak sales, it triggers discounts that erode margin without fixing the actual barrier — getting to the door.{extra}",
        conclusion=f"Treat it as an access problem for the closure's duration: signage and alternate-route/parking guidance, lean staffing to the suppressed dayparts, and a delivery/pickup push if the channel exists.",
        expected_effect=f"Managing the closure as access (not demand) avoids ~${X}/mo of margin-destroying discounting and recovers reachable trips.",
        recommend_when={"state": "access_disruption", "min_signal": "road_closures"},
        tags=("localmarket", "access", "risk", v.family),
    )


# ── 23. Transit disruption ──────────────────────────────────────────────────
def _transit_disruption(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Transit changes move your customers without warning",
        observation=f"Your {unit} volume shifts {X}% on days a nearby transit line is disrupted, rerouted, or has changed service, even with no change inside the store.",
        reasoning=f"A transit-dependent slice of your customers appears and disappears with the service that brings them. A station closure, strike, or schedule change relocates that demand to another stop — and another business — for as long as it lasts. Invisible to POS, it looks like random volatility instead of a traceable external cause.",
        conclusion=f"Subscribe to transit-status for your nearby stops and pre-adjust {v.staff_role} coverage and {unit} prep on disrupted days instead of being surprised by them.",
        expected_effect=f"Anticipating transit-driven swings smooths ~${X}/mo of otherwise-unexplained volatility in staffing and waste.",
        recommend_when={"state": "transit_demand_shift", "min_signal": "transit_status"},
        tags=("localmarket", "transit", "volatility", v.family),
    )


# ── 24. Untapped local-business partnership ─────────────────────────────────
def _partnership_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Non-competing neighbors share your customers and you don't share back",
        observation=f"Within {X} sit {X} non-competing businesses whose customers overlap yours by an estimated {X}%, with zero cross-referral relationship today.",
        reasoning=f"Adjacent businesses that serve the same neighborhood but sell different things are a free distribution channel: their customers are pre-qualified to be yours. A {v.name} captures none of this latent cross-traffic without a deliberate referral or bundle — it's the cheapest acquisition channel in the radius and it's sitting unused.",
        conclusion=f"Stand up {X} reciprocal referrals or a bundle with the highest-overlap neighbors and measure referred {unit}s over {X} weeks.",
        expected_effect=f"A working local referral loop adds ~${X}/mo of customers at near-zero acquisition cost.",
        recommend_when={"state": "partnership_untapped", "min_signal": "business_graph"},
        tags=("localmarket", "partnership", "acquisition", v.family),
    )


# ── 25. Community sponsorship opportunity ───────────────────────────────────
def _community_sponsorship(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Local community events draw your exact customers — without your name on them",
        observation=f"The local community calendar lists {X} recurring events within {X} whose audience matches your trade-area demographic, none currently sponsored or attended by you.",
        reasoning=f"Community events are concentrated, trust-rich reach in your own neighborhood: a sponsorship or presence puts a {v.name} in front of the precise local audience that converts best, with the credibility that paid ads can't buy. Skipping them cedes that goodwill and visibility to whichever competitor shows up instead.",
        conclusion=f"Pick the {X} highest-fit events and commit a presence or sponsorship with a trackable offer, then measure new local {unit}s attributable to each.",
        expected_effect=f"Converting community goodwill into trackable demand is worth ~${X}/mo at far lower cost than equivalent paid reach.",
        recommend_when={"state": "community_reach_untapped", "min_signal": "community_calendar"},
        tags=("localmarket", "community", "brand", v.family),
    )


# ── 26. Anchor-tenant traffic ───────────────────────────────────────────────
def _anchor_tenant(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"A nearby anchor drives the foot traffic and you don't time to it",
        observation=f"A major traffic anchor within {X} (a big-box, grocery, transit hub, or employer) generates predictable surges your {unit} pattern doesn't align to.",
        reasoning=f"When a neighbor pulls the crowd, their rhythm becomes your opportunity: the anchor's peak hours, restock days, or shift changes dump qualified foot traffic into your radius on a schedule. A {v.name} that ignores the anchor's clock staffs and stocks to its own average and misses the borrowed surge.",
        conclusion=f"Map the anchor's traffic rhythm and align your {v.staff_role} coverage, hours, and a catch-the-overflow offer to its peaks.",
        expected_effect=f"Timing to the anchor's traffic is worth ~${X}/mo on surges you currently let pass.",
        recommend_when={"state": "anchor_traffic_unaligned", "min_signal": "anchor_tenants"},
        tags=("localmarket", "foot_traffic", "anchor", v.family),
    )


# ── 27. Rent vs revenue location efficiency ─────────────────────────────────
def _rent_efficiency(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You pay for a location you're not fully using",
        observation=f"Your rent per square foot sits at {X} the local commercial rate, but your {unit} revenue per square foot runs {X}% below what that location's traffic should support.",
        reasoning=f"Rent buys access to a specific stream of foot traffic; the question is whether your revenue justifies that premium. A high-rent, low-yield location means you're either under-converting the traffic you pay for or over-paying for traffic you don't need — a structural cost problem invisible until rent is benchmarked against local rates and your own throughput.",
        conclusion=f"Decide deliberately: either lift revenue-per-foot to match the location's potential ({v.core_kpis[0]}, hours, layout) or renegotiate/relocate toward a rent your throughput supports.",
        expected_effect=f"Closing the rent-to-revenue efficiency gap is worth ~${X}/mo in either captured sales or saved occupancy cost.",
        recommend_when={"state": "rent_revenue_inefficiency", "min_signal": "rent_benchmark"},
        tags=("localmarket", "location", "cost", v.family),
    )


# ── 28. Delivery radius vs population density ────────────────────────────────
def _delivery_radius_density(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your delivery zone is shaped wrong for where the people are",
        observation=f"Population and order density in your delivery radius is lopsided — {X}% of nearby households sit in {X}% of the area, while your zone and driver routing treat the radius as uniform.",
        reasoning=f"Delivery economics are density economics: a circle of equal radius wastes drive time on thin edges and under-serves dense pockets where the same minutes yield more {unit}s. A {v.name} that draws a round zone on a non-round population leaves both margin (long low-yield runs) and demand (uncovered dense blocks) on the table.",
        conclusion=f"Reshape the zone to density: tighten or drop thin low-yield edges, guarantee coverage in the dense pockets, and route to orders-per-mile instead of distance.",
        expected_effect=f"Matching the delivery footprint to population density is worth ~${X}/mo in recovered driver efficiency and captured dense-area demand.",
        recommend_when={"state": "delivery_zone_vs_density", "min_signal": "geo_population"},
        tags=("localmarket", "delivery", "geo", v.family),
    )


# ── 29. Local search demand trend ───────────────────────────────────────────
def _local_search_trend(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The search trend is rising now — meeting the demand early is worth more than meeting it once everyone has noticed." if situation == "emerging" else ""
    return Built(
        title=f"People near you are searching for what you sell more than you're selling it",
        observation=f"Local search interest for your category and specific {unit}s is up {X}% in your area, while your matching sales are flat — a demand signal you're not converting.",
        reasoning=f"Local search is intent that hasn't reached your register yet: a rising query trend in your radius is future demand declaring itself. If a {v.name} isn't visible or in-stock for what's being searched, that intent routes to whoever is — the gap between local search and local sales is leakage at the discovery step, upstream of everything in the store.{extra}",
        conclusion=f"Close the discovery gap: make sure the searched {unit}s are visible, in-stock, and findable locally, and align the offer to the rising query.",
        expected_effect=f"Converting the unmet local search interest is worth ~${X}/mo of demand currently leaking to more-visible competitors.",
        recommend_when={"state": "search_demand_unconverted", "min_signal": "search_trends"},
        tags=("localmarket", "search", "demand", v.family),
    )


# ── 30. Neighborhood safety / time-of-day ───────────────────────────────────
def _safety_time_of_day(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Perceived safety, not demand, is capping your late hours",
        observation=f"Your {X} late dayparts run {X}% below their daytime potential, tracking local time-of-day safety patterns rather than any drop in appetite.",
        reasoning=f"For a {v.name} open into the evening, willingness to be in the area after dark gates demand independently of how much customers want the {unit}. Where the surrounding area feels unsafe at certain hours, the late window underperforms no matter the offer — a constraint that comes from the block, not the business, and that lighting/visibility/escort cues address better than discounts.",
        conclusion=f"Treat late-hour softness as an environment problem: improve lighting and visible {v.staff_role} presence, partner on area safety, and right-size hours to where perceived safety actually supports demand.",
        expected_effect=f"Either recovering the late window or trimming unprofitable unsafe hours is worth ~${X}/mo.",
        recommend_when={"state": "safety_gated_hours", "min_signal": "safety_index"},
        tags=("localmarket", "safety", "hours", v.family),
    )


# ── 31. Local sports team impact ────────────────────────────────────────────
def _sports_team_impact(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Game nights swing your demand and you don't plan to the schedule",
        observation=f"Your {unit} volume moves {X}% around local team game days — surging before/after home games and shifting on big televised matches — while staffing follows the day of week.",
        reasoning=f"For a {v.name} in a sports market, the game calendar is a demand calendar: home games concentrate crowds and pre/post-game rushes, and even televised away games reshape the night. Staffing to Tuesday-vs-Saturday instead of to the fixture list mis-covers exactly the highest-variance nights.",
        conclusion=f"Load the local fixture list into planning: pre-stage {v.staff_role} coverage and a game-night {unit} offer for home games and major broadcasts.",
        expected_effect=f"Planning to the sports calendar is worth ~${X}/yr across the game nights currently mis-staffed.",
        recommend_when={"state": "sports_schedule_swing", "min_signal": "local_events"},
        tags=("localmarket", "events", "sports", v.family),
    )


# ── 32. Large employer shift schedule ───────────────────────────────────────
def _employer_shift_rush(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"A big employer's shift change is a rush you don't staff for",
        observation=f"A major employer within {X} runs shift changes at {X}, creating a predictable {unit} surge your coverage template doesn't anticipate.",
        reasoning=f"A nearby plant, hospital, or office releases hundreds of people at fixed times, and a meaningful share routes past a {v.name} with money and a narrow window to spend it. Staffed to a generic daypart, you queue out or stock out at the exact minutes the surge is guaranteed — leaving captive, time-pressed demand at the door.",
        conclusion=f"Align to the shift clock: add {v.staff_role} coverage and a fast {unit} option in the minutes around each shift change, and pre-pack for the rush.",
        expected_effect=f"Provisioning for the shift-change surge captures ~${X}/mo of predictable, time-boxed demand.",
        recommend_when={"state": "employer_shift_surge", "min_signal": "employer_shifts"},
        tags=("localmarket", "employer", "daypart", v.family),
    )


# ── 33. Local fuel price ────────────────────────────────────────────────────
def _fuel_price_impact(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Local fuel prices quietly steer your discretionary demand",
        observation=f"Your {unit} volume softens {X}% when local fuel prices spike, as the same customers cut discretionary stops and drive-by trips.",
        reasoning=f"Fuel price is a tax on every car trip, and a {v.name} that depends on drive-by or drive-thru demand feels it as fewer, more-deliberate visits. Read blind, a fuel-driven dip looks like a you-problem; in truth a recoverable share of customers is consolidating trips, which calls for trip-worthy value, not panic.",
        conclusion=f"During fuel spikes, lean into trip-justifying value — bundles, drive-thru speed, or a reason worth the fuel — instead of discounting indiscriminately.",
        expected_effect=f"Responding to fuel-driven softness with the right lever protects ~${X}/mo versus misreading it as a demand collapse.",
        recommend_when={"state": "fuel_price_sensitivity", "min_signal": "fuel_prices"},
        tags=("localmarket", "fuel", "discretionary", v.family),
    )


# ── 34. Local economic indicator ────────────────────────────────────────────
def _local_econ_indicator(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    when = {
        "declining": " Local indicators are turning down — get ahead of the discretionary pullback rather than reacting to the dip.",
        "emerging": " Local indicators are improving — the trade-up window is opening; lead it, don't lag it.",
    }.get(situation, "")
    return Built(
        title=f"Your demand mix follows the local economy, not just your effort",
        observation=f"Your {unit} mix and basket shift {X}% with local economic indicators (employment, housing, wage trends) in your trade area.",
        reasoning=f"Discretionary spend at a {v.name} expands and contracts with local economic confidence: in a soft local economy customers trade down and stretch replacement cycles, in a strong one they trade up. Planning the assortment and price ladder to a fixed view misses a slow, predictable external tide you could be riding.{when}",
        conclusion=f"Tilt the price ladder and {unit} mix to the local economic direction — protect entry options when it softens, push premium and {v.core_kpis[0]} when it firms.",
        expected_effect=f"Steering the mix with the local economy instead of against it is worth ~${X}/mo through the cycle.",
        recommend_when={"state": "local_econ_sensitivity", "min_signal": "econ_indicators"},
        tags=("localmarket", "economy", "mix", v.family),
    )


# ── 35. Daylight / sunset shift ─────────────────────────────────────────────
def _daylight_shift(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your evening trade tracks the sunset, and your hours don't follow it",
        observation=f"Your {X} evening {unit} window expands and contracts {X}% across the year with daylight, but your hours and {v.staff_role} coverage stay on a fixed clock.",
        reasoning=f"Daylight is a free, perfectly predictable demand driver: longer evenings extend outdoor and after-work activity (and your late window with it), while early winter dark pulls it forward. A {v.name} on fixed hours overstaffs dark winter evenings and closes too early in summer, leaving captured daylight demand on the table — and this one needs only the merchant's location and the date to compute.",
        conclusion=f"Float the evening edge with the sunset: extend hours and coverage as daylight lengthens and pull them in as it shortens, on a seasonal daylight schedule.",
        expected_effect=f"Floating the evening edge to daylight is worth ~${X}/yr in captured summer trade and saved winter labor.",
        recommend_when={"state": "daylight_hours_mismatch", "min_signal": "daylight_calendar"},
        tags=("localmarket", "daylight", "hours", v.family),
    )


# ── 36. Air quality / wildfire smoke ────────────────────────────────────────
def _air_quality(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " A poor-air event is forecast — set the response before the day, not once the patio's empty." if situation == "anomaly" else ""
    return Built(
        title=f"Bad-air days empty your outdoor demand",
        observation=f"On days local air quality crosses {X}, your outdoor or open-air {unit} volume drops {X}% while indoor demand holds or shifts.",
        reasoning=f"Smoke, heat-haze, and poor air quality are acute external shocks that selectively kill the outdoor, sidewalk, and open-air part of a {v.name}'s demand. Customers don't disappear — they retreat indoors or defer — so the right move is to relocate and re-time capacity, not to write the day off or discount blindly.{extra}",
        conclusion=f"Set an air-quality protocol: shift {v.staff_role} and {unit} capacity to indoor/covered options or pickup-delivery on bad-air days, and flex outdoor staffing down.",
        expected_effect=f"Re-routing demand on bad-air days instead of losing it is worth ~${X}/mo across the affected days.",
        recommend_when={"state": "air_quality_outdoor_loss", "min_signal": "air_quality"},
        tags=("localmarket", "air_quality", "weather", v.family),
    )


register(
    Archetype(
        key="local_event_tie_in", domain="localmarket", name="Nearby-event spillover opportunity",
        build=_event_tie_in, situations=("baseline", "emerging", "untapped", "seasonal_peak"),
        required_signals=("local_events", "daily_revenue"),
        required_agents=("LocalEventAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocalEventAgent: ingest a geo+date events calendar API (concerts/sports/festivals) → join events within a radius to daily_revenue by date+location → output an event-vs-matched-baseline lift per event, and a forward list of upcoming event days to staff.",
    ),
    Archetype(
        key="local_event_conflict", domain="localmarket", name="Event displaces regulars",
        build=_event_conflict, situations=("baseline", "anomaly"),
        required_signals=("local_events", "daily_revenue"),
        required_agents=("LocalEventAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocalEventAgent (shared): same events feed → flag event days whose revenue runs BELOW matched baseline (displacement) vs above (spillover), so the same join distinguishes opportunity from conflict.",
    ),
    Archetype(
        key="competitor_proximity_pressure", domain="localmarket", name="Competitor density in radius",
        build=_competitor_proximity, situations=("baseline",),
        required_signals=("competitor_map", "daily_revenue"),
        required_agents=("CompetitorMapAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CompetitorMapAgent: query a places API for same-category businesses within a radius → join competitor count/density to the merchant's geo → output a density-vs-regional-norm index and the implied pricing/share ceiling.",
    ),
    Archetype(
        key="competitor_new_opening", domain="localmarket", name="New competitor opening impact",
        build=_competitor_new_opening, situations=("baseline", "anomaly", "declining"),
        required_signals=("competitor_map", "daily_revenue", "transactions"),
        required_agents=("CompetitorMapAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CompetitorMapAgent (shared): diff the places API over time to detect NEW same-category openings in radius → align opening date to the merchant's daily_revenue/cohort series → output the post-opening dip and the trial-vulnerable cohort.",
    ),
    Archetype(
        key="competitor_closure_opportunity", domain="localmarket", name="Competitor closure capture",
        build=_competitor_closure, situations=("baseline", "emerging", "untapped"),
        required_signals=("competitor_map", "daily_revenue"),
        required_agents=("CompetitorMapAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CompetitorMapAgent (shared): detect CLOSURES (places API disappearance / permanently-closed flag) in radius → estimate displaced demand from the closed shop's footprint → output a capture window and target neighborhood.",
    ),
    Archetype(
        key="competitor_promotion_response", domain="localmarket", name="Competitor promotion pressure",
        build=_competitor_promotion, situations=("baseline",),
        required_signals=("competitor_promotions", "daily_revenue"),
        required_agents=("CompetitorPriceAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CompetitorPriceAgent: scrape competitor menus/listings/ads for active promotions by geo+date → align promo weeks to the merchant's revenue dips → output overlap (does the promoted item hit our core?) and a respond/hold recommendation.",
    ),
    Archetype(
        key="weather_demand_correlation", domain="localmarket", name="Revenue tracks weather",
        build=_weather_correlation, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("weather_feed", "daily_revenue", "hourly_revenue"),
        required_agents=("WeatherFeedAgent",),
        applies_keys=WEATHER_KEYS,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherFeedAgent: pull NOAA/weather-API daily+hourly conditions for the merchant's lat/long → join to daily_revenue/hourly_revenue by date+location → output the weather-explained share of variance and per-condition demand coefficients.",
    ),
    Archetype(
        key="weather_forecast_prestage", domain="localmarket", name="Act on the forecast",
        build=_weather_forecast_prestage, situations=("baseline",),
        required_signals=("weather_forecast", "daily_revenue", "schedule_shifts"),
        required_agents=("WeatherFeedAgent",),
        applies_keys=WEATHER_KEYS,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherFeedAgent (shared): consume the next-day FORECAST → apply the learned weather coefficients to predict tomorrow's demand by daypart → output a staffing/prep adjustment recommendation joined to schedule_shifts.",
    ),
    Archetype(
        key="weather_rain_washout", domain="localmarket", name="Rain defers, dry rebounds",
        build=_rain_washout, situations=("baseline",),
        required_signals=("weather_feed", "daily_revenue"),
        required_agents=("WeatherFeedAgent",),
        applies_keys=("car_wash", "food_truck", "landscaping", "entertainment", "event_venue"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherFeedAgent (shared): tag rain days and the following dry days → measure the rain-day drop and the post-rain rebound from daily_revenue → output the deferral magnitude and rebound window length.",
    ),
    Archetype(
        key="weather_heat_surge", domain="localmarket", name="Heat-wave demand surge",
        build=_heat_surge, situations=("baseline", "seasonal_peak"),
        required_signals=("weather_feed", "hourly_revenue"),
        required_agents=("WeatherFeedAgent",),
        applies_keys=("car_wash", "food_truck", "cafe", "convenience", "grocery"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherFeedAgent (shared): detect temperature-threshold crossings → join to hourly_revenue + product mix → output the surge size, the concentrated hour window, and the heat-relevant SKUs to deepen.",
    ),
    Archetype(
        key="tourism_seasonal_swing", domain="localmarket", name="Seasonal tourism swing",
        build=_tourism_swing, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("tourism_index", "daily_revenue"),
        required_agents=("TourismAgent",),
        applies_keys=TOURISM_KEYS,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TourismAgent: ingest a regional tourism/visitor-volume index (DMO data, lodging occupancy, airport/visitor counts) by geo+date → join to daily_revenue → output the visitor-driven seasonal swing and peak/trough boundaries for two-mode planning.",
    ),
    Archetype(
        key="tourism_vs_local_mix", domain="localmarket", name="Tourist vs local mix",
        build=_tourism_vs_local_mix, situations=("baseline",),
        required_signals=("tourism_index", "transactions", "daily_revenue"),
        required_agents=("TourismAgent",),
        applies_keys=TOURISM_KEYS,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TourismAgent (shared): combine the visitor index with transaction signals (out-of-area cards, one-time vs repeat) to estimate visitor-vs-local share → output the two-segment mix and how each baskets.",
    ),
    Archetype(
        key="demographic_fit", domain="localmarket", name="Neighborhood demographics vs mix",
        build=_demographic_fit, situations=("baseline",),
        required_signals=("demographics_geo", "transactions"),
        required_agents=("DemographicAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DemographicAgent: pull census/ACS income-age-household data for the trade-area geo → compare the area profile to the merchant's product mix and target → output the mismatch and a re-weighting recommendation.",
    ),
    Archetype(
        key="foot_traffic_benchmark", domain="localmarket", name="Foot traffic vs area benchmark",
        build=_foot_traffic_benchmark, situations=("baseline", "emerging", "declining"),
        required_signals=("mobility_traffic", "transactions"),
        required_agents=("MobilityBenchmarkAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MobilityBenchmarkAgent: ingest a mobility/foot-traffic dataset for the block (SafeGraph-style or carrier aggregates) by geo+date → join area pedestrian volume to the merchant's transaction count → output the traffic-vs-sales capture gap and its hours.",
    ),
    Archetype(
        key="market_share_proxy", domain="localmarket", name="Market-share proxy in radius",
        build=_market_share_proxy, situations=("baseline",),
        required_signals=("local_benchmark", "daily_revenue"),
        required_agents=("LocalBenchmarkAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocalBenchmarkAgent: aggregate anonymized cross-merchant revenue by vertical+region → compute addressable category spend in the merchant's radius → divide the merchant's revenue by it for a local-share estimate vs the footprint norm.",
    ),
    Archetype(
        key="regional_price_positioning", domain="localmarket", name="Regional price positioning",
        build=_regional_price_positioning, situations=("baseline",),
        required_signals=("competitor_pricing", "transactions"),
        required_agents=("CompetitorPriceAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CompetitorPriceAgent (shared): collect comparable-item prices from nearby same-category businesses (menus/listings) by geo → place the merchant's price within the local band → output the position (low/mid/high) and the margin-or-volume correction.",
    ),
    Archetype(
        key="localized_holiday", domain="localmarket", name="Region-specific holiday calendar",
        build=_localized_holiday, situations=("baseline", "seasonal_peak"),
        required_signals=("calendar_context", "daily_revenue"),
        required_agents=("CalendarContextAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CalendarContextAgent: load region-specific holiday/observance/festival calendars by locale → join observance dates to daily_revenue → output which local dates move demand (and direction) for pre-set staffing/stocking.",
    ),
    Archetype(
        key="payday_cycle", domain="localmarket", name="Local pay-cycle swing",
        build=_payday_cycle, situations=("baseline",),
        required_signals=("calendar_context", "daily_revenue", "transactions"),
        required_agents=("CalendarContextAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CalendarContextAgent (shared): the intra-month revenue/basket rhythm is already visible in transactions; the upgrade overlays common local pay dates (semi-monthly, government/benefit schedules by region) to LABEL the swing as a pay cycle and phase offers to it.",
    ),
    Archetype(
        key="school_calendar", domain="localmarket", name="School term vs break",
        build=_school_calendar, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("calendar_context", "hourly_revenue"),
        required_agents=("CalendarContextAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CalendarContextAgent (shared): ingest local school-district term/break/holiday dates by geo → join to hourly_revenue dayparts → output the term-vs-break daypart templates and switch dates.",
    ),
    Archetype(
        key="university_term", domain="localmarket", name="University term cliff",
        build=_university_term, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("calendar_context", "daily_revenue"),
        required_agents=("CalendarContextAgent",),
        applies_keys=("cafe", "qsr", "bar", "bookstore", "full_restaurant", "gym", "barbershop", "convenience", "food_truck"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CalendarContextAgent (shared): ingest nearby university academic calendars (term start/end, reading/break weeks) by geo → align the step-function to daily_revenue → output the term-boundary cliff sizes and flex dates.",
    ),
    Archetype(
        key="commuter_pattern", domain="localmarket", name="Commuter flow capture",
        build=_commuter_pattern, situations=("baseline",),
        required_signals=("mobility_traffic", "hourly_revenue"),
        required_agents=("CommuterFlowAgent",),
        applies_keys=COMMUTE_KEYS,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CommuterFlowAgent: ingest directional mobility/traffic flow past the location by hour (mobility dataset or DOT counters) → join inbound/outbound waves to hourly_revenue → output which commute wave is under-captured and its window.",
    ),
    Archetype(
        key="road_closure", domain="localmarket", name="Construction / road-closure access",
        build=_road_closure, situations=("baseline", "anomaly", "declining"),
        required_signals=("road_closures", "daily_revenue"),
        required_agents=("RoadDisruptionAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RoadDisruptionAgent: ingest municipal construction/road-closure permits and traffic-incident feeds by geo+date → align closure periods near the location to daily_revenue → output the access-driven dip, affected dayparts, and closure end date.",
    ),
    Archetype(
        key="transit_disruption", domain="localmarket", name="Transit disruption shift",
        build=_transit_disruption, situations=("baseline", "anomaly"),
        required_signals=("transit_status", "daily_revenue"),
        required_agents=("TransitFeedAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TransitFeedAgent: subscribe to GTFS/transit-alert feeds for nearby stops → flag service changes/disruptions by date → join to daily_revenue to measure the transit-driven swing and pre-warn on scheduled disruptions.",
    ),
    Archetype(
        key="partnership_untapped", domain="localmarket", name="Untapped local partnership",
        build=_partnership_untapped, situations=("baseline", "untapped"),
        required_signals=("business_graph", "transactions"),
        required_agents=("LocalBusinessGraphAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocalBusinessGraphAgent: map non-competing nearby businesses (places API) and estimate customer overlap from co-visitation/mobility or shared-card signals by geo → output the highest-overlap neighbors with no referral relationship as partnership targets.",
    ),
    Archetype(
        key="community_sponsorship", domain="localmarket", name="Community sponsorship reach",
        build=_community_sponsorship, situations=("baseline", "untapped"),
        required_signals=("community_calendar", "demographics_geo"),
        required_agents=("CommunityCalendarAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CommunityCalendarAgent: ingest local community-event/league/charity calendars by geo+date → score audience-demographic fit against the trade-area profile → output ranked sponsorship/presence opportunities with a trackable-offer hook.",
    ),
    Archetype(
        key="anchor_tenant_traffic", domain="localmarket", name="Anchor-tenant traffic timing",
        build=_anchor_tenant, situations=("baseline",),
        required_signals=("anchor_tenants", "hourly_revenue"),
        required_agents=("AnchorTenantAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnchorTenantAgent: identify major nearby traffic anchors (places API: big-box, grocery, transit hub, large employer) and their peak/restock/shift rhythms (mobility or posted hours) by geo → align to hourly_revenue → output the anchor-driven surge windows to staff toward.",
    ),
    Archetype(
        key="rent_revenue_efficiency", domain="localmarket", name="Rent vs revenue efficiency",
        build=_rent_efficiency, situations=("baseline",),
        required_signals=("rent_benchmark", "daily_revenue"),
        required_agents=("LocationCostAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocationCostAgent: ingest local commercial rent/sq-ft benchmarks by geo (and the merchant's lease terms) → compute revenue-per-sq-ft from daily_revenue and benchmark both → output the rent-to-revenue efficiency gap and lift-or-renegotiate path.",
    ),
    Archetype(
        key="delivery_radius_density", domain="localmarket", name="Delivery radius vs density",
        build=_delivery_radius_density, situations=("baseline",),
        required_signals=("geo_population", "transactions"),
        required_agents=("GeoCoverageAgent",),
        applies_flags=("delivery_capable",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="GeoCoverageAgent: pull population/household density (census) and order-location density for the delivery radius by geo → overlay the current zone and routing → output the density-vs-coverage mismatch and a reshaped zone.",
    ),
    Archetype(
        key="local_search_trend", domain="localmarket", name="Local search demand trend",
        build=_local_search_trend, situations=("baseline", "emerging"),
        required_signals=("search_trends", "transactions"),
        required_agents=("SearchTrendAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="SearchTrendAgent: pull localized search-interest trends for the category and key items (search trends API / GBP insights) by geo+date → compare to the merchant's matching sales → output the search-vs-sales discovery gap and the rising queries to stock and surface.",
    ),
    Archetype(
        key="safety_time_of_day", domain="localmarket", name="Safety-gated late hours",
        build=_safety_time_of_day, situations=("baseline",),
        required_signals=("safety_index", "hourly_revenue"),
        required_agents=("SafetyContextAgent",),
        applies_keys=("bar", "full_restaurant", "convenience", "entertainment", "cafe", "qsr", "liquor", "gym", "food_truck"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="SafetyContextAgent: ingest area crime/safety indices by geo and time-of-day → join to hourly_revenue late dayparts → output whether late-hour softness is safety-gated (environment lever) vs demand-gated (hours lever).",
    ),
    Archetype(
        key="sports_team_impact", domain="localmarket", name="Local sports schedule swing",
        build=_sports_team_impact, situations=("baseline",),
        required_signals=("local_events", "daily_revenue"),
        required_agents=("LocalEventAgent",),
        applies_keys=NIGHTLIFE_KEYS + ("convenience", "liquor", "qsr"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocalEventAgent (shared): ingest local team fixture lists (home/away, broadcast times) by geo+date → join game days to daily_revenue → output the pre/post-game and broadcast-night swings to staff toward.",
    ),
    Archetype(
        key="employer_shift_rush", domain="localmarket", name="Employer shift-change surge",
        build=_employer_shift_rush, situations=("baseline",),
        required_signals=("employer_shifts", "hourly_revenue"),
        required_agents=("EmployerContextAgent",),
        applies_keys=COMMUTE_KEYS + ("full_restaurant", "liquor"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="EmployerContextAgent: identify major nearby employers (places API) and their shift-change times (posted/estimated) by geo → align shift boundaries to hourly_revenue spikes → output the predictable surge minutes to staff and pre-pack for.",
    ),
    Archetype(
        key="fuel_price_impact", domain="localmarket", name="Local fuel-price sensitivity",
        build=_fuel_price_impact, situations=("baseline",),
        required_signals=("fuel_prices", "daily_revenue"),
        required_agents=("FuelPriceAgent",),
        applies_keys=("qsr", "convenience", "car_wash", "oil_change", "food_truck", "grocery"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="FuelPriceAgent: ingest local fuel-price series by geo+date → join to daily_revenue for drive-by/drive-thru-dependent verticals → output the fuel-price elasticity and the trip-worthy-value response trigger.",
    ),
    Archetype(
        key="local_econ_indicator", domain="localmarket", name="Local economy mix shift",
        build=_local_econ_indicator, situations=("baseline", "emerging", "declining"),
        required_signals=("econ_indicators", "transactions"),
        required_agents=("EconIndicatorAgent",),
        exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="EconIndicatorAgent: ingest local employment/housing/wage indicators by geo+month → join to the merchant's mix/basket trend → output the trade-up/trade-down direction to tilt the price ladder and assortment toward.",
    ),
    Archetype(
        key="daylight_shift", domain="localmarket", name="Daylight / sunset hours shift",
        build=_daylight_shift, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("daylight_calendar", "hourly_revenue"),
        required_agents=("DaylightAgent",),
        applies_keys=("cafe", "bar", "full_restaurant", "food_truck", "entertainment", "car_wash", "landscaping"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DaylightAgent: sunset/daylight-length is computable from the merchant's lat/long + date with no external feed; the upgrade joins that daylight curve to the evening hourly_revenue window and outputs a seasonal float schedule for hours and coverage.",
    ),
    Archetype(
        key="air_quality_outdoor", domain="localmarket", name="Air-quality outdoor demand loss",
        build=_air_quality, situations=("baseline", "anomaly"),
        required_signals=("air_quality", "daily_revenue"),
        required_agents=("AirQualityAgent",),
        applies_keys=OUTDOOR_KEYS,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AirQualityAgent: ingest local AQI/wildfire-smoke feeds by geo+date (and forecast) → join bad-air days to the outdoor/open-air share of daily_revenue → output the outdoor-demand loss and an indoor/pickup re-routing trigger.",
    ),
)
