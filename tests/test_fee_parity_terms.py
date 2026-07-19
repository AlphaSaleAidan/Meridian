"""Fee-parity provisioning — canonical fee terms, lead lock, terms table doctrine.

Covers:
  • the canonical tier table mirrors the frontend proposal-plans values
  • resolve_fee_terms server-side defaulting + clamping (old clients keep working)
  • provisioning copies lead terms → merchant_billing_terms (mock db)
  • supersede-not-update doctrine + admin override requires a reason
  • the close/provision paths are actually wired (source inspection, same
    pattern as tests/api/test_provision_plan_tier.py)

Run:  python -m pytest tests/test_fee_parity_terms.py -v
"""
from __future__ import annotations

import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.billing import fee_terms as ft  # noqa: E402


class MockDB:
    """Records every call; select returns canned per-table fixtures."""

    def __init__(self, select_results: dict | None = None):
        self.calls: list[tuple] = []
        self.select_results = select_results or {}

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        self.calls.append(("select", table, filters))
        return list(self.select_results.get(table, []))

    async def insert(self, table, data, return_data=True):
        self.calls.append(("insert", table, data))
        return [dict(data)]

    async def update(self, table, data, filters):
        self.calls.append(("update", table, data, filters))
        return []

    def ops(self, kind):
        return [c for c in self.calls if c[0] == kind]


# ── Canonical table mirrors proposal-plans.ts / canada-proposal-plans.ts ────

@pytest.mark.parametrize("market,tier,monthly,order_fee,floor", [
    ("us", "standard", 25000, 0, 0),
    ("us", "premium", 35000, 149, 65),
    ("us", "command", 50000, 100, 45),
    ("ca", "standard", 35000, 0, 0),
    # CAD floors = USD floors × 1.4 (Aidan 2026-07-19): 65→91, 45→63.
    ("ca", "premium", 50000, 199, 91),
    ("ca", "command", 70000, 139, 63),
])
def test_canonical_table_matches_frontend_plans(market, tier, monthly, order_fee, floor):
    base = ft.CANONICAL_FEE_TERMS[market][tier]
    assert base["monthly_fee_cents"] == monthly
    assert base["order_fee_cents"] == order_fee
    assert base["order_fee_floor_cents"] == floor
    assert base["call_overage_cents_per_min"] == 45
    assert base["included_call_min"] == 3


def test_canonical_json_export_round_trips():
    import json
    assert json.loads(ft.canonical_fee_terms_json()) == ft.CANONICAL_FEE_TERMS


@pytest.mark.parametrize("raw,expected", [
    ("CA", "ca"), ("ca", "ca"), ("cad", "ca"), ("US", "us"), ("usd", "us"),
    ("usa", "us"), (None, "ca"), ("", "ca"), ("canada", "ca"),
])
def test_normalize_market(raw, expected):
    assert ft.normalize_market(raw) == expected


# ── resolve_fee_terms: server-side REQUIRED-by-defaulting ────────────────────

def test_resolve_defaults_everything_from_tier():
    terms = ft.resolve_fee_terms("ca", plan_tier="premium")
    assert terms == {
        "plan_tier": "premium",
        "monthly_fee_cents": 50000,
        "order_fee_cents": 199,
        "call_overage_cents_per_min": 45,
        "included_call_min": 3,
    }


def test_resolve_old_client_no_fields_still_locks_full_terms():
    # Old clients that send nothing must still produce complete terms.
    terms = ft.resolve_fee_terms("us")
    assert terms["plan_tier"] == ft.DEFAULT_PLAN_TIER
    assert all(terms[f] is not None for f in ft.FEE_TERM_FIELDS)


def test_resolve_unknown_tier_falls_back_to_closest_by_monthly():
    # 'weekly' isn't a canonical tier; CA$700/mo → command.
    terms = ft.resolve_fee_terms("ca", plan_tier="weekly", monthly_fee_cents=70000)
    assert terms["plan_tier"] == "command"
    assert terms["order_fee_cents"] == 139


def test_resolve_keeps_rep_price_bump_within_headroom():
    # CA premium base 50000 + CA$150 headroom = 65000 max.
    assert ft.resolve_fee_terms("ca", "premium", monthly_fee_cents=57500)["monthly_fee_cents"] == 57500
    assert ft.resolve_fee_terms("ca", "premium", monthly_fee_cents=99000)["monthly_fee_cents"] == 65000
    # never below the tier base (tiers are floors, never discounted)
    assert ft.resolve_fee_terms("ca", "premium", monthly_fee_cents=10000)["monthly_fee_cents"] == 50000


