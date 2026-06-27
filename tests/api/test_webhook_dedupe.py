"""
Webhook idempotency — persistent, cross-worker Square event dedupe.

Proves the dedupe mechanism (migration 032 `webhook_events` + the
`record_webhook_event` callback) from several angles, with the DB faked:

  1. First delivery of an event_id processes; a redelivery is skipped — and the
     skip is driven by the DB (an INSERT that conflicts the second time), not by
     the in-process cache. Proven by using a FRESH processor for the duplicate
     so its in-memory set is empty.
  2. The route-level `_record_webhook_event` helper maps the REST client's
     return correctly: non-empty rows → first time (True), empty list (409
     conflict, swallowed by the client) → duplicate (False), no DB → None.
  3. With no DB-backed callback wired, dedupe degrades to in-process only
     (legacy behaviour) and still catches same-worker repeats.
  4. A DB failure (callback returns None / raises) fails OPEN: the event is
     processed rather than crashing the webhook.

Pattern mirrors tests/api/test_pos_connect_flow.py: call functions directly
with a fake DB, run via asyncio.run (no pytest-asyncio).

Run:  python -m pytest tests/api/test_webhook_dedupe.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import src.db as db_mod  # noqa: E402
from src.square.webhook_handlers import WebhookProcessor  # noqa: E402
from src.api.routes import webhooks as wh  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class FakeDedupeDB:
    """Fakes the REST client's insert() against a unique-keyed table.

    First insert of an event_id returns the row (PostgREST return=representation);
    a second insert of the same id is a 409 conflict, which the real REST client
    swallows and returns as an empty list. Mirrors that contract.
    """
    def __init__(self):
        self._seen: set[str] = set()
        self.insert_calls: list[tuple[str, dict]] = []

    async def insert(self, table, row, return_data=True):
        self.insert_calls.append((table, row))
        key = row["event_id"]
        if key in self._seen:
            return []          # 409 conflict swallowed → empty
        self._seen.add(key)
        return [row] if return_data else []


class RaisingDB:
    """insert() blows up — simulates a DB outage mid-request."""
    async def insert(self, table, row, return_data=True):
        raise RuntimeError("connection reset")


# ── 1. End-to-end via the route helper + processor: first processes, dup skipped

def test_first_processes_duplicate_skipped_via_db():
    db_mod._db_instance = FakeDedupeDB()
    try:
        # First delivery — fresh worker, empty in-memory cache.
        p1 = WebhookProcessor(record_webhook_event=wh._record_webhook_event)
        first = _run(p1.is_duplicate("evt_abc", provider="square"))
        assert first is False, "first delivery must NOT be flagged duplicate"

        # Redelivery to a *different* worker (fresh processor → empty cache),
        # so the skip can ONLY come from the shared DB row.
        p2 = WebhookProcessor(record_webhook_event=wh._record_webhook_event)
        dup = _run(p2.is_duplicate("evt_abc", provider="square"))
        assert dup is True, "redelivery to another worker must be flagged duplicate"

        # Both workers attempted the DB insert (cross-worker source of truth).
        assert db_mod._db_instance.insert_calls == [
            ("webhook_events", {"event_id": "evt_abc", "provider": "square"}),
            ("webhook_events", {"event_id": "evt_abc", "provider": "square"}),
        ]
    finally:
        db_mod._db_instance = None


def test_same_worker_repeat_uses_cache_no_extra_db_hit():
    """A repeat within the SAME worker is caught by the fast-path cache and does
    not hit the DB a second time."""
    db_mod._db_instance = FakeDedupeDB()
    try:
        p = WebhookProcessor(record_webhook_event=wh._record_webhook_event)
        assert _run(p.is_duplicate("evt_same", provider="square")) is False
        assert _run(p.is_duplicate("evt_same", provider="square")) is True
        # Only ONE DB insert — the second was short-circuited in memory.
        assert len(db_mod._db_instance.insert_calls) == 1
    finally:
        db_mod._db_instance = None


# ── 2. Route helper return mapping ───────────────────────────────────────────

def test_record_webhook_event_return_mapping():
    db_mod._db_instance = FakeDedupeDB()
    try:
        # First → True (newly inserted)
        assert _run(wh._record_webhook_event("e1", "square")) is True
        # Duplicate → False (empty list from swallowed 409)
        assert _run(wh._record_webhook_event("e1", "square")) is False
    finally:
        db_mod._db_instance = None

    # No DB → None (caller falls back to in-process dedupe)
    db_mod._db_instance = None
    assert _run(wh._record_webhook_event("e2", "square")) is None

    # DB raises → None (fail-open, don't crash the webhook)
    db_mod._db_instance = RaisingDB()
    try:
        assert _run(wh._record_webhook_event("e3", "square")) is None
    finally:
        db_mod._db_instance = None


# ── 3. No DB-backed callback → in-process-only fallback (legacy behaviour) ────

def test_in_process_fallback_without_callback():
    p = WebhookProcessor()  # no record_webhook_event wired
    assert _run(p.is_duplicate("evt_x")) is False   # first sighting
    assert _run(p.is_duplicate("evt_x")) is True    # same worker repeat
    # A different worker (fresh processor) has its own empty cache → can't dedupe
    # without the DB. This is exactly why the DB-backed path exists.
    p2 = WebhookProcessor()
    assert _run(p2.is_duplicate("evt_x")) is False


# ── 4. DB failure fails OPEN (process rather than crash) ─────────────────────

def test_db_failure_fails_open():
    async def _boom(event_id, provider):
        raise RuntimeError("db down")

    p = WebhookProcessor(record_webhook_event=_boom)
    # Must not raise; event is treated as first-time (processed).
    assert _run(p.is_duplicate("evt_boom")) is False


def test_empty_event_id_not_duplicate():
    p = WebhookProcessor(record_webhook_event=wh._record_webhook_event)
    assert _run(p.is_duplicate("")) is False


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
