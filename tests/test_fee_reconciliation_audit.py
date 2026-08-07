"""Fee reconciliation diff logic + audit script read-only guard.

Run:  python -m pytest tests/test_fee_reconciliation_audit.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.billing import fee_reconciliation as fr  # noqa: E402


class MockDB:
    def __init__(self, select_results: dict | None = None):
        self.calls: list[tuple] = []
        self.select_results = select_results or {}

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        self.calls.append(("select", table, filters))
        res = self.select_results.get(table, [])
        return res(filters) if callable(res) else list(res)


# call_overage_cents_per_min 0 = the current standard: call time is not billed
# (overage retired 2026-08-07, Aidan). A LEGACY row still carrying 45 is a real
# drift and must be reported — see test_check_merchant_flags_legacy_overage_terms.
TERMS_ROW = {
    "merchant_id": "org-1", "plan_tier": "premium",
    "monthly_fee_cents": 50000, "order_fee_cents": 199,
    "call_overage_cents_per_min": 0, "included_call_min": 3,
}


# ── diff_terms (pure) ────────────────────────────────────────────────────────

def test_diff_match_is_empty():
    c = {"monthly_fee_cents": 50000, "order_fee_cents": 199}
    assert fr.diff_terms("m1", c, dict(c)) == []


def test_diff_mismatch_reports_delta_positive_when_overbilled():
    diffs = fr.diff_terms("m1", {"monthly_fee_cents": 50000}, {"monthly_fee_cents": 57500})
    assert diffs == [{"merchant_id": "m1", "field": "monthly_fee_cents",
                      "contracted": 50000, "applied": 57500, "delta": 7500}]


def test_diff_underbilled_delta_negative():
    diffs = fr.diff_terms("m1", {"order_fee_cents": 199}, {"order_fee_cents": 65})
    assert diffs[0]["delta"] == -134


def test_diff_skips_fields_missing_on_either_side():
    assert fr.diff_terms("m1", {"monthly_fee_cents": 50000}, {"order_fee_cents": 199}) == []
    assert fr.diff_terms("m1", {"monthly_fee_cents": None}, {"monthly_fee_cents": 100}) == []


def test_diff_non_numeric_fields_compared_as_strings():
    diffs = fr.diff_terms("m1", {"plan_tier": "premium"}, {"plan_tier": "command"})
    assert diffs[0]["delta"] is None


# ── check_merchant guard hook ────────────────────────────────────────────────

async def test_check_merchant_healthy(monkeypatch):
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "0")
    db = MockDB({
        "merchant_billing_terms": [TERMS_ROW],
        "subscriptions": [{"org_id": "org-1", "status": "active", "monthly_price_cents": 50000}],
        "phone_agent_config": [{"merchant_id": "org-1", "order_fee_cents": 199, "plan_tier": "premium"}],
        "merchant_websites": [],
    })
    assert await fr.check_merchant(db, "org-1") == []


async def test_check_merchant_flags_legacy_overage_terms(monkeypatch):
    """Merchants provisioned before the overage was retired still carry
    call_overage_cents_per_min=45 in merchant_billing_terms while the live
    config applies 0. That IS a drift and must surface — the reconciler is how
    we find the rows that need their terms superseded."""
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "0")
    db = MockDB({
        "merchant_billing_terms": [dict(TERMS_ROW, call_overage_cents_per_min=45)],
        "subscriptions": [{"org_id": "org-1", "status": "active", "monthly_price_cents": 50000}],
        "phone_agent_config": [{"merchant_id": "org-1", "order_fee_cents": 199, "plan_tier": "premium"}],
        "merchant_websites": [],
    })
    diffs = await fr.check_merchant(db, "org-1")
    overage = [d for d in diffs if d["field"] == "call_overage_cents_per_min"]
    assert len(overage) == 1
    assert overage[0]["contracted"] == 45
    assert overage[0]["applied"] == 0
    assert overage[0]["delta"] == -45      # underbilled vs the legacy contract


async def test_check_merchant_flags_monthly_drift(monkeypatch):
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "0")
    db = MockDB({
        "merchant_billing_terms": [TERMS_ROW],
        "subscriptions": [{"org_id": "org-1", "status": "active", "monthly_price_cents": 57500}],
        "phone_agent_config": [{"merchant_id": "org-1", "order_fee_cents": 199, "plan_tier": "premium"}],
        "merchant_websites": [],
    })
    mismatches = await fr.check_merchant(db, "org-1")
    fields = {m["field"]: m for m in mismatches}
    assert fields["monthly_fee_cents"]["delta"] == 7500
    assert fields["monthly_fee_cents"]["contract_source"] == "terms"


async def test_check_merchant_no_contract_returns_empty():
    db = MockDB({"merchant_billing_terms": [], "businesses": [], "subscriptions": []})
    assert await fr.check_merchant(db, "org-x") == []


async def test_check_merchant_fail_open():
    class BoomDB(MockDB):
        async def select(self, *a, **k):
            raise RuntimeError("db down")
    assert await fr.check_merchant(BoomDB(), "org-1") == []


# ── reconcile_all fixtures: match / mismatch / missing linkage ───────────────

async def test_reconcile_all_classifies_matched_mismatched_unlinked(monkeypatch):
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "0")
    terms_ok = dict(TERMS_ROW)
    terms_drift = {**TERMS_ROW, "merchant_id": "org-2", "monthly_fee_cents": 70000}

    def terms_lookup(filters):
        mid = (filters or {}).get("merchant_id", "")
        if mid == "eq.org-1":
            return [terms_ok]
        if mid == "eq.org-2":
            return [terms_drift]
        return []

    db = MockDB({
        "subscriptions": [
            {"org_id": "org-1", "status": "active", "monthly_price_cents": 50000},
            {"org_id": "org-2", "status": "active", "monthly_price_cents": 50000},  # underbilled vs contract
            {"org_id": "org-3", "status": "active", "monthly_price_cents": 25000},  # no contract, no lead
        ],
        "merchant_billing_terms": terms_lookup,
        "phone_agent_config": lambda f: (
            [{"merchant_id": "org-1", "order_fee_cents": 199}] if (f or {}).get("merchant_id") == "eq.org-1"
            else [{"merchant_id": "org-2", "order_fee_cents": 199}] if (f or {}).get("merchant_id") == "eq.org-2"
            else []),
        "merchant_websites": [],
        "businesses": [],
        "canada_leads": [],
        "us_leads": [],
    })
    report = await fr.reconcile_all(db)
    assert report["checked"] == 3
    assert report["matched"] == ["org-1"]
    assert [m["merchant_id"] for m in report["mismatched"]] == ["org-2"]
    assert report["mismatched"][0]["monthly_delta_cents"] == -20000
    assert report["unlinked"] == ["org-3"]
    assert report["healthy"] is False
    assert report["total_monthly_delta_cents"] == -20000


async def test_reconcile_all_lead_fallback_by_email(monkeypatch):
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "0")
    db = MockDB({
        "subscriptions": [{"org_id": "org-9", "status": "active", "monthly_price_cents": 70000}],
        "merchant_billing_terms": [],
        "businesses": [{"id": "org-9", "email": "Owner@Shop.ca"}],
        "canada_leads": [{
            "contact_email": "owner@shop.ca", "stage": "closed_won",
            "monthly_value": 500, "plan_tier": "premium",
            "monthly_fee_cents": 50000, "order_fee_cents": 199,
            "call_overage_cents_per_min": 45, "included_call_min": 3,
            "fee_terms_locked_at": "2026-07-16T00:00:00Z",
        }],
        "us_leads": [],
        "phone_agent_config": [{"merchant_id": "org-9", "order_fee_cents": 199, "plan_tier": "premium"}],
        "merchant_websites": [],
    })
    report = await fr.reconcile_all(db)
    assert [m["merchant_id"] for m in report["mismatched"]] == ["org-9"]
    m = report["mismatched"][0]
    assert m["contract_source"] == "lead"
    assert m["monthly_delta_cents"] == 20000  # OVERBILLED by $200/mo


# ── audit script: read-only guard + redaction ────────────────────────────────

def _audit_module():
    import importlib.util
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "scripts", "fee_parity_audit.py"))
    spec = importlib.util.spec_from_file_location("fee_parity_audit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_audit_query_builder_refuses_non_get():
    mod = _audit_module()
    client = mod.ReadOnlySupabase("https://example.supabase.co", "key")
    for verb in ("POST", "PATCH", "PUT", "DELETE", "post", "delete"):
        with pytest.raises(AssertionError):
            client.build_request(verb, "subscriptions", {"select": "*"})


def test_audit_query_builder_builds_get_only():
    mod = _audit_module()
    client = mod.ReadOnlySupabase("https://example.supabase.co", "key")
    req = client.build_request("GET", "canada_leads", {"select": "*", "stage": "eq.closed_won"})
    assert req.get_method() == "GET"
    assert "canada_leads" in req.full_url and "stage=eq.closed_won" in req.full_url


def test_audit_script_source_has_no_write_verbs():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "scripts", "fee_parity_audit.py"))
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if "sys.path.insert" in line:  # module import path setup, not a DB write
            continue
        for needle in (".insert(", ".update(", ".upsert(", ".delete(", ".rpc(",
                       "method=\"POST\"", "method=\"PATCH\"", "method=\"DELETE\""):
            assert needle not in line, (
                f"audit script must be read-only (found {needle} at line {i})")


def test_audit_redacts_emails():
    mod = _audit_module()
    assert mod.redact_email("owner@shop.ca") == "own***@shop.ca"
    assert mod.redact_email("ab@x.io") == "ab***@x.io"
    assert mod.redact_email("") == "(none)"