def test_resolve_clamps_order_fee_to_tier_redline_and_ceiling():
    # crafted low fee → clamped up to the floor
    assert ft.resolve_fee_terms("us", "premium", order_fee_cents=1)["order_fee_cents"] == 65
    assert ft.resolve_fee_terms("ca", "command", order_fee_cents=1)["order_fee_cents"] == 63
    # above the tier standard rate → clamped down
    assert ft.resolve_fee_terms("us", "command", order_fee_cents=9999)["order_fee_cents"] == 100
    # in-range negotiated fee passes through
    assert ft.resolve_fee_terms("ca", "premium", order_fee_cents=120)["order_fee_cents"] == 120


def test_terms_from_lead_row_locked_columns_win():
    lead = {
        "monthly_value": 500, "plan_tier": "premium",
        "monthly_fee_cents": 52500, "order_fee_cents": 150,
        "call_overage_cents_per_min": 45, "included_call_min": 3,
        "fee_terms_locked_at": "2026-07-16T00:00:00Z",
    }
    terms = ft.terms_from_lead_row("ca", lead)
    assert terms["monthly_fee_cents"] == 52500
    assert terms["order_fee_cents"] == 150


def test_terms_from_lead_row_pre_migration_lead_infers_from_monthly_value():
    terms = ft.terms_from_lead_row("ca", {"monthly_value": 700})
    assert terms["plan_tier"] == "command"
    assert terms["monthly_fee_cents"] == 70000
    assert terms["order_fee_cents"] == 139


# ── merchant_billing_terms: provision copies lead → terms ────────────────────

async def test_set_terms_supersedes_then_inserts_never_updates_in_place():
    db = MockDB()
    terms = ft.resolve_fee_terms("ca", "premium", order_fee_cents=150)
    row = await ft.set_merchant_billing_terms(
        db, "org-1", terms, source_lead_id="lead-1", source_market="ca",
        created_by="rep@x.com")
    assert row is not None
    # 1) active row superseded first
    kind, table, data, filters = db.ops("update")[0]
    assert table == "merchant_billing_terms"
    assert "superseded_at" in data and set(data) == {"superseded_at"}
    assert filters == {"merchant_id": "eq.org-1", "superseded_at": "is.null"}
    # 2) fresh row inserted with full terms + linkage
    _, table, inserted = db.ops("insert")[0]
    assert table == "merchant_billing_terms"
    assert inserted["source_lead_id"] == "lead-1"
    assert inserted["source_market"] == "ca"
    assert inserted["monthly_fee_cents"] == 50000
    assert inserted["order_fee_cents"] == 150
    assert inserted["override_reason"] is None  # lead-sourced = automatic


async def test_set_terms_manual_provision_records_reason():
    db = MockDB()
    await ft.set_merchant_billing_terms(
        db, "org-2", ft.resolve_fee_terms("us", "command"),
        created_by="provision_customer", override_reason="manual_provision")
    _, _, inserted = db.ops("insert")[0]
    assert inserted["override_reason"] == "manual_provision"
    assert inserted["source_lead_id"] is None


async def test_set_terms_failure_returns_none_not_raise():
    class BoomDB(MockDB):
        async def update(self, *a, **k):
            raise RuntimeError("table missing")
    assert await ft.set_merchant_billing_terms(BoomDB(), "org-3", ft.resolve_fee_terms("ca")) is None


async def test_get_active_terms_fail_open_returns_none():
    class BoomDB(MockDB):
        async def select(self, *a, **k):
            raise RuntimeError("no such table")
    assert await ft.get_active_terms(BoomDB(), "org-1") is None
    assert await ft.get_active_terms(MockDB(), "") is None


async def test_lock_lead_fee_terms_only_locks_unlocked_rows():
    db = MockDB()
    ok = await ft.lock_lead_fee_terms(db, "us", "lead-9", ft.resolve_fee_terms("us", "premium"), "rep@x.com")
    assert ok
    _, table, data, filters = db.ops("update")[0]
    assert table == "us_leads"
    # first-lock-wins: the filter excludes already-locked rows
    assert filters == {"id": "eq.lead-9", "fee_terms_locked_at": "is.null"}
    assert data["plan_tier"] == "premium" and data["fee_terms_locked_by"] == "rep@x.com"
    assert data["fee_terms_locked_at"]


