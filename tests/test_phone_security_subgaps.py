"""
Phone security sub-gaps (found in the 2026-07-21 gap sweep):

  1. DID-hijack: save_phone_config accepted a client-supplied phone_number and
     wrote it verbatim — a merchant could claim ANOTHER merchant's DID, and
     get_merchant_by_phone (first match) then routed that merchant's inbound
     calls nondeterministically. phone_number is now system-managed (only
     /provision-number sets it) and dropped from the config-save payload.

  2. Unknown-DID fallback safety: a dialed number with no merchant row falls
     back to the demo config. That config was NOT demo_safe, so the fallback
     could run the real order/charge path. _demo_config is now demo_safe=True —
     the fallback is provably logs-only.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_PHONE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services", "phone_agent"))
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import merchant_config as mc  # noqa: E402
from tests.test_menu_store import MID, FakeDB, _run  # noqa: E402

SERVICE = {"kind": "service"}


def _patch_membership(monkeypatch):
    from src.api import auth

    async def _ok(user, org_id):
        return True
    monkeypatch.setattr(auth, "_check_org_membership", _ok)


# ── 1. DID-hijack ────────────────────────────────────────────────────────
def test_config_save_ignores_client_supplied_phone_number(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID})
    monkeypatch.setattr(db_mod, "_db_instance", db)

    # Attacker tries to claim a victim's DID via the settings-save endpoint.
    req = PhoneConfigRequest(merchant_id=MID, phone_number="+15550009999",
                             greeting="hi")
    _run(save_phone_config(req, principal=SERVICE))

    row = db.tables["phone_agent_config"][0]
    assert row.get("greeting") == "hi"          # legit fields still save
    assert "phone_number" not in row, "phone_number must never be written by config save"


def test_config_save_does_not_overwrite_existing_number(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID, "phone_number": "+15551112222"})
    monkeypatch.setattr(db_mod, "_db_instance", db)

    req = PhoneConfigRequest(merchant_id=MID, phone_number="+15559998888",
                             business_name="New Name")
    _run(save_phone_config(req, principal=SERVICE))

    row = db.tables["phone_agent_config"][0]
    assert row["phone_number"] == "+15551112222", "provisioned DID unchanged by config save"
    assert row["business_name"] == "New Name"


# ── 2. unknown-DID fallback is provably harmless ─────────────────────────
def test_demo_fallback_config_is_demo_safe():
    cfg = mc._demo_config("demo")
    assert cfg.demo_safe is True, (
        "the unknown-DID fallback config must be demo_safe so a mis-routed real "
        "caller can never trigger a live order/charge")


# ── go-live gate: no activation without a provisioned number ──────────────
def test_activate_blocked_without_number(monkeypatch):
    import src.db as db_mod
    from fastapi import HTTPException
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID})  # no phone_number stored
    monkeypatch.setattr(db_mod, "_db_instance", db)

    req = PhoneConfigRequest(merchant_id=MID, active=True)
    import pytest as _pytest
    with _pytest.raises(HTTPException) as exc:
        _run(save_phone_config(req, principal=SERVICE))
    assert exc.value.status_code == 400


def test_activate_allowed_with_number(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID, "phone_number": "+15068017376",
                 "menu_items": [{"name": "Burger"}]})
    monkeypatch.setattr(db_mod, "_db_instance", db)

    req = PhoneConfigRequest(merchant_id=MID, active=True)
    _run(save_phone_config(req, principal=SERVICE))
    assert db.tables["phone_agent_config"][0].get("active") is True


def test_deactivate_never_blocked(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID})  # no number
    monkeypatch.setattr(db_mod, "_db_instance", db)

    # active=False must always be allowed (e.g. reclaim clears it)
    req = PhoneConfigRequest(merchant_id=MID, active=False)
    _run(save_phone_config(req, principal=SERVICE))
    assert db.tables["phone_agent_config"][0].get("active") is False
