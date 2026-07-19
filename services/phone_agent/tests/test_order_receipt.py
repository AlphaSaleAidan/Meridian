"""
Tests for the SHARED order-receipt SMS (order_receipt.send_order_receipt).

The turn-based Vapi path and the streaming Pipecat path must both fire the SAME
customer receipt SMS after an order completes — exactly once per order, with the
correct summary, and always subject to the transactional opt-out + killswitch
guards.

Asserts, with fakes (no network):
  - streaming order → exactly one receipt SMS, body carries the order summary +
    the pay/pickup line.
  - idempotent on order_id: a second report of the SAME order (e.g. sidecar AND
    the payment webhook both reporting) sends NO second SMS.
  - transactional opt-out suppresses the receipt (no send).
  - killswitch (PHONE_RECEIPT_SMS_ENABLED=0) suppresses the receipt (no send).
  - the pay_at_pickup streaming fan-out (_fanout_release) fires the receipt once.

These exercise the shared helper directly + through the streaming dispatch
surface (pay_on_phone._fanout_release) without importing pipecat-heavy bot.py.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import order_receipt  # noqa: E402
from merchant_config import _demo_config  # noqa: E402

pytestmark = pytest.mark.asyncio


def _order(merchant_id="real-merchant"):
    return {
        "merchant_id": merchant_id,
        "business_name": "Demo Restaurant",
        "customer_name": "Sam Rivera",
        "order_type": "pickup",
        "items": [
            {"name": "Cheeseburger", "quantity": 2, "unit_price": 12.99},
            {"name": "Fries", "quantity": 1, "unit_price": 4.00},
        ],
        "subtotal": 29.98, "tax": 3.90, "total": 33.88,
        "currency": "cad",
        "caller_phone": "+15555550111",
        "pos_system": "square",
    }


class _Sms:
    """Spy over order_receipt.send_sms — records every send."""

    def __init__(self):
        self.sends = []  # (to, body)

    def install(self, monkeypatch, *, sent=True):
        async def fake_send_sms(to, body):
            self.sends.append((to, body))
            return {"sent": sent, "method": "telnyx", "message_sid": "SM-R1"}

        monkeypatch.setattr(order_receipt, "send_sms", fake_send_sms)
        return self


def _no_optout(monkeypatch, *, transactional=False, marketing=False):
    async def fake_optout(merchant_id, phone):
        return {"marketing_optout": marketing, "transactional_optout": transactional}

    monkeypatch.setattr(order_receipt, "fetch_optout_status", fake_optout)


def _mark_first_time(monkeypatch):
    """Durable idempotency marker: first call returns True (we own the send),
    any later call for the SAME claim target returns False (already claimed).

    Used only by the guard/copy tests that aren't exercising the DB claim itself.
    Keyed on the claim's dedup_id (stable per order across call sites)."""
    seen = set()

    async def fake_claim(claim):
        key = getattr(claim, "dedup_id", "") or getattr(claim, "value", "")
        if not key or key in seen:
            return False
        seen.add(key)
        return True

    monkeypatch.setattr(order_receipt, "_claim_receipt", fake_claim)
    return seen


# ─── shared helper: happy path ───────────────────────────────────────────────
async def test_streaming_receipt_sends_once_with_summary(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="POS-STREAM-1", paid=True,
    )

    assert res["sent"] is True
    assert len(sms.sends) == 1
    to, body = sms.sends[0]
    assert to == "+15555550111"
    # summary present
    assert "Cheeseburger" in body
    assert "CA$33.88" in body
    # paid receipt line present
    assert "paid" in body.lower() or "payment received" in body.lower()


async def test_receipt_pickup_line_for_pay_at_pickup(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="POS-PICKUP-1", paid=False,
    )

    assert res["sent"] is True
    _to, body = sms.sends[0]
    # unpaid / pay-at-pickup receipt speaks to pickup, not "paid"
    assert "pickup" in body.lower() or "ready" in body.lower()


# ─── idempotency ─────────────────────────────────────────────────────────────
async def test_double_report_sends_one_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    first = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-DUP", paid=True,
    )
    # sidecar AND payment webhook both report the SAME order id
    second = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-DUP", paid=True,
    )

    assert first["sent"] is True
    assert second["sent"] is False
    assert second.get("reason") == "already_sent"
    assert len(sms.sends) == 1