# ── Admin override endpoint: supersede + mandatory reason ────────────────────

def test_override_request_requires_reason():
    from src.api.routes import billing as billing_mod
    with pytest.raises(Exception):
        billing_mod.TermsOverrideRequest(override_reason="", monthly_fee_cents=1000)
    with pytest.raises(Exception):
        billing_mod.TermsOverrideRequest(override_reason="  x ", monthly_fee_cents=1000)
    req = billing_mod.TermsOverrideRequest(override_reason="mispriced at signup", monthly_fee_cents=1000)
    assert req.override_reason == "mispriced at signup"


async def test_override_supersedes_and_records_reason(monkeypatch):
    from src.api.routes import billing as billing_mod
    db = MockDB(select_results={"merchant_billing_terms": [{
        "merchant_id": "org-7", "plan_tier": "premium",
        "monthly_fee_cents": 50000, "order_fee_cents": 199,
        "call_overage_cents_per_min": 45, "included_call_min": 3,
        "source_lead_id": "lead-7", "source_market": "ca",
    }]})
    monkeypatch.setattr(billing_mod, "get_db", lambda: db)
    resp = await billing_mod.override_billing_terms(
        "org-7",
        billing_mod.TermsOverrideRequest(override_reason="rep undersold; corrected per Aidan ticket",
                                         monthly_fee_cents=52500),
        admin={"email": "admin@meridian.tips"},
    )
    assert resp["ok"] is True
    _, _, data, filters = db.ops("update")[0]
    assert set(data) == {"superseded_at"} and filters["superseded_at"] == "is.null"
    _, _, inserted = db.ops("insert")[0]
    assert inserted["monthly_fee_cents"] == 52500
    assert inserted["order_fee_cents"] == 199  # untouched fields carry over
    assert inserted["override_reason"].startswith("rep undersold")
    assert inserted["created_by"] == "admin@meridian.tips"


async def test_override_requires_at_least_one_field(monkeypatch):
    from fastapi import HTTPException
    from src.api.routes import billing as billing_mod
    monkeypatch.setattr(billing_mod, "get_db", lambda: MockDB())
    with pytest.raises(HTTPException) as exc:
        await billing_mod.override_billing_terms(
            "org-8", billing_mod.TermsOverrideRequest(override_reason="valid reason"),
            admin={"email": "admin@meridian.tips"})
    assert exc.value.status_code == 400


# ── Wiring: the close/provision/consumption paths actually use fee terms ─────

def test_create_customer_paths_provision_fee_terms():
    from src.api.routes import canada as canada_mod
    from src.api.routes import us as us_mod
    assert "_provision_fee_terms" in inspect.getsource(canada_mod.create_customer)
    assert "_provision_fee_terms" in inspect.getsource(us_mod.create_customer)


def test_provision_customer_copies_lead_terms():
    from src.api.routes import onboarding as onboarding_mod
    # endpoint delegates to the unit-tested helper
    assert "_record_provision_fee_terms" in inspect.getsource(onboarding_mod.provision_customer)
    src = inspect.getsource(onboarding_mod._record_provision_fee_terms)
    assert "set_merchant_billing_terms" in src
    assert "terms_from_lead_row" in src
    assert "manual_provision" in src
    assert "lock_lead_fee_terms" in src
    # request carries the lead linkage
    fields = onboarding_mod.ProvisionCustomerRequest.model_fields
    assert "lead_id" in fields and "lead_market" in fields


# ── provision-customer fee-terms order of operations (New Customer flow) ─────
# The New Customer pages insert the CRM lead FIRST, then provision with its
# lead_id — the helper must end with (1) merchant_billing_terms linked to that
# lead and (2) the lead carrying locked fee-term columns.

def _prov_req(**over):
    from src.api.routes.onboarding import ProvisionCustomerRequest
    base = dict(
        org_id="7a5ba1f6-1111-4222-8333-944445555666", email="owner@example.com", owner_name="Owner",
        business_name="Biz", plan="premium", monthly_price=350,
        rep_id="rep-1", rep_name="Rep One", country="US",
    )
    base.update(over)
    return ProvisionCustomerRequest(**base)


