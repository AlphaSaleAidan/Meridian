"""summarize_ledger: the pure P&L core behind the per-location voice wallet."""
from src.services.voice_ledger import summarize_ledger


def _row(kind, cents, at):
    return {"kind": kind, "amount_cents": cents, "created_at": at}


def test_balance_all_time_minus_debits():
    rows = [
        _row("credit", 5000, "2026-07-01T00:00:00+00:00"),
        _row("debit", 1200, "2026-07-02T00:00:00+00:00"),
        _row("credit", 800, "2026-06-01T00:00:00+00:00"),  # older than window
        _row("debit", 300, "2026-06-01T00:00:00+00:00"),
    ]
    out = summarize_ledger(rows, window_days=30, cutoff_iso="2026-06-20T00:00:00+00:00")
    assert out["balance_cents"] == 5000 - 1200 + 800 - 300  # all-time = 4300
    assert out["self_funded"] is True
    # window only counts rows >= cutoff (the July ones)
    assert out["window_credit_cents"] == 5000
    assert out["window_debit_cents"] == 1200
    assert out["window_net_cents"] == 3800


def test_underwater_not_self_funded_no_runway():
    rows = [_row("credit", 100, "2026-07-01T00:00:00+00:00"),
            _row("debit", 900, "2026-07-02T00:00:00+00:00")]
    out = summarize_ledger(rows, window_days=30, cutoff_iso="2026-06-20T00:00:00+00:00")
    assert out["balance_cents"] == -800
    assert out["self_funded"] is False
    assert out["runway_days"] is None  # underwater ⇒ no finite runway


def test_runway_when_funded_and_burning():
    # balance +3000, window debit 900 over 30d ⇒ 30¢/day ⇒ 100 days runway
    rows = [_row("credit", 3900, "2026-07-01T00:00:00+00:00"),
            _row("debit", 900, "2026-07-10T00:00:00+00:00")]
    out = summarize_ledger(rows, window_days=30, cutoff_iso="2026-06-20T00:00:00+00:00")
    assert out["balance_cents"] == 3000
    assert out["avg_daily_debit_cents"] == 30.0
    assert out["runway_days"] == 100.0


def test_zero_burn_has_no_runway():
    rows = [_row("credit", 5000, "2026-07-01T00:00:00+00:00")]
    out = summarize_ledger(rows, window_days=30, cutoff_iso="2026-06-20T00:00:00+00:00")
    assert out["runway_days"] is None
    assert out["self_funded"] is True


def test_empty_ledger():
    out = summarize_ledger([], window_days=30, cutoff_iso="2026-06-20T00:00:00+00:00")
    assert out["balance_cents"] == 0 and out["self_funded"] is True and out["runway_days"] is None
