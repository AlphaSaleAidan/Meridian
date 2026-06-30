"""
Situation-based recommender.

Given what we find at a specific business — its vertical, which data signals are
actually flowing, and which business STATES we've detected — this selects the
prebuilt insight templates worth pursuing, split into:

  * ready    — every required signal is available now; can be filled + proven.
  * blocked  — relevant, but a required signal needs a swarm upgrade first
               (these drive the swarm roadmap, and we can tell the owner
               "connect X and we'll light up these insights").

This is the layer that turns 10k generic roadmaps into "the right ~N for THIS
owner." It never returns customer-facing text — recommendations are still
templates (placeholders intact); the prover fills + proves before anything shows.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .verticals import VERTICALS_BY_KEY


@dataclass
class Situation:
    vertical: str
    available_signals: set[str] = field(default_factory=set)   # signal names flowing for this merchant
    detected_states: set[str] = field(default_factory=set)     # e.g. {"high_peak_concentration","churn_rising"}
    family: str | None = None

    def resolve_family(self) -> str | None:
        if self.family:
            return self.family
        v = VERTICALS_BY_KEY.get(self.vertical)
        return v.family if v else None


def _signal_available(required: list[str], available: set[str]) -> bool:
    """A template is fillable when every required signal is present. Dotted paths
    (vision_traffic.entries) match if the root or full path is available."""
    for sig in required:
        root = sig.split(".")[0]
        if sig not in available and root not in available:
            return False
    return True


def _vertical_matches(row: dict, sit: Situation) -> bool:
    rw = row.get("recommend_when") or {}
    if rw.get("vertical") and rw["vertical"] == sit.vertical:
        return True
    # rows are vertical-instantiated already (row['vertical']); match on that
    return row.get("vertical") == sit.vertical


def _state_matches(row: dict, sit: Situation) -> bool:
    """If the caller supplied detected_states, prefer templates whose situation /
    recommend_when.state is among them. If no states given, don't filter on state."""
    if not sit.detected_states:
        return True
    rw = row.get("recommend_when") or {}
    state = rw.get("state")
    return (row.get("situation") in sit.detected_states) or (state in sit.detected_states)


def recommend(catalog: list[dict], sit: Situation, *, limit: int | None = None) -> dict:
    """Return {'ready': [...], 'blocked': [...]} template rows for this situation."""
    ready, blocked = [], []
    for row in catalog:
        if not _vertical_matches(row, sit):
            continue
        if not _state_matches(row, sit):
            continue
        if _signal_available(row.get("required_signals", []), sit.available_signals):
            ready.append(row)
        else:
            blocked.append(row)

    # Rank: ready by capability (full first), blocked by how few extra signals needed.
    cap_order = {"full": 0, "partial": 1, "missing": 2}
    ready.sort(key=lambda r: cap_order.get(r.get("swarm_capability"), 3))
    blocked.sort(key=lambda r: sum(
        1 for s in r.get("required_signals", [])
        if s.split(".")[0] not in sit.available_signals and s not in sit.available_signals
    ))
    if limit:
        ready, blocked = ready[:limit], blocked[:limit]
    return {
        "vertical": sit.vertical,
        "ready": ready,
        "blocked": blocked,
        "ready_count": len(ready),
        "blocked_count": len(blocked),
    }
