"""last_sync_at (ISO string from PostgREST) must reach sync engines as datetime.

Regression: run_incremental passed the raw string into the Clover engine, which
types ``since`` as datetime and calls ``since.isoformat()`` — AttributeError on
every incremental Clover sync (live worker logs 2026-07-21:
"Sync failed <id>/clover: 'str' object has no attribute 'isoformat'").
"""
from datetime import datetime, timezone

from src.services.pos_sync_runner import _parse_since


def test_parse_iso_string_with_offset():
    dt = _parse_since("2026-07-21T19:04:55.108+00:00")
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None
    assert dt.year == 2026 and dt.minute == 4


def test_parse_iso_string_with_z_suffix():
    dt = _parse_since("2026-07-21T19:04:55Z")
    assert isinstance(dt, datetime)
    assert dt.utcoffset().total_seconds() == 0


def test_naive_string_gets_utc():
    dt = _parse_since("2026-07-21T19:04:55")
    assert dt.tzinfo is timezone.utc


def test_none_passthrough():
    assert _parse_since(None) is None


def test_datetime_passthrough():
    now = datetime.now(timezone.utc)
    assert _parse_since(now) is now


def test_garbage_returns_none():
    assert _parse_since("not-a-date") is None