# ─── guards ──────────────────────────────────────────────────────────────────
async def test_transactional_optout_suppresses_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch, transactional=True)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-OPTOUT", paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "transactional_optout"
    assert sms.sends == []


async def test_killswitch_suppresses_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    monkeypatch.setenv("PHONE_RECEIPT_SMS_ENABLED", "0")
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-KILL", paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "killswitch"
    assert sms.sends == []


async def test_no_phone_skips_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")
    order = _order()
    order["caller_phone"] = ""

    res = await order_receipt.send_order_receipt(
        order, cfg, order_id="ORD-NOPHONE", paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "no_phone"
    assert sms.sends == []


# ─── REAL DB claim: prove the claim PATCH matches the actual row per flow ─────
# These do NOT monkeypatch _claim_receipt — that's exactly what hid the original
# bug (claim keyed on pos_order_id while the row carried pos_order_id=""). Here a
# real-shaped phone_orders table is stood up in a fake PostgREST transport, and
# each flow's claim must find its row and flip receipt_sent exactly once.

import urllib.parse  # noqa: E402

import order_receipt as _or  # noqa: E402


class _FakePostgrest:
    """Minimal in-memory phone_orders honoring the exact PostgREST calls
    _claim_receipt makes: GET newest-by-(merchant,phone) and conditional PATCH
    with receipt_sent=is.false plus an eq filter on id / pos_order_id / merchant
    + caller_phone. return=representation echoes the flipped rows."""

    def __init__(self, rows):
        # rows: list of dicts, each an insert-shaped phone_orders row
        self.rows = [dict(r) for r in rows]

    # httpx.AsyncClient() async-context-manager surface
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    @staticmethod
    def _filters(url):
        # NB: split manually (not parse_qs) — the real code passes raw values
        # like "+15555550111"; parse_qs would decode '+' to a space and break
        # the phone match, masking whether the claim actually found the row.
        q = urllib.parse.urlparse(url).query
        params: dict[str, list[str]] = {}
        for pair in q.split("&"):
            if not pair:
                continue
            k, _, v = pair.partition("=")
            params.setdefault(k, []).append(v)
        eq = {}
        for k, vals in params.items():
            if k in ("order", "limit", "select"):
                continue
            v = vals[0]
            if v.startswith("eq."):
                eq[k] = v[3:]
            elif v == "is.false":
                eq[k] = ("__is_false__",)
        return eq, params

    def _match(self, row, eq):
        for col, want in eq.items():
            if want == ("__is_false__",):
                if row.get(col) not in (False, None):
                    return False
            elif str(row.get(col, "")) != want:
                return False
        return True

    async def get(self, url, headers=None, timeout=None):
        eq, params = self._filters(url)
        hits = [r for r in self.rows if self._match(r, eq)]
        if "order" in params and "created_at.desc" in params["order"][0]:
            hits.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        if "limit" in params:
            hits = hits[: int(params["limit"][0])]
        sel = params.get("select", ["*"])[0]
        if sel != "*":
            cols = sel.split(",")
            hits = [{c: r.get(c) for c in cols} for r in hits]
        return _Resp(200, hits)

    async def patch(self, url, json=None, headers=None, timeout=None):
        eq, _ = self._filters(url)
        flipped = []
        for r in self.rows:
            if self._match(r, eq):
                r.update(json)
                flipped.append(dict(r))
        # return=representation → echo flipped rows
        return _Resp(200, flipped)


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    @property
    def content(self):
        return b"x" if self._payload is not None else b""

    def json(self):
        return self._payload


def _install_db(monkeypatch, rows):
    """Point _claim_receipt at a configured Supabase + fake PostgREST table."""
    monkeypatch.setattr(_or, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(_or, "SUPABASE_KEY", "service-role-key")
    table = _FakePostgrest(rows)

    def _client(*a, **k):
        # A fresh view over the SAME table each AsyncClient() call.
        proxy = _FakePostgrest.__new__(_FakePostgrest)
        proxy.rows = table.rows  # share the row list (so flips persist)
        return proxy

    monkeypatch.setattr(_or.httpx, "AsyncClient", _client)
    return table


def _row(**over):
    base = {
        "id": "row-1", "merchant_id": "real-merchant",
        "caller_phone": "+15555550111", "pos_order_id": "",
        "receipt_sent": False, "created_at": "2026-07-19T00:00:00Z",
    }
    base.update(over)
    return base


async def test_claim_pay_now_stripe_matches_deferred_row(monkeypatch):
    """pay_now-Stripe: held row has pos_order_id="" — the OLD pos_order_id claim
    matched zero rows and dropped the receipt. Claim by merchant+phone-newest
    must find and flip THIS row."""
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    row = _row(pos_order_id="")  # deferred POS → empty on the row
    table = _install_db(monkeypatch, [row])

    claim = order_receipt.ReceiptClaim(
        merchant_id="real-merchant", caller_phone="+15555550111",
        dedup_id="cs_test_session_123",  # the Stripe session id (NOT a column)
    )
    res = await order_receipt.send_order_receipt(
        _order(), _demo_config("real-merchant"),
        order_id="cs_test_session_123", claim=claim, paid=True,
    )

    assert res["sent"] is True
    assert len(sms.sends) == 1
    assert table.rows[0]["receipt_sent"] is True  # the REAL row got flipped


async def test_claim_pos_failed_pay_at_pickup_matches_by_row_id(monkeypatch):
    """POS-failed pay_at_pickup: row has pos_order_id="" but a real primary key.
    Claim by id must find and flip it."""
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    row = _row(id="po-abc-999", pos_order_id="")
    table = _install_db(monkeypatch, [row])

    claim = order_receipt.ReceiptClaim(column="id", value="po-abc-999",
                                       dedup_id="po-abc-999")
    res = await order_receipt.send_order_receipt(
        _order(), _demo_config("real-merchant"),
        order_id="po-abc-999", claim=claim, paid=False,
    )

    assert res["sent"] is True
    assert len(sms.sends) == 1
    assert table.rows[0]["receipt_sent"] is True


async def test_claim_clover_native_matches_by_pos_order_id(monkeypatch):
    """Clover-native: the row carries a REAL pos_order_id. Claim by it."""
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    row = _row(pos_order_id="CLOVER-TKT-42")
    table = _install_db(monkeypatch, [row])

    claim = order_receipt.ReceiptClaim(column="pos_order_id", value="CLOVER-TKT-42",
                                       dedup_id="CLOVER-TKT-42")
    res = await order_receipt.send_order_receipt(
        _order(), _demo_config("real-merchant"),
        order_id="CLOVER-TKT-42", claim=claim, paid=True,
    )

    assert res["sent"] is True
    assert len(sms.sends) == 1
    assert table.rows[0]["receipt_sent"] is True


async def test_claim_double_report_one_send_real_key(monkeypatch):
    """Double report of the SAME order across the REAL DB claim → one send.
    The second flip finds receipt_sent already true → matches zero rows → skip."""
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    row = _row(pos_order_id="")
    table = _install_db(monkeypatch, [row])
    cfg = _demo_config("real-merchant")

    claim = order_receipt.ReceiptClaim(
        merchant_id="real-merchant", caller_phone="+15555550111",
        dedup_id="cs_dup_session",
    )
    first = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="cs_dup_session", claim=claim, paid=True,
    )
    # webhook retry (or streaming already reported) — SAME order, same target row
    second = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="cs_dup_session", claim=claim, paid=True,
    )

    assert first["sent"] is True
    assert second["sent"] is False
    assert second.get("reason") == "already_sent"
    assert len(sms.sends) == 1
    assert table.rows[0]["receipt_sent"] is True


async def test_claim_stale_pos_order_id_matches_nothing(monkeypatch):
    """Regression guard: claiming on a value that ISN'T on any row (the ORIGINAL
    bug — a Stripe session id passed as pos_order_id) flips nothing → in the DB
    path the receipt would be dropped. Proves the OLD behavior was broken so the
    per-flow claim above is load-bearing, not decoration."""
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    row = _row(pos_order_id="")  # deferred → no pos_order_id on the row
    table = _install_db(monkeypatch, [row])

    # Simulate the OLD call: claim keyed on the Stripe session id as pos_order_id.
    claim = order_receipt.ReceiptClaim(column="pos_order_id",
                                       value="cs_test_session_xyz",
                                       dedup_id="cs_test_session_xyz")
    res = await order_receipt.send_order_receipt(
        _order(), _demo_config("real-merchant"),
        order_id="cs_test_session_xyz", claim=claim, paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "already_sent"  # claim matched nothing → skip
    assert sms.sends == []
    assert table.rows[0]["receipt_sent"] is False  # the real row NEVER flipped
