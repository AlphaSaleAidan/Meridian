"""_rollup_team_commissions: per-rep commission rollup for the Manager view."""
from src.api.routes.canada import _rollup_team_commissions


def test_rollup_buckets_and_totals():
    ms = [
        {"rep_id": "a", "amount_cents": 1000, "status": "earned"},
        {"rep_id": "a", "amount_cents": 2000, "status": "pending"},
        {"rep_id": "a", "amount_cents": 500,  "status": "paid"},
        {"rep_id": "b", "amount_cents": 9000, "status": "earned"},
        {"rep_id": "a", "amount_cents": 7777, "status": "halted"},   # excluded
        {"rep_id": "a", "amount_cents": 4,    "status": "weird"},    # excluded
        {"rep_id": None, "amount_cents": 1,   "status": "earned"},   # no rep -> skip
    ]
    out = _rollup_team_commissions(ms)
    by = {r["rep_id"]: r for r in out["rows"]}
    assert by["a"] == {"rep_id": "a", "earned_cents": 1000, "pending_cents": 2000, "paid_cents": 500}
    assert by["b"] == {"rep_id": "b", "earned_cents": 9000, "pending_cents": 0, "paid_cents": 0}
    assert out["totals"] == {"earned_cents": 10000, "pending_cents": 2000, "paid_cents": 500}
    # sorted by total desc: b(9000) before a(3500)
    assert [r["rep_id"] for r in out["rows"]] == ["b", "a"]


def test_rollup_empty():
    assert _rollup_team_commissions([]) == {
        "rows": [], "totals": {"earned_cents": 0, "pending_cents": 0, "paid_cents": 0}}
