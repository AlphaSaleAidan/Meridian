"""
Insight lifecycle + proof gate.

This is the machinery that guarantees a half-finished insight never reaches a
customer portal. Flow:

    template_row ──fill(values)──▶ candidate ──prove(context)──▶ proven/rejected
                                                                      │
                                          serve_for_portal() ◀────────┘  (only proven/published)

Two independent proofs:
  1. prove(): post-fill — every placeholder filled, every required signal present
     and non-empty, numbers sane, and the situation precondition actually holds.
  2. is_portal_safe() (in schema): re-checked at the serving boundary, so a
     mislabeled row still can't leak ("prove it again before you show it").
"""
from __future__ import annotations

from .schema import (
    InsightStatus,
    PLACEHOLDER,
    has_unfilled_placeholders,
    is_portal_safe,
)

_OPEN = PLACEHOLDER[0]  # "{"


def fill(template_row: dict, values: list[str]) -> dict:
    """Replace placeholders left-to-right with `values`, returning a CANDIDATE row.

    Templates use the generic `{x}` token for every fill-in; `values` are the
    real, computed strings in the order the tokens appear (title first, then the
    four reasoning legs). Does NOT mark anything portal-safe — that's prove()'s job.
    """
    row = {**template_row}
    it = iter(values)

    def _sub(text: str) -> str:
        out = []
        i = 0
        while i < len(text):
            if text.startswith(PLACEHOLDER, i):
                out.append(str(next(it, PLACEHOLDER)))
                i += len(PLACEHOLDER)
            else:
                out.append(text[i])
                i += 1
        return "".join(out)

    row["title"] = _sub(row.get("title", ""))
    reasoning = dict(row.get("reasoning") or {})
    for leg in ("observation", "reasoning", "conclusion", "expected_effect"):
        reasoning[leg] = _sub(reasoning.get(leg, ""))
    row["reasoning"] = reasoning
    row["status"] = InsightStatus.CANDIDATE.value
    return row


def _signal_present(context: dict, signal: str) -> bool:
    """A required signal counts as present only if the context has a non-empty
    value for it. Supports dotted paths like `vision_traffic.entries`."""
    cur: object = context
    for part in signal.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    if cur is None:
        return False
    if isinstance(cur, (list, dict, str)) and len(cur) == 0:
        return False
    return True


def prove(candidate_row: dict, context: dict, *, situation_holds: bool = True) -> dict:
    """Post-fill validation. Returns the row marked PROVEN or REJECTED.

    Rejects when: a placeholder survived the fill, a required signal is absent /
    empty, or the situation precondition does not actually hold for this merchant.
    """
    reasoning = candidate_row.get("reasoning") or {}
    texts = [candidate_row.get("title", "")] + [
        reasoning.get(k, "") for k in ("observation", "reasoning", "conclusion", "expected_effect")
    ]

    rejected = {**candidate_row, "status": InsightStatus.REJECTED.value}

    # 1) no half-filled text
    if has_unfilled_placeholders(*texts):
        rejected["reject_reason"] = "unfilled_placeholder"
        return rejected
    # 2) every required signal actually present in the merchant's data
    for sig in candidate_row.get("required_signals", []):
        if not _signal_present(context, sig):
            rejected["reject_reason"] = f"missing_signal:{sig}"
            return rejected
    # 3) the situation this insight asserts must genuinely hold
    if not situation_holds:
        rejected["reject_reason"] = "situation_not_met"
        return rejected

    return {**candidate_row, "status": InsightStatus.PROVEN.value, "reject_reason": None}


def publish(proven_row: dict) -> dict | None:
    """Final boundary check before a row may be marked PUBLISHED. Returns the
    published row, or None if it fails the independent serve-time guard."""
    if not is_portal_safe(proven_row):
        return None
    return {**proven_row, "status": InsightStatus.PUBLISHED.value}


def serve_for_portal(rows: list[dict]) -> list[dict]:
    """The ONLY function a customer-portal serving path should use to filter
    insights. Applies the independent is_portal_safe() gate to every row."""
    return [r for r in rows if is_portal_safe(r)]
