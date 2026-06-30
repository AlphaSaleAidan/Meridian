"""
Domain: TIMING / DEMAND-OVER-TIME.

Each archetype is a distinct reasoning pattern about WHEN demand happens — by
hour, daypart, day-of-week, season, holiday, weather, pay cycle, and booking
lead time. Distinctness comes from the LEVER each pattern pulls, not a number:
a peak-hour concentration is a capacity-and-pricing problem, a dead daypart is a
demand-creation problem, a seasonal trough is a cash-and-margin problem, and a
no-show cluster is a scheduling-policy problem. Specialization per vertical
changes the unit and the move (a cafe's morning-rush share reads nothing like a
bar's late-night share or a salon's booking-window gap), so a food-service timing
insight and an appointment-based timing insight are genuinely different.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── Hour / daypart shape ──────────────────────────────────────────────────
def _peak_hour_concentration(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "emerging": " This spike is newly forming — price and staff it before it hardens into the norm.".replace("{x}", X),
        "seasonal_peak": " The approaching season sharpens this peak further; lock capacity now.",
        "volatile": " The peak hour swings week to week, so fixed staffing keeps missing it.",
    }.get(situation, "")
    return Built(
        title=f"One hour ({X}) carries {X}% of your day",
        observation=f"{X}% of daily {unit}s land in the single {X} hour, while the other {X} open hours split the rest.",
        reasoning=f"When demand piles into one hour, throughput — not interest — caps revenue: queue, prep, and {v.staff_role} capacity all bottleneck at once, so marginal demand walks.{extra}",
        conclusion=f"Protect that hour: pre-stage {unit}s, add a {v.staff_role} only for the {X} window, and steer flexible demand to the shoulders with a {X} off-peak nudge.",
        expected_effect=f"Unblocking the single peak hour is worth ~${X}/mo in {unit}s that currently bottleneck.",
        recommend_when={"state": "peak_hour_concentration", "min_signal": "hourly_revenue"},
        tags=("timing", "peak", "capacity", v.family),
    )


def _dead_daypart(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "untapped": " This daypart has never been worked with an offer — it's latent, not lost.",
        "declining": " This daypart used to pull traffic and has gone quiet; defend it before it closes.",
    }.get(situation, "")
    return Built(
        title=f"Your {X} daypart is dead — {X}% of hours, {X}% of sales",
        observation=f"Between {X} and {X} you take only {X}% of daily {unit}s yet carry full fixed cost (rent, light, a {v.staff_role} on the clock).",
        reasoning=f"A dead daypart is a demand problem, not a capacity one: the doors are open and paid for, so any incremental {unit} in that window is almost pure contribution.{extra}",
        conclusion=f"Create demand for the slot — a daypart-specific offer, a {v.channels[0]} promo, or a standing reason-to-come — rather than cutting the hours outright.",
        expected_effect=f"Lifting the dead window to even half your average hour adds ~${X}/mo in near-pure-margin {unit}s.",
        recommend_when={"state": "dead_daypart", "min_signal": "hourly_revenue"},
        tags=("timing", "daypart", "demand_creation", v.family),
    )


def _slowest_day_shift(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Demand is quietly shifting onto your slowest day ({X})",
        observation=f"{X} has grown from {X}% to {X}% of weekly {unit}s over the last {X} weeks while your historically busy {X} flattened.",
        reasoning=f"When the demand curve moves between days, a schedule built for the old pattern overstaffs the fading day while it underserves the rising one, so you pay twice for the lag — idle {v.staff_role} hours on the dead day and lost {unit}s on the busy one.",
        conclusion=f"Rebalance one {v.staff_role} shift from {X} toward {X} and re-point any day-targeted promo to match where demand is actually going.",
        expected_effect=f"Tracking the shift recovers ~${X}/mo otherwise lost to mistimed coverage.",
        recommend_when={"state": "demand_shifting_days", "min_signal": "daily_revenue"},
        tags=("timing", "day_of_week", "trend", v.family),
    )


def _day_of_week_imbalance(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your week is lopsided — {X} does {X}x the volume of {X}",
        observation=f"{X} and {X} together take {X}% of weekly {unit}s; your three slowest days split the remainder.",
        reasoning=f"A lopsided week strands capacity: you're capacity-bound on the heavy days (lost {unit}s) and cost-bound on the light ones (idle {v.staff_role} hours) — same labor budget, wrong distribution.",
        conclusion=f"Move flexible demand off the peak days with a light-day incentive, and slide {v.staff_role} hours from the slow days into the heavy ones.",
        expected_effect=f"Flattening the week is worth ~${X}/mo — captured peak demand plus reclaimed slow-day labor.",
        recommend_when={"state": "day_of_week_imbalance", "min_signal": "daily_revenue"},
        tags=("timing", "day_of_week", "balance", v.family),
    )


# ── Seasonality ───────────────────────────────────────────────────────────
def _seasonality_trough_prep(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    inv = "perishable" in v.flags or "inventory_heavy" in v.flags
    cash_lever = (
        f"taper purchasing/{('perishable ' if 'perishable' in v.flags else '')}stock {X} weeks ahead"
        if inv else f"convert the slow window into prepaid demand (packages, deposits, gift cards)"
    )
    return Built(
        title=f"Your {X} seasonal trough is {X} weeks out — protect cash now",
        observation=f"Last {X} years, {unit}s fell ~{X}% from {X} through {X}; the same dip is approaching.",
        reasoning=f"A trough you can see coming is a cash-and-margin event, not a sales one: the danger is carrying peak-season cost ({v.staff_role} hours, {('inventory, ' if inv else '')}fixed overhead) into thin revenue.",
        conclusion=f"Pre-position: {cash_lever}, flex {v.staff_role} hours down in advance, and pull a demand lever ({v.channels[0]} offer) to soften the floor.",
        expected_effect=f"Entering the trough lean protects ~${X} of margin vs. carrying peak cost into it.",
        recommend_when={"state": "seasonal_trough", "min_signal": "daily_revenue"},
        tags=("timing", "seasonality", "cash", v.family),
    )


def _seasonality_peak_prep(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    inv = "perishable" in v.flags or "inventory_heavy" in v.flags
    capacity_lever = (
        f"pre-build {('par ' if 'perishable' in v.flags else '')}stock and lock supplier lead time"
        if inv else f"open extra {v.staff_role} capacity / booking slots ahead of the rush"
    )
    return Built(
        title=f"Your {X} seasonal peak is {X} weeks out — secure capacity",
        observation=f"Last {X} years, {unit}s rose ~{X}% from {X} through {X}; the ramp is starting again.",
        reasoning=f"A visible peak is a capacity-and-readiness event, so the loss isn't demand — it's the {unit}s you can't fulfill because {v.staff_role} hours{(' and stock' if inv else '')} aren't staged in advance, which means proven demand walks straight to whoever is ready.",
        conclusion=f"Prepare ahead of the curve: {capacity_lever}, schedule {v.staff_role} coverage to the historical shape, and warm demand early via {v.channels[0]}.",
        expected_effect=f"Being ready for the peak captures ~${X}/mo that would otherwise hit a capacity ceiling.",
        recommend_when={"state": "seasonal_peak", "min_signal": "daily_revenue"},
        tags=("timing", "seasonality", "capacity", v.family),
    )


def _holiday_spike(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"{X} drives a {X}% one-day spike you under-prepare for",
        observation=f"Around {X}, daily {unit}s jump ~{X}% above a normal {X}, then snap back within {X} days.",
        reasoning=f"A holiday spike is a short, predictable surge, so it rewards pre-staged capacity and pre-orders and punishes treating it like a normal day — because {v.staff_role} undercoverage and stockouts turn the year's densest demand into walkaways instead of sales.",
        conclusion=f"Run a holiday playbook: take pre-orders/bookings via {v.channels[0]}, staff the spike day to the historical multiple, and prep {unit} supply to the forecast — not the average.",
        expected_effect=f"Capturing the full holiday spike instead of the average is worth ~${X} per occurrence.",
        recommend_when={"state": "holiday_spike", "min_signal": "daily_revenue"},
        tags=("timing", "holiday", "event", v.family),
    )


def _weather_sensitive(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {unit}s swing with the weather and you can't see it coming",
        observation=f"Daily {unit}s move ~{X}% between favorable and adverse weather days, but the swing isn't in any forecast you act on.",
        reasoning=f"Weather is an exogenous demand driver: when a {X}-degree or {X} day is predictable {X} hours out, fixed {v.staff_role} staffing and {('perishable ' if 'perishable' in v.flags else '')}prep that ignore it either waste cost or miss demand.",
        conclusion=f"Tie a same-week weather forecast to staffing and {('prep/stock ' if ('perishable' in v.flags or 'inventory_heavy' in v.flags) else 'promo ')}decisions — flex up for favorable days, trim and discount ahead of adverse ones.",
        expected_effect=f"Acting on a weather signal is worth ~${X}/mo in matched cost and captured weather-driven demand.",
        recommend_when={"state": "weather_sensitive_demand", "min_signal": "daily_revenue"},
        tags=("timing", "weather", "exogenous", v.family),
    )


# ── Food / hospitality specific ───────────────────────────────────────────
def _lunch_vs_dinner_skew(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your lunch and dinner are out of balance — {X} carries {X}% of food sales",
        observation=f"Lunch takes {X}% of daily {unit}s at ${X} average and dinner takes {X}% at ${X}, but you staff and prep both the same.",
        reasoning=f"Lunch and dinner are different businesses (speed and ticket size differ): one prep-and-staffing template can't optimize both, so the weaker daypart drags margin and the stronger one bottlenecks.",
        conclusion=f"Split the playbook — a fast, fixed-price lunch menu and a higher-ticket dinner build, with {v.staff_role} coverage and prep sized to each daypart's real shape.",
        expected_effect=f"Right-sizing each daypart separately is worth ~${X}/mo across faster lunches and richer dinners.",
        recommend_when={"state": "daypart_skew", "min_signal": "hourly_revenue"},
        tags=("timing", "daypart", "menu", v.family),
        # food only
    )


def _morning_rush_share(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your morning rush is {X}% of the day and runs at the throughput ceiling",
        observation=f"{X}% of daily {unit}s land in the {X}–{X} morning window, where line/queue time peaks and attach drops.",
        reasoning=f"A morning rush converts on speed: a slow line costs both walkaways and the high-margin attach ({unit} add-ons) that customers skip when they're in a hurry — the constraint is seconds-per-{unit}, not interest.",
        conclusion=f"Engineer the rush: mobile/{v.channels[-1]} pre-order, a stripped fast-lane menu, and a second {v.staff_role} on bar/pickup for the {X} window only.",
        expected_effect=f"Shaving rush throughput time lifts both volume and attach — worth ~${X}/mo.",
        recommend_when={"state": "morning_rush_concentration", "min_signal": "hourly_revenue"},
        tags=("timing", "morning_rush", "throughput", v.family),
    )


def _late_night_share(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Late-night is {X}% of your take — manage it as its own shift",
        observation=f"After {X}, you do {X}% of daily {unit}s at a {X}% higher average {unit}, but staffing and security are sized to the early evening.",
        reasoning=f"Late-night is a distinct, high-margin, higher-risk daypart: it rewards a dedicated {v.staff_role} setup and pour/serve discipline, and the regulated late window punishes treating it as an extension of dinner.",
        conclusion=f"Run a late-night shift profile — its own {v.staff_role} coverage, last-call and pour controls, and a late-only offer — rather than coasting on the evening setup.",
        expected_effect=f"Treating late-night as its own shift protects ~${X}/mo of its premium take and limits risk.",
        recommend_when={"state": "late_night_concentration", "min_signal": "hourly_revenue"},
        tags=("timing", "late_night", "daypart", v.family),
    )


def _daypart_margin_mix(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your busiest daypart isn't your most profitable one",
        observation=f"The {X} daypart drives the most {unit}s, but the {X} daypart carries a {X}-point higher margin per {unit}.",
        reasoning=f"Volume and margin can live in different windows: chasing the loud daypart while under-pushing the profitable one leaves contribution on the table even when top-line looks fine.",
        conclusion=f"Shift marketing and {v.staff_role} energy toward the high-margin daypart, and lift the high-volume one's mix toward its better-margin {unit}s.",
        expected_effect=f"Reweighting effort toward margin (not just volume) is worth ~${X}/mo in contribution.",
        recommend_when={"state": "daypart_margin_mismatch", "min_signal": "transactions"},
        tags=("timing", "daypart", "margin", v.family),
    )


# ── Appointment-based timing ──────────────────────────────────────────────
def _appointment_lead_time(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your booking lead time ({X} days) is mismatched to demand",
        observation=f"The average {unit} is booked {X} days out, yet {X}% of requests want a slot inside {X} days and can't get one.",
        reasoning=f"Lead-time shape governs yield: too long a book-out turns away same-week demand and invites no-shows, while wide-open near-term slots signal soft demand — either way the {v.staff_role} calendar isn't earning.",
        conclusion=f"Tune the calendar: hold a few near-term slots for high-intent same-week {unit}s, and use waitlist/standby to backfill, instead of booking everything far out.",
        expected_effect=f"Matching lead time to demand recovers ~${X}/mo in same-week {unit}s now turned away.",
        recommend_when={"state": "lead_time_mismatch", "min_signal": "bookings"},
        tags=("timing", "lead_time", "booking", v.family),
        # appointment_based only
    )


def _booking_window_gaps(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your calendar has recurring holes — {X} idle {v.staff_role}-hours/week",
        observation=f"The {X} and {X} windows book to only {X}% of available {v.staff_role} capacity week after week, leaving predictable gaps.",
        reasoning=f"A recurring empty slot is perishable capacity: an unbooked {v.staff_role} hour can never be sold again, so structural gaps are a standing leak, not a random dip.",
        conclusion=f"Fill the known holes deliberately — a gap-window rate, online same-day availability for those slots, and a standby list to plug last-minute openings.",
        expected_effect=f"Filling even half the recurring gaps is worth ~${X}/mo in otherwise-perished {v.staff_role} time.",
        recommend_when={"state": "booking_gaps", "min_signal": "bookings"},
        tags=("timing", "utilization", "booking", v.family),
    )


def _no_show_clustering(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No-shows cluster at specific times — {X} loses {X}% of its {unit}s",
        observation=f"No-show rate runs {X}% overall but spikes to {X}% in the {X} window and on {X}, not evenly across the calendar.",
        reasoning=f"Clustered no-shows are a policy problem, not bad luck: a predictable high-risk window calls for confirmation, deposits, or overbooking precisely there — a flat policy over- or under-protects every slot.",
        conclusion=f"Apply targeted controls to the high-risk window only: tighter confirmation cadence, a deposit/card-hold, or controlled double-booking; leave reliable windows untouched.",
        expected_effect=f"Recovering the clustered no-show window protects ~${X}/mo of {v.staff_role} capacity.",
        recommend_when={"state": "no_show_clustered", "min_signal": "bookings"},
        tags=("timing", "no_show", "policy", v.family),
    )


# ── Cadence / cycle ───────────────────────────────────────────────────────
def _recurring_visit_cadence(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    repeat = "membership" in v.flags
    return Built(
        title=f"Your repeat customers visit every {X} days — but you don't time outreach to it",
        observation=f"Returning customers come back on a ~{X}-day cadence, yet reminders/{('renewal ' if repeat else 'rebook ')}nudges aren't timed to that interval.",
        reasoning=f"A natural visit rhythm is a forecasting gift: a nudge sent at day {X} of a {X}-day cycle catches intent at its peak, while untimed outreach either nags or arrives after the customer has already lapsed.",
        conclusion=f"Trigger outreach off each customer's own cadence — a reminder at ~{X} days via {v.channels[0]} — instead of a flat broadcast schedule.",
        expected_effect=f"Timing nudges to cadence lifts repeat frequency, worth ~${X}/mo in pulled-forward {unit}s.",
        recommend_when={"state": "visit_cadence_untapped", "min_signal": "transactions"},
        tags=("timing", "cadence", "retention", v.family),
    )


def _first_week_of_month_skew(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your first-of-month is front-loaded — week 1 carries {X}% of the month",
        observation=f"The first {X} days of each month take {X}% of monthly {unit}s, then volume sags through the final week.",
        reasoning=f"An intra-month skew is a cash-flow and effort-allocation signal: pushing acquisition in the dead final week and capacity in the front week beats spreading both evenly against an uneven curve.",
        conclusion=f"Schedule a late-month demand push (offer/{v.channels[0]} campaign) to fill the trough and stage capacity for the known week-1 surge.",
        expected_effect=f"Smoothing the month is worth ~${X}/mo by lifting the soft final week toward the strong first.",
        recommend_when={"state": "intra_month_skew", "min_signal": "daily_revenue"},
        tags=("timing", "month_cycle", "cash", v.family),
    )


def _payday_cycle_demand(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your demand tracks the pay cycle — {X} spikes, mid-cycle sags",
        observation=f"{unit}s and average ticket rise ~{X}% in the {X} days after common paydays ({X}, month-end) and dip between them.",
        reasoning=f"Pay-cycle sensitivity means discretionary spend is liquidity-gated: high-ticket {unit}s and upsells land on payday, while the mid-cycle trough responds to value/entry-price offers, not premium ones.",
        conclusion=f"Time the offer to the wallet — push premium/{('high-ticket ' if 'high_ticket' in v.flags else '')}{unit}s and add-ons around payday, run value/payment-friendly promos mid-cycle.",
        expected_effect=f"Aligning offers to the pay cycle is worth ~${X}/mo in better-timed {unit} demand.",
        recommend_when={"state": "payday_cycle", "min_signal": "transactions"},
        tags=("timing", "pay_cycle", "pricing", v.family),
    )


# ── Additional hour / week shape ──────────────────────────────────────────
def _shoulder_hour_opportunity(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"The hours flanking your peak are half-empty — spread the rush",
        observation=f"Your {X} peak runs at capacity while the {X} and {X} shoulder hours sit at only {X}% of it.",
        reasoning=f"When the peak is capacity-bound and the adjacent hours are slack, every {unit} you can pull into a shoulder is incremental — it relieves the bottleneck instead of competing for it.",
        conclusion=f"Shift flexible demand off the peak into the shoulders with a time-boxed shoulder-hour incentive, rather than only trying to add capacity at the top.",
        expected_effect=f"Smoothing the peak into its shoulders captures ~${X}/mo of demand that currently bounces off the ceiling.",
        recommend_when={"state": "shoulder_hour_opportunity", "min_signal": "hourly_revenue"},
        tags=("timing", "peak", "smoothing", v.family),
    )


def _weekend_weekday_mix(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Weekend and weekday are different businesses — you run one playbook",
        observation=f"Weekends carry {X}% of {unit}s at a ${X} average; weekdays carry the rest at ${X}, but staffing, hours, and offers are identical.",
        reasoning=f"Weekend and weekday demand differ in mission and basket: one menu/{v.staff_role}-plan can't serve both well, so the weaker pattern drags margin and the stronger one runs short.",
        conclusion=f"Split the approach — weekend capacity and offers tuned to its higher-ticket {unit}s, a leaner weekday plan tuned to frequency.",
        expected_effect=f"Running weekend and weekday as distinct profiles is worth ~${X}/mo across both.",
        recommend_when={"state": "weekend_weekday_mismatch", "min_signal": "daily_revenue"},
        tags=("timing", "weekend", "mix", v.family),
    )


def _happy_hour_window(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You have a slack {X} window perfect for a demand-shaping offer",
        observation=f"The {X}–{X} window sits at {X}% of your peak yet carries full {v.staff_role} cost and capacity.",
        reasoning=f"A deliberate time-boxed offer (a 'happy hour' construct) turns slack capacity into traffic without cannibalizing the peak — the discount only applies where you have nothing to lose and a habit to build.",
        conclusion=f"Stand up a recurring {X} window offer on margin-friendly {unit}s, promoted via {v.channels[0]}, and measure incremental vs. pulled-forward traffic.",
        expected_effect=f"A working off-peak window adds ~${X}/mo in incremental, near-pure-margin {unit}s.",
        recommend_when={"state": "offpeak_offer_opportunity", "min_signal": "hourly_revenue"},
        tags=("timing", "daypart", "demand_creation", v.family),
        # food / hospitality
    )


def _closing_hour_runoff(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your last open hour is nearly dead — {X}% of an average hour",
        observation=f"The final hour before close produces only {X}% of your typical hour's {unit}s, yet a {v.staff_role}, lights, and {('perishable holding ' if 'perishable' in v.flags else 'overhead ')}all run full.",
        reasoning=f"The closing hour is a clean trim-or-activate decision: it either earns its fixed cost or it doesn't, and right now it doesn't — so the choice is shorten hours or give a reason to come late.",
        conclusion=f"Test both directions: trim the closing hour for {X} weeks against an end-of-day {('markdown on perishables' if 'perishable' in v.flags else 'closing offer')} — keep whichever clears the fixed cost.",
        expected_effect=f"Resolving the dead closing hour is worth ~${X}/mo either way (saved cost or captured late demand).",
        recommend_when={"state": "closing_hour_dead", "min_signal": "hourly_revenue"},
        tags=("timing", "hours", "daypart", v.family),
    )


def _opening_ramp_lag(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Demand doesn't arrive until {X} after you open",
        observation=f"Your first {X} open hours produce only {X}% of daily {unit}s; real traffic doesn't start until {X}.",
        reasoning=f"An opening ramp lag means you pay setup, a {v.staff_role}, and utilities against near-zero demand — the open time is a habit, not a demand-backed choice.",
        conclusion=f"Either push the open {X} later, or seed early demand with an open-window offer/{v.channels[0]} reason-to-come-early — don't keep paying for empty open hours by default.",
        expected_effect=f"Right-sizing the open is worth ~${X}/mo in reclaimed dead-start cost or captured early demand.",
        recommend_when={"state": "opening_ramp_lag", "min_signal": "hourly_revenue"},
        tags=("timing", "hours", "open", v.family),
    )


def _demand_volatility_by_hour(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {X} hour is unpredictable — it swings {X}% day to day",
        observation=f"The {X} window averages a normal load but ranges from {X} to {X} {unit}s on different days of the same weekday — high variance, not a stable shape.",
        reasoning=f"A volatile hour defeats fixed staffing: schedule to the average and you alternately overpay and get buried, so the answer is flexible capacity, not a different fixed number.",
        conclusion=f"Cover the volatile window with on-call/flex {v.staff_role} capacity and a same-day call-in trigger tied to early-signal volume, instead of a single fixed headcount.",
        expected_effect=f"Matching flexible coverage to the swing is worth ~${X}/mo in avoided idle and captured surge.",
        recommend_when={"state": "hourly_volatility", "min_signal": "hourly_revenue"},
        tags=("timing", "volatility", "capacity", v.family),
    )


def _advance_booking_mix_shift(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your pre-booked vs. same-day mix is shifting toward {X}",
        observation=f"Pre-booked {unit}s have moved from {X}% to {X}% of the calendar over {X} weeks, with same-day/walk-in demand making up the difference.",
        reasoning=f"The advance/same-day mix dictates how you hold the calendar: more same-day demand means holding open slots beats booking everything out, and the reverse if it's drying up — a wrong-way policy strands {v.staff_role} time.",
        conclusion=f"Follow the mix — adjust how many near-term slots you protect for same-day {unit}s vs. release for advance booking, and re-tune confirmation cadence accordingly.",
        expected_effect=f"Keeping calendar policy aligned to the mix recovers ~${X}/mo of otherwise-idle {v.staff_role} capacity.",
        recommend_when={"state": "advance_mix_shift", "min_signal": "bookings"},
        tags=("timing", "booking", "mix", v.family),
        # appointment_based
    )


def _inquiry_to_sale_lag(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {v.channels[0]} inquiries lead sales by {X} days — use them as a forecast",
        observation=f"Inquiry/quote volume via {v.channels[0]} rises ~{X} days before {unit}s do, but you don't staff or stock to that leading signal.",
        reasoning=f"A reliable inquiry-to-sale lag is free forward visibility: acting on it lets you stage {v.staff_role} hours and {('stock ' if ('inventory_heavy' in v.flags or 'perishable' in v.flags) else 'capacity ')}ahead of demand instead of reacting after it lands.",
        conclusion=f"Track {v.channels[0]} inquiry volume as a {X}-day leading indicator and schedule capacity to it, rather than to last week's sales.",
        expected_effect=f"Acting on the leading signal is worth ~${X}/mo in better-timed capacity and fewer missed {unit}s.",
        recommend_when={"state": "leading_inquiry_signal", "min_signal": "inquiries"},
        tags=("timing", "leading_indicator", "forecast", v.family),
    )


def _service_time_drift(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Time per {unit} has crept up {X}% — silent capacity loss",
        observation=f"Average time per {unit} drifted from {X} to {X} minutes over {X} weeks while {v.staff_role} headcount and open hours held flat.",
        reasoning=f"Throughput is capacity divided by time-per-{unit}, so when service time creeps up the same staffed hours hold fewer {unit}s — which means effective capacity shrank without anyone cutting a shift, and a throughput-bound business loses the difference at every peak.",
        conclusion=f"Set a target time-per-{unit}, trim the slowest step in the {unit} flow, and stage prep ahead so the {v.staff_role} isn't building capacity from scratch at the peak.",
        expected_effect=f"Recovering the drifted {X}% of service time adds back ~${X}/mo of peak throughput.",
        recommend_when={"state": "service_time_drift", "min_signal": "transactions"},
        tags=("timing", "throughput", "capacity", v.family),
    )


def _daylight_demand_shift(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your evening trade shrinks with the daylight — {X}% swing",
        observation=f"Post-{X} {unit}s fall ~{X}% in the short-daylight months versus the long-daylight ones, even though your close time never changes.",
        reasoning=f"Foot traffic tracks daylight rather than the clock, so when sunset moves earlier the after-dark hours empty out while you still pay a {v.staff_role}, lights, and heat against them — which turns a fixed closing schedule into a seasonal cost leak the calendar hides.",
        conclusion=f"Shift the close earlier in short-daylight months and redeploy those {v.staff_role} hours into the busier afternoon, rather than holding one schedule year-round.",
        expected_effect=f"Flexing hours to daylight saves ~${X}/mo of dead after-dark cost.",
        recommend_when={"state": "daylight_demand_shift", "min_signal": "hourly_revenue"},
        tags=("timing", "seasonality", "hours", v.family),
    )


def _local_event_demand(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Nearby events move your demand {X}% — and you don't plan for them",
        observation=f"On days with a major event within {X} miles, {unit}s swing ~{X}% versus a normal {X}, but staffing and prep don't change for them.",
        reasoning=f"A scheduled local event is a known demand shock, so ignoring the venue calendar means you under-staff the inbound-crowd days and over-staff the ones an event pulls traffic away — which leaks lost {unit}s when the crowd arrives and idle {v.staff_role} cost when it doesn't.",
        conclusion=f"Build the local-event calendar into the schedule — add {v.staff_role} coverage and prep for inbound-crowd events, and trim hours for events that draw traffic elsewhere.",
        expected_effect=f"Planning to the event calendar is worth ~${X}/mo in matched cost and captured surge.",
        recommend_when={"state": "local_event_sensitivity", "min_signal": "daily_revenue"},
        tags=("timing", "event", "exogenous", v.family),
    )


# ── Registration ──────────────────────────────────────────────────────────
register(
    Archetype(
        key="peak_hour_concentration", domain="timing", name="One-hour concentration",
        build=_peak_hour_concentration,
        situations=("baseline", "emerging", "seasonal_peak", "volatile"),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="dead_daypart", domain="timing", name="Dead daypart",
        build=_dead_daypart,
        situations=("baseline", "untapped", "declining"),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="slowest_day_shift", domain="timing", name="Demand shifting onto slow day",
        build=_slowest_day_shift,
        situations=("baseline", "emerging"),
        required_signals=("daily_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="day_of_week_imbalance", domain="timing", name="Lopsided week",
        build=_day_of_week_imbalance,
        situations=("baseline",),
        required_signals=("daily_revenue",),
        required_agents=("PatternAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="seasonality_trough_prep", domain="timing", name="Seasonal trough prep",
        build=_seasonality_trough_prep,
        situations=("seasonal_trough",),
        required_signals=("daily_revenue",),
        required_agents=("SeasonalityAgent", "ForecastAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="SeasonalityAgent: needs >=13 months of daily_revenue history to fit a season curve; current ingestion window is shorter — extend the historical backfill before this fires reliably.",
    ),
    Archetype(
        key="seasonality_peak_prep", domain="timing", name="Seasonal peak prep",
        build=_seasonality_peak_prep,
        situations=("seasonal_peak",),
        required_signals=("daily_revenue",),
        required_agents=("SeasonalityAgent", "ForecastAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="SeasonalityAgent (shared): same multi-year history requirement; ForecastAgent projects the ramp to size pre-built capacity/stock.",
    ),
    Archetype(
        key="holiday_spike", domain="timing", name="Holiday spike",
        build=_holiday_spike,
        situations=("baseline", "seasonal_peak"),
        required_signals=("daily_revenue",),
        required_agents=("SeasonalityAgent", "CalendarAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CalendarAgent: join daily_revenue to a holiday/local-event calendar (not yet ingested) to isolate holiday lift from ordinary day-of-week effects.",
    ),
    Archetype(
        key="weather_sensitive_demand", domain="timing", name="Weather-sensitive demand",
        build=_weather_sensitive,
        situations=("baseline", "volatile"),
        required_signals=("daily_revenue",),
        required_agents=("WeatherFeedAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WeatherFeedAgent: ingest a daily historical + forecast weather feed keyed to merchant location, regress daily_revenue on weather to quantify sensitivity and drive same-week staffing/prep decisions. No weather source is wired today.",
    ),
    Archetype(
        key="lunch_vs_dinner_skew", domain="timing", name="Lunch vs dinner skew",
        build=_lunch_vs_dinner_skew,
        situations=("baseline",),
        applies_families=("food_service", "hospitality"),
        required_signals=("hourly_revenue", "transactions"),
        required_agents=("PatternAnalyzer", "DaypartAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="morning_rush_share", domain="timing", name="Morning rush concentration",
        build=_morning_rush_share,
        situations=("baseline", "emerging"),
        applies_keys=("cafe", "bakery", "qsr", "convenience"),
        required_signals=("hourly_revenue", "transactions"),
        required_agents=("PatternAnalyzer", "DaypartAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="late_night_share", domain="timing", name="Late-night share",
        build=_late_night_share,
        situations=("baseline",),
        applies_keys=("bar", "full_restaurant", "entertainment", "dispensary"),
        required_signals=("hourly_revenue", "transactions"),
        required_agents=("PatternAnalyzer", "DaypartAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="daypart_margin_mix", domain="timing", name="Volume vs margin daypart",
        build=_daypart_margin_mix,
        situations=("baseline",),
        required_signals=("transactions", "hourly_revenue"),
        required_agents=("DaypartAgent", "MarginAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MarginAnalyzer: needs per-item/per-{unit} cost (COGS) joined to transactions by daypart to compare margin, not just revenue, across windows. Cost data is not ingested yet.",
    ),
    Archetype(
        key="appointment_lead_time", domain="timing", name="Booking lead-time mismatch",
        build=_appointment_lead_time,
        situations=("baseline", "leaking"),
        applies_flags=("appointment_based",),
        required_signals=("bookings",),
        required_agents=("BookingAgent", "DemandShapeAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingAgent: needs booking-created vs appointment-start timestamps AND turned-away/declined request logs to measure lead time vs unmet near-term demand. Request/decline events are not captured today.",
    ),
    Archetype(
        key="booking_window_gaps", domain="timing", name="Recurring calendar gaps",
        build=_booking_window_gaps,
        situations=("baseline", "leaking"),
        applies_flags=("appointment_based",),
        required_signals=("bookings", "schedule_shifts"),
        required_agents=("BookingAgent", "UtilizationAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="UtilizationAgent: join bookings to per-{role} availability/schedule to compute open-slot capacity per window; availability calendar (not just booked events) must be ingested.",
    ),
    Archetype(
        key="no_show_clustering", domain="timing", name="No-show time clustering",
        build=_no_show_clustering,
        situations=("baseline", "concentrated"),
        applies_flags=("appointment_based",),
        required_signals=("bookings",),
        required_agents=("BookingAgent", "NoShowAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="NoShowAgent: needs appointment outcome status (kept/cancelled/no-show) on bookings to bucket no-show rate by hour/day. Outcome status is inconsistently captured — normalize it at ingestion.",
    ),
    Archetype(
        key="recurring_visit_cadence", domain="timing", name="Repeat visit cadence",
        build=_recurring_visit_cadence,
        situations=("baseline", "untapped"),
        applies_flags=("repeat_purchase",),
        required_signals=("transactions",),
        required_agents=("CustomerJourneyAgent", "CadenceAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CadenceAgent: requires customer identity to stitch repeat visits per person (join transactions to anonymous_customer_profiles/caller_memory_index) and derive an inter-visit interval. No per-customer linkage exists for walk-in transactions yet.",
    ),
    Archetype(
        key="first_week_of_month_skew", domain="timing", name="Intra-month skew",
        build=_first_week_of_month_skew,
        situations=("baseline",),
        required_signals=("daily_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="payday_cycle_demand", domain="timing", name="Pay-cycle demand",
        build=_payday_cycle_demand,
        situations=("baseline",),
        required_signals=("transactions", "daily_revenue"),
        required_agents=("PatternAnalyzer", "CalendarAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CalendarAgent (shared): map daily_revenue to pay-cycle markers (15th/month-end/local payroll patterns) to separate payday lift from ordinary month-cycle effects.",
    ),
    Archetype(
        key="shoulder_hour_opportunity", domain="timing", name="Shoulder-hour smoothing",
        build=_shoulder_hour_opportunity,
        situations=("baseline", "untapped"),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="weekend_weekday_mix", domain="timing", name="Weekend vs weekday mix",
        build=_weekend_weekday_mix,
        situations=("baseline",),
        required_signals=("daily_revenue", "transactions"),
        required_agents=("PatternAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="happy_hour_window", domain="timing", name="Off-peak offer window",
        build=_happy_hour_window,
        situations=("baseline", "untapped"),
        applies_families=("food_service", "hospitality"),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "DaypartAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="closing_hour_runoff", domain="timing", name="Dead closing hour",
        build=_closing_hour_runoff,
        situations=("baseline",),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="opening_ramp_lag", domain="timing", name="Slow opening ramp",
        build=_opening_ramp_lag,
        situations=("baseline",),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "TimeSeriesAgent"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="demand_volatility_by_hour", domain="timing", name="Volatile hour",
        build=_demand_volatility_by_hour,
        situations=("volatile",),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "VarianceAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VarianceAgent: compute per-hour-of-weekday variance/dispersion across history (not just the mean) to flag windows where flexible coverage beats a fixed headcount. Current PatternAnalyzer reports averages only.",
    ),
    Archetype(
        key="advance_booking_mix_shift", domain="timing", name="Advance vs same-day mix",
        build=_advance_booking_mix_shift,
        situations=("baseline", "emerging", "declining"),
        applies_flags=("appointment_based",),
        required_signals=("bookings",),
        required_agents=("BookingAgent", "DemandShapeAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingAgent (shared): needs booking-created vs appointment-start timestamps to classify each {unit} as advance vs same-day and trend the mix.",
    ),
    Archetype(
        key="inquiry_to_sale_lag", domain="timing", name="Leading inquiry signal",
        build=_inquiry_to_sale_lag,
        situations=("baseline",),
        required_signals=("inquiries", "daily_revenue"),
        required_agents=("ChannelAgent", "LeadingIndicatorAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LeadingIndicatorAgent: ingest dated inquiry/quote/call volume per channel (caller_memory_index gives phone inquiries; web/booking inquiries are not yet captured) and cross-correlate against daily_revenue to estimate the lead and drive forward staffing/stock.",
    ),
    Archetype(
        key="service_time_drift", domain="timing", name="Service-time drift",
        build=_service_time_drift,
        situations=("baseline", "emerging"),
        required_signals=("transactions", "hourly_revenue"),
        required_agents=("PatternAnalyzer", "ThroughputAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ThroughputAgent: derive time-per-{unit} from transaction timestamps (or order-open-to-close) and trend it over weeks to separate a capacity loss from a demand drop. Per-order duration is not yet computed.",
    ),
    Archetype(
        key="daylight_demand_shift", domain="timing", name="Daylight-driven hour shift",
        build=_daylight_demand_shift,
        situations=("baseline",),
        required_signals=("hourly_revenue",),
        required_agents=("SeasonalityAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="SeasonalityAgent: join hourly_revenue to local sunset times by date to attribute after-dark demand decay to daylight rather than season. A sunrise/sunset table keyed to merchant location must be added.",
    ),
    Archetype(
        key="local_event_demand", domain="timing", name="Local-event demand shock",
        build=_local_event_demand,
        situations=("baseline",),
        required_signals=("daily_revenue",),
        required_agents=("CalendarAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CalendarAgent: ingest a geo-scoped local-event feed (stadiums, venues, conventions within a radius) and join to daily_revenue to isolate event-driven swings from ordinary day-of-week effects. No local-event source is wired today.",
    ),
)
