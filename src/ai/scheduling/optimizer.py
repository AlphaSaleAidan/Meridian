"""
Schedule Optimizer — Generates optimal staff schedules.

Uses peak_hours + staffing agent data to build shift assignments
that minimize labor cost while maintaining coverage.

Constraint-based approach:
  - Cover all open hours with minimum staff
  - Respect max hours per employee (40h/week)
  - Prefer longer shifts (4-8h) over short ones
  - Weight staffing toward peak hours
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("meridian.scheduling")


@dataclass
class ShiftSlot:
    day_of_week: int  # 0=Mon
    start_hour: int
    end_hour: int
    required_staff: int
    is_peak: bool = False


@dataclass
class ScheduleResult:
    shifts: list[dict]
    total_labor_hours: float
    peak_coverage_pct: float
    estimated_cost_cents: int
    warnings: list[str] = field(default_factory=list)


def build_demand_profile(
    peak_hours_data: dict,
    staffing_data: dict,
) -> list[ShiftSlot]:
    """Convert agent outputs into hourly demand slots."""
    hourly_staffing = staffing_data.get("data", {}).get("hourly_staffing", [])
    hourly_profile = peak_hours_data.get("data", {}).get("hourly_profile", [])

    peak_hours_set = set()
    top_windows = peak_hours_data.get("data", {}).get("top_5_windows", [])
    for w in top_windows:
        peak_hours_set.add(w.get("hour", 0))

    slots = []
    for hour_rec in hourly_staffing:
        hour = hour_rec.get("hour", 0)
        ideal = hour_rec.get("ideal_staff", 1)
        avg_rev = hour_rec.get("avg_revenue_cents", 0)

        if avg_rev == 0 and ideal <= 1:
            continue

        for dow in range(7):
            slots.append(ShiftSlot(
                day_of_week=dow,
                start_hour=hour,
                end_hour=hour + 1,
                required_staff=ideal,
                is_peak=hour in peak_hours_set,
            ))

    return slots


def optimize_schedule(
    peak_hours_data: dict,
    staffing_data: dict,
    num_employees: int = 8,
    max_hours_per_week: int = 40,
    min_shift_hours: int = 4,
    max_shift_hours: int = 8,
    hourly_rate_cents: int = 1500,
) -> ScheduleResult:
    """Generate an optimized staff schedule.

    Greedy approach: assign shifts starting from peak hours,
    then fill remaining coverage needs.
    """
    demand = build_demand_profile(peak_hours_data, staffing_data)
    if not demand:
        return ScheduleResult(
            shifts=[],
            total_labor_hours=0,
            peak_coverage_pct=0,
            estimated_cost_cents=0,
            warnings=["No demand data available — connect POS for hourly data"],
        )

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    demand_sorted = sorted(demand, key=lambda s: (not s.is_peak, -s.required_staff))

    employee_hours: dict[int, float] = {i: 0 for i in range(num_employees)}
    shifts: list[dict] = []
    peak_slots_total = sum(1 for s in demand if s.is_peak)
    peak_slots_covered = 0

    for slot in demand_sorted:
        for staff_needed in range(slot.required_staff):
            available = [
                emp for emp, hours in employee_hours.items()
                if hours + 1 <= max_hours_per_week
            ]
            if not available:
                continue

            emp = min(available, key=lambda e: employee_hours[e])
            employee_hours[emp] += 1

            shifts.append({
                "employee_id": emp,
                "day": day_names[slot.day_of_week],
                "day_of_week": slot.day_of_week,
                "start_hour": slot.start_hour,
                "end_hour": slot.end_hour,
                "is_peak": slot.is_peak,
            })

            if slot.is_peak:
                peak_slots_covered += 1

    total_hours = sum(employee_hours.values())
    peak_pct = (peak_slots_covered / max(peak_slots_total, 1)) * 100
    cost = int(total_hours * hourly_rate_cents)

    warnings = []
    overworked = [e for e, h in employee_hours.items() if h > max_hours_per_week]
    if overworked:
        warnings.append(f"{len(overworked)} employees exceed {max_hours_per_week}h/week limit")

    if peak_pct < 80:
        warnings.append(f"Only {peak_pct:.0f}% of peak hours covered — consider hiring")

    merged = _merge_consecutive_shifts(shifts)

    return ScheduleResult(
        shifts=merged,
        total_labor_hours=total_hours,
        peak_coverage_pct=round(peak_pct, 1),
        estimated_cost_cents=cost,
        warnings=warnings,
    )


def _merge_consecutive_shifts(shifts: list[dict]) -> list[dict]:
    """Merge consecutive 1-hour slots into longer shifts per employee per day."""
    from collections import defaultdict

    by_emp_day: dict[tuple, list[dict]] = defaultdict(list)
    for s in shifts:
        key = (s["employee_id"], s["day_of_week"])
        by_emp_day[key].append(s)

    merged = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for (emp, dow), slots in by_emp_day.items():
        slots_sorted = sorted(slots, key=lambda s: s["start_hour"])
        if not slots_sorted:
            continue

        current = {**slots_sorted[0]}
        for s in slots_sorted[1:]:
            if s["start_hour"] == current["end_hour"]:
                current["end_hour"] = s["end_hour"]
                if s["is_peak"]:
                    current["is_peak"] = True
            else:
                merged.append(current)
                current = {**s}
        merged.append(current)

    return sorted(merged, key=lambda s: (s["day_of_week"], s["start_hour"], s["employee_id"]))
