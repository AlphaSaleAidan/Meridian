"""
Domain: CAPACITY / BOOKING.

Each archetype is a distinct reasoning pattern about the BOOKABLE or PHYSICAL
RESOURCE — slots on a calendar, tables, chairs, bays, rooms, classes, lanes —
NOT the people who staff it (that is the labor domain) and NOT raw demand timing
(that is the footfall/timing domains). The lever here always moves a unit of
sellable capacity: open a slot, tighten a turn, add a buffer, set a deposit,
fill an off-peak hour. Specialization changes that unit per vertical so a salon
chair-idle insight, an auto bay-idle insight, and a restaurant table-turn insight
are genuinely different reasoning, not relabeled.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── helpers ───────────────────────────────────────────────────────────────
def _bookable_unit(v: Vertical) -> str:
    """The physical/bookable resource one booking consumes."""
    if "table_service" in v.flags:
        return "table"
    if v.key in ("salon", "barbershop", "nail_salon"):
        return "chair"
    if v.key in ("spa", "med_spa", "dental", "physio", "chiro", "optometry", "vet", "tattoo"):
        return "room"
    if v.key in ("auto_repair", "oil_change", "tire_shop"):
        return "bay"
    if v.family == "fitness":
        return "class spot"
    if v.key in ("car_wash",):
        return "lane"
    return "slot"


def _calendar_gap(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    sale = v.sale_unit
    extra = {
        "untapped": " You have never marketed these open windows — start by surfacing them at booking time.",
        "declining": " These gaps used to fill; demand has drifted to other days while the calendar stayed fixed.",
    }.get(situation, "")
    return Built(
        title=f"{X}% of your bookable {unit}s sit empty on {X}",
        observation=f"Across a typical week {X} {unit}-hours are open for booking but never fill, concentrated on {X} between {X} and {X}.",
        reasoning=f"Each idle {unit}-hour is perishable inventory — once {X} passes it cannot be resold, and your {v.core_kpis[1]} runs {X}% below the days that do fill.{extra}",
        conclusion=f"Promote the {X} open windows with a targeted offer or shift discretionary {sale}s into them before opening new capacity.",
        expected_effect=f"Filling even half the idle {unit}-hours is worth ~${X}/mo at your current {sale} value.",
        recommend_when={"state": "bookable_calendar_gap", "min_signal": "booking_calendar"},
        tags=("capacity", "utilization", v.family),
    )


def _inter_appointment_idle(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    role = v.staff_role
    return Built(
        title=f"Dead time between bookings is eating {X} {unit}-hours/week",
        observation=f"The average gap between consecutive bookings on the same {unit} is {X} minutes — {X} idle minutes per {role} per day.",
        reasoning=f"These sub-bookable gaps are too short to sell yet add up to {X} lost {v.sale_unit}-equivalents weekly; tighter scheduling, not more {unit}s, recovers them.",
        conclusion=f"Compress booking spacing on {X} or backfill gaps with {X}-minute add-on services that fit the window.",
        expected_effect=f"Reclaiming inter-booking idle time adds ~${X}/mo without extending hours or adding a {unit}.",
        recommend_when={"state": "inter_appointment_idle", "min_signal": "booking_calendar"},
        tags=("capacity", "utilization", v.family),
    )


def _double_booking_friction(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Double-booked {unit}s are forcing waits or bumped bookings",
        observation=f"{X}% of {X} days show two bookings assigned to one {unit} in the same window, leading to {X} bumped or delayed {v.sale_unit}s.",
        reasoning=f"Overlap that isn't a deliberate buffer creates waiting-room friction and rushed service — it dents {v.core_kpis[0]} and review scores, not just the schedule.",
        conclusion=f"Add a hard {unit}-conflict block in the booking rules and move the overflow to the verified idle {X} window.",
        expected_effect=f"Removing the conflicts protects ~${X}/mo of at-risk {v.sale_unit}s and the rebookings they drive.",
        recommend_when={"state": "double_booking_conflict", "min_signal": "booking_calendar"},
        tags=("capacity", "friction", v.family),
    )


def _overbooking_untapped(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"No-show buffer untapped — you lose {X} {unit}-slots to empty no-shows",
        observation=f"Your no-show rate runs {X}% on {X}, yet you book each {unit} 1:1 with zero overbooking cushion.",
        reasoning=f"Because every no-show leaves a perishable {unit} empty, a measured overbook on high-no-show windows recovers capacity the way airlines do — the risk is bounded by your historical no-show floor.",
        conclusion=f"Overbook the {X} window by {X}% (capped at the no-show floor) and hold a short standby list to absorb the rare full-show.",
        expected_effect=f"Converting predictable no-shows into filled {unit}s is worth ~${X}/mo in otherwise-dead capacity.",
        recommend_when={"state": "overbooking_untapped", "min_signal": "no_show_log"},
        tags=("capacity", "no_show", v.family),
    )


def _lead_time_too_long(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Your booking lead time is too long and you lose {X}% of would-be {sale}s",
        observation=f"The soonest available {sale} is {X} days out, while {X}% of inbound requests want service within {X} days.",
        reasoning=f"Customers who can't book soon enough go elsewhere — long lead time reads as 'fully booked' even when later {X} windows sit open, so demand and capacity miss each other.",
        conclusion=f"Reserve a daily {X} same-week express block and steer urgent requests into it instead of the far calendar.",
        expected_effect=f"Capturing the impatient segment is worth ~${X}/mo in {sale}s currently lost to lead time.",
        recommend_when={"state": "lead_time_loses_bookings", "min_signal": "booking_calendar"},
        tags=("capacity", "conversion", v.family),
    )


def _cancellation_window(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Last-minute cancellations leave {X} {unit}-slots unfillable",
        observation=f"{X}% of cancellations land inside {X} hours of the booking — too late to resell, costing {X} empty {unit}-slots/week.",
        reasoning=f"A short notice window means the {unit} dies empty; a longer notice rule plus an instant waitlist ping turns the cancelled slot back into sellable inventory.",
        conclusion=f"Set a {X}-hour cancellation policy and auto-offer freed {unit}s to a standby waitlist the moment they open.",
        expected_effect=f"Reselling late cancellations recovers ~${X}/mo of perishable {unit} capacity.",
        recommend_when={"state": "late_cancellation_unfillable", "min_signal": "booking_calendar"},
        tags=("capacity", "cancellation", v.family),
    )


def _waitlist_untapped(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"No waitlist — freed {unit}s vanish instead of being resold",
        observation=f"On {X} you turn away {X} requests at peak, yet {X} same-day {unit}s later open via cancellation and go unfilled.",
        reasoning=f"Without a waitlist there is no mechanism to reconnect overflow demand with capacity that opens up later the same day — two solvable problems cancel each other unsolved.",
        conclusion=f"Stand up an opt-in waitlist and auto-notify the next person when a {unit} frees on a {X} peak day.",
        expected_effect=f"Matching turn-aways to freed {unit}s is worth ~${X}/mo at no added capacity cost.",
        recommend_when={"state": "waitlist_untapped", "min_signal": "booking_calendar"},
        tags=("capacity", "waitlist", v.family),
    )


def _slot_granularity(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    sale = v.sale_unit
    return Built(
        title=f"Your booking slot size doesn't match how long {sale}s actually take",
        observation=f"Slots are sold in {X}-minute increments but actual {sale} duration clusters at {X} minutes, leaving {X} stranded minutes per {unit} per day.",
        reasoning=f"Granularity that's coarser than real service time wastes the remainder of each slot; finer or service-typed slots pack the {unit} tighter without rushing anyone.",
        conclusion=f"Re-tier slots to {X}-minute granularity (or per-service durations) so back-to-back bookings leave no stranded remainder.",
        expected_effect=f"Tighter slot packing recovers ~${X}/mo of {unit} time already paid for.",
        recommend_when={"state": "slot_granularity_mismatch", "min_signal": "booking_calendar"},
        tags=("capacity", "scheduling", v.family),
    )


def _table_turn_slow(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Table turns are running {X} min slow during your {X} rush",
        observation=f"Average table occupancy is {X} minutes at peak versus {X} off-peak — {X} fewer {v.sale_unit}s seated per table on your busiest nights.",
        reasoning=f"At peak the binding constraint is the table, not the kitchen or the floor; every extra minute per turn is a cover you physically cannot seat, so turn time converts directly into lost covers.",
        conclusion=f"Tighten the peak turn (pre-bussing, prompt check-drop, pacing) on {X} and hold a {X}-minute target; leave off-peak relaxed.",
        expected_effect=f"Shaving the peak turn by {X} minutes adds ~${X}/mo in incremental covers.",
        recommend_when={"state": "slow_table_turn_at_peak", "min_signal": "table_timing"},
        tags=("capacity", "turn_time", v.family),
    )


def _resource_idle_between_uses(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Each {unit} idles {X} min between uses — turnaround, not demand, is the cap",
        observation=f"Reset/cleanup between {v.sale_unit}s averages {X} minutes per {unit}, holding {v.core_kpis[1]} to {X}% even on fully-booked days.",
        reasoning=f"When a {unit} is booked solid yet utilization stalls, the loss is changeover time — faster reset adds throughput on the exact days you're already turning people away.",
        conclusion=f"Stage prep and cut {unit} turnaround to {X} minutes on {X}; standardize the reset so the next {v.sale_unit} starts on time.",
        expected_effect=f"Cutting changeover frees ~{X} extra {v.sale_unit}s/week, ~${X}/mo, with no new {unit}.",
        recommend_when={"state": "resource_changeover_drag", "min_signal": "booking_calendar"},
        tags=("capacity", "throughput", v.family),
    )


def _class_below_fill(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your {X} classes run {X}% below fill",
        observation=f"The {X} time slot averages {X} of {X} spots filled, while {X} sells out and turns members away.",
        reasoning=f"A class's marginal cost is fixed once the instructor is booked, so every empty spot is pure lost contribution — and chronically thin classes also feel dead, which suppresses rebooking.",
        conclusion=f"Consolidate or re-time the under-filled {X} class and redirect that capacity toward the {X} slot that overflows.",
        expected_effect=f"Right-sizing the class grid lifts contribution ~${X}/mo and protects the sold-out experience.",
        recommend_when={"state": "class_below_fill", "min_signal": "class_roster"},
        tags=("capacity", "fill_rate", v.family),
    )


def _prep_capacity_vs_demand(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Prep/kitchen capacity caps you out before the dining room does",
        observation=f"On {X} the kitchen hits its ticket ceiling at {X} orders/hr while {X} seats/lanes still sit open downstream.",
        reasoning=f"When the back-of-house throughput ceiling is below front-of-house capacity, adding covers or speeding turns just lengthens ticket times — prep capacity is the real bottleneck on peak {v.sale_unit}s.",
        conclusion=f"Pre-batch the {X} high-volume items and add a prep hand for the {X} window so the kitchen ceiling rises to meet the room.",
        expected_effect=f"Lifting the prep ceiling unlocks ~${X}/mo of demand the dining capacity could already serve.",
        recommend_when={"state": "prep_capacity_bottleneck", "min_signal": "ticket_timing"},
        tags=("capacity", "throughput", v.family),
    )


def _no_deposit_leakage(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"No deposit on bookings — flaky reservations cost you {X} {unit}-slots",
        observation=f"{X}% of no-deposit bookings no-show or cancel late, versus {X}% when a deposit is on file; you take no deposit on {X} of bookings.",
        reasoning=f"A deposit changes the customer's commitment and lets you hold the {unit} with confidence; without it, high-value windows get blocked by reservations that never convert.",
        conclusion=f"Require a {X} deposit (credited to the bill) on {X} and high-value {v.sale_unit}s; keep walk-in and low-risk slots deposit-free.",
        expected_effect=f"Deposit-gating the flaky bookings recovers ~${X}/mo of {unit} capacity lost to no-shows.",
        recommend_when={"state": "reservation_no_deposit_leakage", "min_signal": "booking_calendar"},
        tags=("capacity", "no_show", v.family),
    )


def _peak_day_turnaways(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"{X} is fully booked and turning away {X} {v.sale_unit}s/week",
        observation=f"{X} books out {X} days ahead with {X} unmet requests, while {X} runs {X}% empty.",
        reasoning=f"A single saturated day signals real demand you can't physically serve there — but the same customers often have flexibility, so the lever is shifting demand to open {unit}s, not refusing it.",
        conclusion=f"Incentivize spillover from {X} into the open {X} window (off-peak pricing or perk) before considering more {unit}s.",
        expected_effect=f"Redistributing peak-day overflow captures ~${X}/mo without adding capacity.",
        recommend_when={"state": "peak_day_saturated", "min_signal": "booking_calendar"},
        tags=("capacity", "demand_shaping", v.family),
    )


def _offpeak_never_fills(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Your {X} off-peak {unit}s never fill no matter what",
        observation=f"{X} consistently runs at {X}% of capacity across {X} weeks — structurally, not seasonally, under-booked.",
        reasoning=f"Chronically empty off-peak {unit}s won't fill with the same offer that works at peak; they need a different audience (flexible, price-sensitive, or new-trial) recruited specifically into that window.",
        conclusion=f"Create an off-peak-only offer (membership perk, trial, or standing discount) targeted at flexible customers for the {X} window.",
        expected_effect=f"Even a {X}% lift in chronic off-peak utilization is worth ~${X}/mo of dead capacity.",
        recommend_when={"state": "offpeak_structurally_empty", "min_signal": "booking_calendar"},
        tags=("capacity", "off_peak", v.family),
    )


def _package_booking_untapped(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"You sell single {sale}s where multi-session packages would lock in capacity",
        observation=f"{X}% of {v.core_kpis[0]}-relevant customers return for {X}+ {sale}s, yet {X}% book one at a time with no package.",
        reasoning=f"Selling sessions individually leaves future capacity unclaimed and rebooking to chance; a pre-paid package books the calendar forward and raises retention at the same time.",
        conclusion=f"Offer a {X}-session package at a modest bundle discount and prompt it at checkout for proven repeat {v.sale_unit}s.",
        expected_effect=f"Packages pre-book ~${X}/mo of future capacity and lift repeat rate.",
        recommend_when={"state": "package_booking_untapped", "min_signal": "transactions"},
        tags=("capacity", "packages", v.family),
    )


def _recurring_not_set(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"Customers who should be on a standing booking aren't",
        observation=f"{X}% of customers return on a regular {X}-week cadence but {X}% leave each visit without the next {sale} booked.",
        reasoning=f"Predictable repeat demand left un-booked re-competes for the calendar every cycle and risks drifting away; a standing recurring booking captures that demand the moment it's proven.",
        conclusion=f"Prompt a standing recurring {sale} at checkout for anyone with {X}+ visits on a steady cadence.",
        expected_effect=f"Converting proven repeaters to recurring bookings secures ~${X}/mo of forward capacity and cuts churn.",
        recommend_when={"state": "recurring_booking_not_set", "min_signal": "transactions"},
        tags=("capacity", "retention", v.family),
    )


def _lane_capacity(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Drive-thru/lane capacity throttles your {X} peak",
        observation=f"At peak the lane holds {X} cars and overflow balks away — {X} lost {v.sale_unit}s/day when the queue maxes out.",
        reasoning=f"Once the physical lane is full, additional demand simply leaves; the constraint is queue length and per-car service time, so lane flow — not staffing alone — caps peak revenue.",
        conclusion=f"Add a pull-forward/second order point or pre-stage the {X} top sellers to cut per-car time during the {X} surge.",
        expected_effect=f"Recovering balked lane demand is worth ~${X}/mo at peak.",
        recommend_when={"state": "lane_capacity_throttle", "min_signal": "drive_thru_timing"},
        tags=("capacity", "throughput", v.family),
    )


def _buffer_too_generous(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Your between-booking buffers are too generous — {X} {unit}-hours/week lost",
        observation=f"Booking rules pad {X} minutes between every {v.sale_unit}, but actual overrun exceeds the pad only {X}% of the time.",
        reasoning=f"Buffers sized for the worst case waste capacity on every normal booking; right-sizing them to real overrun frequency reclaims sellable {unit} time without causing back-ups.",
        conclusion=f"Cut the standard buffer to {X} minutes and keep the longer pad only for the {X} service types that actually run over.",
        expected_effect=f"Trimming over-generous buffers frees ~${X}/mo of bookable {unit} time.",
        recommend_when={"state": "buffer_too_generous", "min_signal": "booking_calendar"},
        tags=("capacity", "scheduling", v.family),
    )


def _online_selfbooking_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"No online self-booking — you lose after-hours demand to the phone",
        observation=f"{X}% of booking requests arrive outside open hours, but the only path is a phone call, so {X}% never convert.",
        reasoning=f"Demand that can't book itself when it's ready leaks to competitors with online booking; self-serve scheduling captures the after-hours and impulse window your phone line can't.",
        conclusion=f"Enable real-time online self-booking and surface live open {X} slots so off-hours demand converts unattended.",
        expected_effect=f"Capturing after-hours self-bookings is worth ~${X}/mo in {v.sale_unit}s that currently go unanswered.",
        recommend_when={"state": "online_selfbooking_gap", "min_signal": "channel_mix"},
        tags=("capacity", "channel", v.family),
    )


def _peak_slot_yield(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    sale = v.sale_unit
    return Built(
        title=f"Your scarce {X} peak {unit}s are filled with low-value {sale}s",
        observation=f"At your fully-booked {X} peak, {X}% of {unit}s hold {sale}s worth ${X} while higher-value {sale}s (${X}) get pushed to off-peak or turned away.",
        reasoning=f"When peak capacity is the binding constraint, the question isn't whether a {unit} is full but what it's full of — letting low-value {sale}s occupy scarce peak {unit}s caps your yield even at 100% utilization.",
        conclusion=f"Reserve peak {unit}s for high-value {sale}s and steer quick/low-value ones into the open {X} window.",
        expected_effect=f"Yield-managing the peak by value (not just fill) is worth ~${X}/mo at unchanged utilization.",
        recommend_when={"state": "peak_slot_yield_mismatch", "min_signal": "booking_calendar"},
        tags=("capacity", "yield", v.family),
    )


def _group_party_untapped(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Group/party capacity sits unsold on your slow {X}",
        observation=f"Groups account for only {X}% of bookings despite {X} {unit}s that could be combined for parties on under-booked {X}.",
        reasoning=f"A group booking fills multiple {unit}s at once on exactly the days that otherwise run empty, and carries a higher per-head spend — but it never happens if nothing surfaces or holds combined capacity.",
        conclusion=f"Package and promote a group/party option that bundles {X} {unit}s on the slow {X} window, with a deposit to hold it.",
        expected_effect=f"Selling group capacity into dead days is worth ~${X}/mo at premium per-head spend.",
        recommend_when={"state": "group_booking_untapped", "min_signal": "booking_calendar"},
        tags=("capacity", "group", v.family),
    )


def _walk_in_to_booking(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    sale = v.sale_unit
    return Built(
        title=f"Walk-in overflow at peak walks out instead of booking a later {unit}",
        observation=f"On {X} you turn away {X} walk-ins/week at peak, while {X} same-week {unit}s sit open and unbooked.",
        reasoning=f"Walk-in-heavy demand spikes past physical capacity in the moment, but a chunk of those customers would take a later {unit} if offered one — without a capture step they simply leave, losing both the {sale} and the relationship.",
        conclusion=f"At peak turn-away, offer the open {X} slot on the spot (text-the-slot or quick-book) instead of letting walk-ins leave empty-handed.",
        expected_effect=f"Converting even {X}% of turned-away walk-ins into booked {unit}s recovers ~${X}/mo.",
        recommend_when={"state": "walk_in_overflow_uncaptured", "min_signal": "booking_calendar"},
        tags=("capacity", "conversion", v.family),
    )


def _express_priority_tier(v: Vertical, situation: str) -> Built:
    sale = v.sale_unit
    return Built(
        title=f"You give away urgency — no paid express/priority {sale} tier",
        observation=f"{X}% of requests ask to be seen sooner than the calendar allows, yet every booking is priced the same regardless of urgency.",
        reasoning=f"Willingness-to-pay for speed is real and unmonetized; a held priority slot lets urgent customers buy the front of the line without cannibalizing standard bookings — pure margin on existing capacity.",
        conclusion=f"Hold a small daily express block and offer it as a priced priority {sale} for customers who need it now.",
        expected_effect=f"Monetizing urgency on held capacity adds ~${X}/mo at high margin.",
        recommend_when={"state": "express_tier_untapped", "min_signal": "booking_calendar"},
        tags=("capacity", "yield", v.family),
    )


def _advance_booking_decay(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Bookings made far ahead no-show the most — and you don't reconfirm them",
        observation=f"Bookings made {X}+ days out no-show at {X}% versus {X}% for same-week ones, but get no reconfirmation.",
        reasoning=f"Commitment decays with booking age — the further out a {unit} is booked, the likelier it dies empty without a nudge; a timed reconfirm turns the stalest, riskiest bookings back into reliable capacity.",
        conclusion=f"Auto-reconfirm bookings older than {X} days within {X} hours of the appointment and release unconfirmed ones to the waitlist.",
        expected_effect=f"Reconfirming aged bookings recovers ~${X}/mo of {unit}s otherwise lost to long-lead no-shows.",
        recommend_when={"state": "advance_booking_show_decay", "min_signal": "booking_calendar"},
        tags=("capacity", "no_show", v.family),
    )


def _block_standing_booking(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"No block/standing-contract booking locks in your off-peak {unit}s",
        observation=f"Recurring B2B or group demand (corporate, league, contract) is served ad-hoc, leaving {X} off-peak {unit}-hours unclaimed each week.",
        reasoning=f"A standing block contract pre-sells the exact off-peak capacity that otherwise goes empty and converts lumpy ad-hoc demand into guaranteed baseline utilization — a different lever than individual recurring bookings.",
        conclusion=f"Offer a discounted standing block for the {X} off-peak window to recurring group/B2B buyers and reserve it on the calendar.",
        expected_effect=f"Locking a standing block into dead capacity secures ~${X}/mo of guaranteed baseline revenue.",
        recommend_when={"state": "block_standing_booking_untapped", "min_signal": "booking_calendar"},
        tags=("capacity", "off_peak", v.family),
    )


def _seasonal_capacity_prep(v: Vertical, situation: str) -> Built:
    unit = _bookable_unit(v)
    return Built(
        title=f"Your {X} season will exceed bookable {unit}s before you've planned for it",
        observation=f"Demand for {X} climbs {X}% entering the {X} season, but bookable {unit} capacity is held flat at last year's grid.",
        reasoning=f"Seasonal demand that arrives faster than the calendar can absorb it turns into turn-aways at exactly your highest-margin window; capacity has to be opened ahead of the curve, not after.",
        conclusion=f"Extend hours or add temporary {unit} capacity for the {X} peak weeks and open those slots {X} weeks early.",
        expected_effect=f"Pre-opening seasonal capacity captures ~${X}/mo of peak demand that would otherwise be refused.",
        recommend_when={"state": "seasonal_capacity_shortfall", "min_signal": "booking_calendar"},
        tags=("capacity", "seasonal", v.family),
    )


register(
    Archetype(
        key="bookable_calendar_gap", domain="capacity", name="Idle bookable slots",
        build=_calendar_gap, situations=("baseline", "untapped", "declining"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingCalendarAgent: ingest the booking system's slot grid (open vs filled per resource-hour) — POS transactions alone don't expose unsold availability.",
    ),
    Archetype(
        key="inter_appointment_idle", domain="capacity", name="Dead time between bookings",
        build=_inter_appointment_idle, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingGapAgent: compute per-resource gaps between consecutive bookings from the calendar to isolate sub-bookable idle minutes.",
    ),
    Archetype(
        key="double_booking_friction", domain="capacity", name="Double-booking conflicts",
        build=_double_booking_friction, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingConflictAgent: detect overlapping bookings assigned to the same resource and tie each to bumped/delayed transactions.",
    ),
    Archetype(
        key="overbooking_strategy_untapped", domain="capacity", name="No-show buffer untapped",
        build=_overbooking_untapped, situations=("baseline", "leaking"),
        applies_flags=("appointment_based",),
        required_signals=("no_show_log", "booking_calendar"),
        required_agents=("NoShowLedgerAgent", "BookingCalendarAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="NoShowLedgerAgent: derive per-window no-show rates from booking vs attendance records (no-show/attendance not yet ingested — add source) to set a bounded overbook level.",
    ),
    Archetype(
        key="lead_time_too_long", domain="capacity", name="Lead time loses bookings",
        build=_lead_time_too_long, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar", "booking_requests"),
        required_agents=("BookingCalendarAgent", "DemandRequestAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DemandRequestAgent: capture requested-vs-offered booking dates (incl. abandoned requests) to quantify demand lost to lead time — request-side telemetry not yet ingested.",
    ),
    Archetype(
        key="last_minute_cancellation_window", domain="capacity", name="Late cancellations unfillable",
        build=_cancellation_window, situations=("baseline", "leaking"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar", "cancellation_log"),
        required_agents=("BookingCalendarAgent", "CancellationAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CancellationAgent: log cancellation timestamps relative to booking start to size the unfillable late-cancel window (cancellation events not yet ingested).",
    ),
    Archetype(
        key="waitlist_untapped", domain="capacity", name="No waitlist for freed slots",
        build=_waitlist_untapped, situations=("baseline", "untapped"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingCalendarAgent: pair turn-away/peak-saturation signals with same-day freed slots to size unmet waitlist recovery.",
    ),
    Archetype(
        key="slot_granularity_mismatch", domain="capacity", name="Slot size vs service duration",
        build=_slot_granularity, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ServiceDurationAgent: compare booked slot length to actual service duration per service type to find stranded slot remainders.",
    ),
    Archetype(
        key="table_turn_too_slow", domain="capacity", name="Slow table turns at peak",
        build=_table_turn_slow, situations=("baseline", "declining"),
        applies_flags=("table_service",),
        required_signals=("table_timing", "hourly_revenue"),
        required_agents=("TableTurnAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TableTurnAgent: derive per-table seat/clear timestamps (from POS open/close or floor system) to measure peak vs off-peak turn time — table-level timing not yet ingested.",
    ),
    Archetype(
        key="resource_idle_between_uses", domain="capacity", name="Changeover idle on the resource",
        build=_resource_idle_between_uses, situations=("baseline",),
        applies_keys=("salon", "barbershop", "nail_salon", "spa", "med_spa",
                      "auto_repair", "oil_change", "tire_shop", "car_wash",
                      "dental", "physio", "tattoo"),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent", "ResourceTurnAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ResourceTurnAgent: measure per-resource reset/changeover time between consecutive uses (needs service end + next start, plus cleanup events) to separate changeover drag from demand.",
    ),
    Archetype(
        key="class_size_below_fill", domain="capacity", name="Classes below fill",
        build=_class_below_fill, situations=("baseline", "declining"),
        applies_families=("fitness",),
        required_signals=("class_roster",),
        required_agents=("ClassRosterAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ClassRosterAgent: ingest per-class booked-vs-capacity rosters to compute fill rate by time slot (class capacity not in POS transactions).",
    ),
    Archetype(
        key="prep_capacity_vs_demand", domain="capacity", name="Kitchen/prep bottleneck",
        build=_prep_capacity_vs_demand, situations=("baseline",),
        applies_keys=("qsr", "full_restaurant", "ghost_kitchen", "food_truck", "bar", "hotel_fb"),
        required_signals=("ticket_timing", "hourly_revenue"),
        required_agents=("TicketTimingAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TicketTimingAgent: capture kitchen ticket open/fire/complete times to find the prep throughput ceiling vs front-of-house capacity (KDS timing not yet ingested).",
    ),
    Archetype(
        key="reservation_no_deposit_leakage", domain="capacity", name="No-deposit reservation leakage",
        build=_no_deposit_leakage, situations=("baseline", "leaking"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar", "no_show_log"),
        required_agents=("BookingCalendarAgent", "NoShowLedgerAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="NoShowLedgerAgent (shared): join deposit-on-file flag to no-show outcomes to quantify deposit lift — deposit/attendance fields not yet ingested.",
    ),
    Archetype(
        key="peak_day_fully_booked_turnaways", domain="capacity", name="Peak day saturated",
        build=_peak_day_turnaways, situations=("baseline", "seasonal_peak"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingCalendarAgent: flag days at/near 100% booked with declined requests, and contrast with same-week open windows for redistribution.",
    ),
    Archetype(
        key="off_peak_slots_never_fill", domain="capacity", name="Off-peak structurally empty",
        build=_offpeak_never_fills, situations=("baseline", "untapped"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingCalendarAgent: identify windows that stay below a utilization floor across many weeks (structural, not seasonal) to target a distinct off-peak offer.",
    ),
    Archetype(
        key="package_booking_untapped", domain="capacity", name="Multi-session packages untapped",
        build=_package_booking_untapped, situations=("baseline", "untapped"),
        applies_flags=("appointment_based",),
        required_signals=("transactions",),
        required_agents=("RepeatPurchaseAgent",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="recurring_appointment_not_set", domain="capacity", name="Standing booking not set",
        build=_recurring_not_set, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("transactions",),
        required_agents=("RepeatPurchaseAgent", "CadenceAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CadenceAgent: detect customers on a steady return cadence who leave without the next booking, from transaction recency intervals.",
    ),
    Archetype(
        key="drive_thru_lane_capacity", domain="capacity", name="Lane capacity throttle",
        build=_lane_capacity, situations=("baseline", "seasonal_peak"),
        applies_keys=("qsr", "oil_change", "car_wash"),
        required_signals=("drive_thru_timing", "hourly_revenue"),
        required_agents=("LaneFlowAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LaneFlowAgent: capture lane queue depth, per-car service time, and balk events (lane sensor / timer feed not yet ingested) to size throttled peak demand.",
    ),
    Archetype(
        key="buffer_time_too_generous", domain="capacity", name="Over-generous buffers",
        build=_buffer_too_generous, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent", "ServiceDurationAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ServiceDurationAgent (shared): compare configured buffer to actual overrun frequency per service type to right-size padding.",
    ),
    Archetype(
        key="online_self_booking_gap", domain="capacity", name="No online self-booking",
        build=_online_selfbooking_gap, situations=("baseline", "untapped"),
        applies_flags=("appointment_based",),
        required_signals=("channel_mix", "booking_requests"),
        required_agents=("ChannelAgent", "DemandRequestAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DemandRequestAgent (shared): capture after-hours/phone booking attempts and conversion to size demand lost to lack of self-booking.",
    ),
    Archetype(
        key="peak_slot_yield_mismatch", domain="capacity", name="Low-value bookings hold peak slots",
        build=_peak_slot_yield, situations=("baseline", "concentrated"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar", "transactions"),
        required_agents=("BookingCalendarAgent", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="BookingYieldAgent: join booked-slot value to slot scarcity (peak vs open) to flag low-value bookings occupying constrained peak resources.",
    ),
    Archetype(
        key="group_party_booking_untapped", domain="capacity", name="Group/party capacity unsold",
        build=_group_party_untapped, situations=("baseline", "untapped"),
        applies_keys=("full_restaurant", "bar", "hotel_fb", "entertainment", "event_venue",
                      "yoga_studio", "crossfit", "spa"),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingCalendarAgent: detect combinable open capacity on under-booked days and size group/party headroom vs current group share.",
    ),
    Archetype(
        key="walk_in_overflow_to_booking", domain="capacity", name="Walk-in overflow uncaptured",
        build=_walk_in_to_booking, situations=("baseline",),
        applies_flags=("walk_in_heavy",),
        required_signals=("booking_calendar", "vision_traffic"),
        required_agents=("BookingCalendarAgent", "TrafficAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="WalkInCaptureAgent: pair peak walk-in turn-away (queue/vision balk) with same-week open slots to size convertible overflow.",
    ),
    Archetype(
        key="express_priority_tier_untapped", domain="capacity", name="Paid express tier untapped",
        build=_express_priority_tier, situations=("baseline", "untapped"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar", "booking_requests"),
        required_agents=("BookingCalendarAgent", "DemandRequestAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DemandRequestAgent (shared): quantify urgency-driven requests (want-sooner-than-available) to size a priced priority block.",
    ),
    Archetype(
        key="advance_booking_show_decay", domain="capacity", name="Aged bookings no-show more",
        build=_advance_booking_decay, situations=("baseline", "leaking"),
        applies_flags=("appointment_based",),
        required_signals=("booking_calendar", "no_show_log"),
        required_agents=("BookingCalendarAgent", "NoShowLedgerAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="NoShowLedgerAgent (shared): correlate booking lead-age to no-show outcome to target reconfirmation at the riskiest aged bookings.",
    ),
    Archetype(
        key="block_standing_booking_untapped", domain="capacity", name="Standing block booking untapped",
        build=_block_standing_booking, situations=("baseline", "untapped"),
        applies_keys=("event_venue", "yoga_studio", "crossfit", "gym", "full_restaurant",
                      "bar", "hotel_fb", "entertainment", "car_wash", "cleaning"),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="BookingCalendarAgent: identify recurring off-peak open capacity suitable for a standing block contract and size ad-hoc group demand against it.",
    ),
    Archetype(
        key="seasonal_capacity_shortfall", domain="capacity", name="Seasonal capacity shortfall",
        build=_seasonal_capacity_prep, situations=("seasonal_peak", "emerging"),
        applies_flags=("appointment_based", "seasonal"),
        required_signals=("booking_calendar",),
        required_agents=("BookingCalendarAgent", "SeasonalForecastAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="SeasonalForecastAgent: project seasonal demand against the held-flat slot grid to flag capacity shortfalls ahead of the curve.",
    ),
)
