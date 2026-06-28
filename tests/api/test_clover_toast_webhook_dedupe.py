"""
Clover + Toast webhook idempotency — persistent, cross-worker dedupe.

Mirrors the Square dedupe (migration 032 `webhook_events` + the
`record_webhook_event` callback) for the two POS providers that lacked it.
Neither Clover nor Toast carries a single global event id like Square, so:

  * Clover keys each object-change on `clover:{merchantId}:{objectId}:{ts}`.
  * Toast keys on `toast:{webhookId}`.

Both reuse the EXISTING `webhook_events` table (provider='clover'/'toast') via
the shared module `processor` — no new migration.

Proven from several angles, DB faked:

  1. Clover: first delivery of an object-event processes; a redelivery to a
     DIFFERENT worker (fresh in-memory cache) is dropped — the skip is driven by
     the shared DB row, not the local cache. The recorded key matches the scheme.
  2. Clover: a batch with one already-seen + one new event yields only the fresh
     one (process only the fresh).
  3. Clover: a DB outage fails OPEN — the event is processed, not dropped.
  4. Toast: first delivery (valid HMAC) is accepted + scheduled for processing;
     a redelivery to a different worker is acked 200 but NOT scheduled. Recorded
     key matches `toast:{webhookId}`.
  5. Toast: a DB outage fails OPEN — first delivery still scheduled.

Pattern mirrors tests/api/test_webhook_dedupe.py: swap the module `processor`
to simulate separate uvicorn workers sharing one DB, run via asyncio.run.

Run:  python -m pytest tests/api/test_clover_toast_webhook_dedupe.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from starlette.requests import Request  # noqa: E402
from fastapi import BackgroundTasks  # noqa: E402

import src.db as db_mod  # noqa: E402
from src.square.webhook_handlers import WebhookProcessor  # noqa: E402
from src.toast.webhook_verify import compute_signature  # noqa: E402
from src.api.routes import webhooks as wh  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class FakeDedupeDB:
    """Fakes the REST client's insert() against a unique-keyed table.

    First insert of an event_id returns the row; a second insert of the same id
    is a swallowed 409 → empty list. Same contract as the real client.
    """
    def __init__(self):
        self._seen: set[str] = set()
        self.insert_calls: list[tuple[str, dict]] = []

    async def insert(self, table, row, return_data=True):
        self.insert_calls.append((table, row))
        key = row["event_id"]
        if key in self._seen:
            return []
        self._seen.add(key)
        return [row] if return_data else []


class RaisingDB:
    """insert() blows up — simulates a DB outage mid-request."""
    async def insert(self, table, row, return_data=True):
        raise RuntimeError("connection reset")


def _fresh_worker():
    """A new WebhookProcessor wired to the real route helper — simulates another
    uvicorn worker with an empty in-process cache but the SAME shared DB."""
    return WebhookProcessor(record_webhook_event=wh._record_webhook_event)


def _make_request(body: bytes, headers: dict) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/webhooks/toast",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


# ── 1. Clover: first processes, cross-worker duplicate skipped (DB-driven) ─────

def test_clover_first_processes_duplicate_skipped_cross_worker():
    db_mod._db_instance = FakeDedupeDB()
    orig = wh.processor
    try:
        events = [{"type": "UPDATE", "objectId": "O:abc", "ts": 1717000000000}]

        # Worker 1 — first delivery processes.
        wh.processor = _fresh_worker()
        fresh1 = _run(wh._filter_fresh_clover_events("M1", events))
        assert fresh1 == events, "first delivery must be processed"

        # Worker 2 — empty in-memory cache, so the skip can only come from the
        # shared DB row.
        wh.processor = _fresh_worker()
        fresh2 = _run(wh._filter_fresh_clover_events("M1", events))
        assert fresh2 == [], "redelivery to another worker must be dropped"

        # Recorded under the documented key scheme + provider.
        assert db_mod._db_instance.insert_calls[0] == (
            "webhook_events",
            {"event_id": "clover:M1:O:abc:1717000000000", "provider": "clover"},
        )
    finally:
        wh.processor = orig
        db_mod._db_instance = None


# ── 2. Clover: a mixed batch yields only the fresh events ─────────────────────

def test_clover_partial_batch_only_fresh_processed():
    db_mod._db_instance = FakeDedupeDB()
    orig = wh.processor
    try:
        wh.processor = _fresh_worker()
        # Pre-seed: "old" is already recorded by an earlier delivery.
        seen = [{"type": "UPDATE", "objectId": "old", "ts": 1}]
        assert _run(wh._filter_fresh_clover_events("M1", seen)) == seen

        # New worker sees a batch with the old event + a new one → only new kept.
        wh.processor = _fresh_worker()
        batch = [
            {"type": "UPDATE", "objectId": "old", "ts": 1},
            {"type": "CREATE", "objectId": "new", "ts": 2},
        ]
        fresh = _run(wh._filter_fresh_clover_events("M1", batch))
        assert fresh == [{"type": "CREATE", "objectId": "new", "ts": 2}]
    finally:
        wh.processor = orig
        db_mod._db_instance = None


# ── 3. Clover: DB outage fails OPEN (process rather than drop) ────────────────

def test_clover_db_error_fails_open():
    db_mod._db_instance = RaisingDB()
    orig = wh.processor
    try:
        wh.processor = _fresh_worker()
        events = [{"type": "UPDATE", "objectId": "O:x", "ts": 1}]
        fresh = _run(wh._filter_fresh_clover_events("M1", events))
        assert fresh == events, "DB down must fail open (process the event)"
    finally:
        wh.processor = orig
        db_mod._db_instance = None


# ── 4. Toast: first delivery scheduled, cross-worker duplicate skipped ────────

def test_toast_first_processes_duplicate_skipped_cross_worker():
    os.environ["TOAST_WEBHOOK_SECRET"] = "shh-secret"
    db_mod._db_instance = FakeDedupeDB()
    orig = wh.processor
    try:
        body = json.dumps({
            "eventType": "order.created",
            "restaurantGuid": "R1",
            "webhookId": "wh-123",
        }).encode()
        sig = compute_signature("shh-secret", body)
        headers = {"Toast-Signature": sig, "content-type": "application/json"}

        # Worker 1 — valid signature, first delivery → 200 + scheduled.
        wh.processor = _fresh_worker()
        bg1 = BackgroundTasks()
        resp1 = _run(wh.toast_webhook(_make_request(body, headers), bg1))
        assert resp1.status_code == 200
        assert len(bg1.tasks) == 1, "first delivery must be scheduled for processing"

        # Worker 2 — fresh cache, shared DB → duplicate, ack 200 but NOT scheduled.
        wh.processor = _fresh_worker()
        bg2 = BackgroundTasks()
        resp2 = _run(wh.toast_webhook(_make_request(body, headers), bg2))
        assert resp2.status_code == 200
        assert len(bg2.tasks) == 0, "duplicate must be skipped (not scheduled)"

        assert db_mod._db_instance.insert_calls[0] == (
            "webhook_events",
            {"event_id": "toast:wh-123", "provider": "toast"},
        )
    finally:
        wh.processor = orig
        db_mod._db_instance = None
        os.environ.pop("TOAST_WEBHOOK_SECRET", None)


# ── 5. Toast: DB outage fails OPEN (first delivery still scheduled) ───────────

def test_toast_db_error_fails_open():
    os.environ["TOAST_WEBHOOK_SECRET"] = "shh-secret"
    db_mod._db_instance = RaisingDB()
    orig = wh.processor
    try:
        body = json.dumps({
            "eventType": "order.created",
            "restaurantGuid": "R1",
            "webhookId": "wh-boom",
        }).encode()
        sig = compute_signature("shh-secret", body)
        headers = {"Toast-Signature": sig, "content-type": "application/json"}

        wh.processor = _fresh_worker()
        bg = BackgroundTasks()
        resp = _run(wh.toast_webhook(_make_request(body, headers), bg))
        assert resp.status_code == 200
        assert len(bg.tasks) == 1, "DB down must fail open (still process)"
    finally:
        wh.processor = orig
        db_mod._db_instance = None
        os.environ.pop("TOAST_WEBHOOK_SECRET", None)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
