"""
Domain: LABOR / STAFFING.

Each archetype is a distinct reasoning pattern about matching people to demand.
Specialization per vertical changes the lever (queue walkouts for walk-in-heavy;
chair/bay/room utilization for appointment-based; route density for dispatch),
so a cafe insight and a salon insight are genuinely different, not relabeled.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


def _peak_coverage(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    if "walk_in_heavy" in v.flags or "table_service" in v.flags:
        lever = f"add one {role} to the {X}–{X} block"
        loss = f"abandoned-queue {unit}s (entries exceed {unit}s by {X}% at peak)"
    elif "appointment_based" in v.flags:
        lever = f"open one more {role} slot / extend {role} hours at {X}"
        loss = f"turned-away {unit} demand when {v.core_kpis[0]} hits {X}%"
    else:
        lever = f"shift one {role} into the {X} window"
        loss = f"unserved demand worth ~${X}/wk"
    extra = {
        "emerging": " A newly-forming rush at {x} is the cause — staff it before it sets the pattern.".replace("{x}", X),
        "declining": " Coverage that used to match this peak has slipped as volume grew.",
    }.get(situation, "")
    return Built(
        title=f"Your {X} peak is understaffed — {X} {role}s carry {X}% of the day",
        observation=f"{X}% of daily {unit}s land between {X} and {X}, but only {X} {role}(s) are scheduled then.",
        reasoning=f"Throughput per {role} exceeds {X}/hr in that window, which historically drives {loss}.{extra}",
        conclusion=f"To capture it, {lever}; keep the rest of the schedule as-is.",
        expected_effect=f"Recovering the peak gap is worth ~${X}/mo in otherwise-lost {unit}s.",
        recommend_when={"state": "high_peak_concentration", "min_signal": "hourly_revenue"},
        tags=("staffing", "peak", v.family),
    )


def _idle_trough(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Overstaffed during your {X} lull — {X} idle {role}-hours/week",
        observation=f"Between {X} and {X}, {X} {role}s are scheduled but only ${X} of revenue flows — {X}% of labor for {X}% of sales.",
        reasoning=f"That window runs a labor cost ratio of {X}%, well above your {X}% target; the {role}s are paid faster than demand arrives.",
        conclusion=f"Trim to {X} {role}(s) in that block or shift the hours toward your {X} peak.",
        expected_effect=f"Re-timing those hours saves ~${X}/mo without touching peak service.",
        recommend_when={"state": "low_demand_overstaffed", "min_signal": "hourly_revenue"},
        tags=("staffing", "labor_cost", v.family),
    )


def _hours_demand_mismatch(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your open/close hours don't match when customers actually come",
        observation=f"The first {X} and last {X} open hours produce only {X}% of daily {v.sale_unit}s, while demand spikes at {X}.",
        reasoning=f"You pay fixed open/close labor + utilities for {X} low-yield hours daily; meanwhile {X} shows unmet demand outside current hours.",
        conclusion=f"Shift opening {X} later and extend toward {X}, or test the high-demand window for {X} weeks.",
        expected_effect=f"Aligning hours to demand nets ~${X}/mo (saved dead hours + captured peak).",
        recommend_when={"state": "hours_demand_mismatch", "min_signal": "hourly_revenue"},
        tags=("staffing", "hours", v.family),
    )


def _solo_shift_risk(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Single-{role} shifts during meaningful volume",
        observation=f"On {X} shifts a lone {role} handles {X}+ {v.sale_unit}s/hr with no backup.",
        reasoning=f"Solo coverage at that volume lengthens wait, blocks breaks, and leaves no cover for a no-show — a service and continuity risk, not just a cost one.",
        conclusion=f"Add a floating {role} across the {X} overlapping busy shifts, or stagger starts so coverage never drops to one during {X}.",
        expected_effect=f"Eliminates {X} weekly single-coverage hours and the walkout/risk they carry.",
        recommend_when={"state": "solo_coverage_at_volume", "min_signal": "schedule_shifts"},
        tags=("staffing", "risk", v.family),
    )


def _overtime_concentration(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Overtime is piling onto {X} {role}s",
        observation=f"{X}% of overtime hours fall on just {X} {role}(s); {X} others sit under {X} hours.",
        reasoning=f"Concentrated OT costs a {X}% premium AND raises burnout/turnover risk on the very {role}s you most rely on, while trained capacity goes unused.",
        conclusion=f"Redistribute {X} OT hours to under-scheduled {role}s before approving more premium hours.",
        expected_effect=f"Rebalancing trims ~${X}/mo in OT premium and de-risks your key {role}s.",
        recommend_when={"state": "overtime_concentrated", "min_signal": "schedule_shifts"},
        tags=("staffing", "labor_cost", "retention", v.family),
    )


def _staff_revenue_link(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Your highest-revenue {role} works your lowest-traffic shifts",
        observation=f"{role} {X} converts at ${X}/{v.sale_unit} — {X}% above peers — but is scheduled mostly during {X}.",
        reasoning=f"Top performers parked in slow windows waste their conversion edge, because their above-average close rate lands on near-empty traffic instead of your busiest hours; moving your best {role} onto the {X} peak applies that lift where the {v.sale_unit} volume actually is, which compounds into materially higher per-{v.sale_unit} value.",
        conclusion=f"Schedule {role} {X} onto the {X} peak for {X} weeks and measure ticket lift vs control shifts.",
        expected_effect=f"Aligning your best {role} to peak traffic is worth ~${X}/mo in incremental {v.sale_unit} value.",
        recommend_when={"state": "talent_demand_misalignment", "min_signal": "transactions"},
        tags=("staffing", "performance", v.family),
    )


def _shift_changeover_gap(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"Coverage dips at shift change — a recurring hole mid-day",
        observation=f"Around the {X} changeover, effective {role} coverage drops to {X} for {X} minutes while {X}% of that hour's {unit}s still arrive.",
        reasoning=f"A handoff gap quietly costs sales because demand doesn't pause while one {role} leaves before the next is productive, so service slows exactly when the floor is thinnest — a scheduling-overlap problem distinct from being understaffed at peak, since the headcount looks fine on paper.",
        conclusion=f"Stagger the {role} shift starts so the outgoing and incoming overlap through the {X} changeover, rather than scheduling a clean swap that leaves the floor short.",
        expected_effect=f"Closing the changeover gap recovers ~${X}/mo of {unit}s lost to the mid-shift hole.",
        recommend_when={"state": "shift_changeover_gap", "min_signal": "schedule_shifts"},
        tags=("staffing", "scheduling", "coverage", v.family),
    )


def _cross_training_gap(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"One skill rides on a single {role} — a coverage single-point-of-failure",
        observation=f"{X}% of {unit}s depend on a task only {X} {role}(s) can do; when they're off, that demand stalls or walks.",
        reasoning=f"A skill concentrated in one or two people is a scheduling trap, because a single absence collapses capacity for that {unit}, so you either over-rely on one {role} (burnout, OT premium) or turn demand away — a flexibility gap that pure headcount can't fix.",
        conclusion=f"Cross-train {X} additional {role}s on the bottleneck skill so coverage flexes, and build a trained backup into every shift instead of relying on one person.",
        expected_effect=f"Cross-training out the single-point-of-failure protects ~${X}/mo of otherwise-stalled {unit}s.",
        recommend_when={"state": "cross_training_gap", "min_signal": "schedule_shifts"},
        tags=("staffing", "cross_training", "risk", v.family),
    )


register(
    Archetype(
        key="peak_coverage_gap", domain="labor", name="Understaffed peak",
        build=_peak_coverage, situations=("baseline", "emerging", "declining", "seasonal_peak"),
        required_signals=("hourly_revenue", "schedule_shifts"),
        required_agents=("PatternAnalyzer", "StaffingAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StaffPeakFusionAgent: join schedule_shifts to hourly_revenue (+vision_traffic.entries where present) to compute per-hour coverage vs demand and walkout gap.",
    ),
    Archetype(
        key="idle_labor_trough", domain="labor", name="Overstaffed lull",
        build=_idle_trough, situations=("baseline", "seasonal_trough"),
        required_signals=("hourly_revenue", "schedule_shifts"),
        required_agents=("PatternAnalyzer", "StaffingAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StaffPeakFusionAgent (shared): also flags hours where scheduled labor cost ratio exceeds target.",
    ),
    Archetype(
        key="hours_demand_mismatch", domain="labor", name="Hours vs demand mismatch",
        build=_hours_demand_mismatch, situations=("baseline",),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="solo_shift_risk", domain="labor", name="Solo coverage at volume",
        build=_solo_shift_risk, situations=("baseline",),
        required_signals=("schedule_shifts", "hourly_revenue"),
        required_agents=("StaffingAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StaffPeakFusionAgent (shared): detect hours where headcount==1 while volume exceeds a per-role throughput threshold.",
    ),
    Archetype(
        key="overtime_concentration", domain="labor", name="Concentrated overtime",
        build=_overtime_concentration, situations=("baseline",),
        required_signals=("schedule_shifts",),
        required_agents=("StaffingAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="OvertimeLedgerAgent: derive per-worker weekly hours + OT premium from schedule_shifts/timeclock (timeclock not yet ingested — add source).",
    ),
    Archetype(
        key="staff_revenue_link", domain="labor", name="Top performer on slow shifts",
        build=_staff_revenue_link, situations=("baseline",),
        required_signals=("transactions", "schedule_shifts"),
        required_agents=("StaffingAgent", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="StaffAttributionAgent: attribute transaction value to the worker on shift (needs employee_id on transactions or shift-overlap join) to rank per-staff conversion.",
    ),
    Archetype(
        key="shift_changeover_gap", domain="labor", name="Shift-changeover coverage gap",
        build=_shift_changeover_gap, situations=("baseline",),
        required_signals=("schedule_shifts", "hourly_revenue"),
        required_agents=("StaffingAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="StaffPeakFusionAgent (shared): detect minutes where overlapping shift starts/ends drop effective coverage below demand at the changeover boundary.",
    ),
    Archetype(
        key="cross_training_gap", domain="labor", name="Skill single-point-of-failure",
        build=_cross_training_gap, situations=("baseline",),
        required_signals=("schedule_shifts", "transactions"),
        required_agents=("StaffingAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="SkillCoverageAgent: map per-worker skills/role to the tasks each {unit} needs, then flag tasks whose coverage rides on one or two workers (skill matrix is not ingested today).",
    ),
)