async def test_provision_locks_fresh_lead_and_links_billing_terms():
    """New Customer flow: unlocked lead → server-side lock + linked contract."""
    from src.api.routes.onboarding import _record_provision_fee_terms
    db = MockDB(select_results={"us_leads": [{"id": "lead-nc", "stage": "closed_won"}]})
    recorded, terms = await _record_provision_fee_terms(
        db, _prov_req(lead_id="lead-nc", lead_market="us"))
    assert recorded and terms["plan_tier"] == "premium"
    # (2) the lead got locked — first-lock-wins update on us_leads
    lock = [u for u in db.ops("update") if u[1] == "us_leads"]
    assert len(lock) == 1
    _, _, patch, filters = lock[0]
    assert filters == {"id": "eq.lead-nc", "fee_terms_locked_at": "is.null"}
    assert patch["fee_terms_locked_at"] and patch["fee_terms_locked_by"] == "Rep One"
    assert patch["plan_tier"] == "premium"
    # (1) billing contract links back to the lead, not flagged manual
    _, _, row = db.ops("insert")[-1]
    assert row["source_lead_id"] == "lead-nc"
    assert row["source_market"] == "us"
    assert row["override_reason"] is None


async def test_provision_copies_already_locked_lead_verbatim():
    """LeadDetail close path: locked lead terms are the contract of record."""
    from src.api.routes.onboarding import _record_provision_fee_terms
    db = MockDB(select_results={"us_leads": [{
        "id": "lead-lk", "plan_tier": "command", "monthly_fee_cents": 50000,
        "order_fee_cents": 100, "call_overage_cents_per_min": 45,
        "included_call_min": 3, "fee_terms_locked_at": "2026-07-01T00:00:00Z",
    }]})
    recorded, terms = await _record_provision_fee_terms(
        db, _prov_req(lead_id="lead-lk", lead_market="us", plan="premium"))
    assert recorded and terms["plan_tier"] == "command"  # lead wins over req.plan
    # already locked → no rewrite of the lead
    assert [u for u in db.ops("update") if u[1] == "us_leads"] == []
    _, _, row = db.ops("insert")[-1]
    assert row["source_lead_id"] == "lead-lk" and row["override_reason"] is None


async def test_provision_without_lead_stays_manual_provision():
    """Backward compat: self-serve wizards send no lead_id — unchanged path."""
    from src.api.routes.onboarding import _record_provision_fee_terms
    db = MockDB()
    recorded, terms = await _record_provision_fee_terms(db, _prov_req())
    assert recorded and terms["plan_tier"] == "premium"
    # nothing to lock (only the merchant_billing_terms supersede update runs)
    assert [u for u in db.ops("update") if u[1] in ("us_leads", "canada_leads")] == []
    _, _, row = db.ops("insert")[-1]
    assert row["source_lead_id"] is None
    assert row["override_reason"] == "manual_provision"


async def test_provision_with_missing_lead_falls_back_to_manual():
    """A lead_id that matches no row must not link or lock anything."""
    from src.api.routes.onboarding import _record_provision_fee_terms
    db = MockDB(select_results={"us_leads": []})
    recorded, _ = await _record_provision_fee_terms(
        db, _prov_req(lead_id="ghost", lead_market="us"))
    assert recorded
    assert [u for u in db.ops("update") if u[1] in ("us_leads", "canada_leads")] == []
    _, _, row = db.ops("insert")[-1]
    assert row["source_lead_id"] is None
    assert row["override_reason"] == "manual_provision"


def test_billing_service_reads_contracted_monthly_and_prechecks():
    from src.billing.billing_service import BillingService
    src = inspect.getsource(BillingService.process_renewals)
    assert "get_active_terms" in src
    assert "check_merchant" in src


def test_vapi_end_of_call_uses_merchant_terms_fail_open():
    from src.api.routes import vapi_webhook as vw
    src = inspect.getsource(vw)
    assert "get_active_terms" in src
    assert "included_call_min" in src and "call_overage_cents_per_min" in src


def test_stripe_connect_order_fee_prefers_terms_over_env():
    from src.api.routes import stripe_connect as sc
    src = inspect.getsource(sc._merchant_service_fee_cents)
    assert "get_active_terms" in src
    # env default remains the final fallback
    assert "MERIDIAN_SERVICE_FEE_CENTS" in src
