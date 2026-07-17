"""E2E bug batch — round-trip coverage for the two backend fixes.

  A. Careers data loss: the Canada careers form posts UI-shaped keys
     (yearsExperience / commissionExperience / employer / linkedin / heardFrom /
     referral / message). Those were silently dropped by Pydantic, losing the
     experience, commission-experience, employer, LinkedIn, channel, referral
     name and motivation answers. The model now accepts both the UI keys and the
     canonical keys via AliasChoices, and persists commission_experience +
     referral_name. Asserted BOTH directions (UI keys AND canonical keys map).

  B. Menu unpublish: POST /api/menu/{id}/publish {published:false} must take the
     hosted page offline (published=false) instead of re-publishing, while
     retaining the slug so a republish reuses the URL. Asserted both directions.

Pattern mirrors tests/api/test_careers_pipeline.py: call the functions directly
with a fake DB, run via asyncio.run (no pytest-asyncio).

Run:  python -m pytest tests/api/test_careers_menu_e2efix.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes import careers as careers_mod  # noqa: E402
from src.api.routes import menu as menu_mod  # noqa: E402
from src.services import menu_store  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


# ── A. Careers key mapping (data-loss fix) ───────────────────────────────────

class _CareersDB:
    def __init__(self):
        self.inserts: list = []

    async def insert(self, table, data, return_data=True):
        self.inserts.append((table, data))
        return [data]


def _wire_careers(monkeypatch):
    db = _CareersDB()
    monkeypatch.setattr(careers_mod, "get_db", lambda: db)
    import src.email.send as email_send

    captured = {}

    async def _capture_email(*a, **kw):
        captured.update(kw)
        return {"status": "skipped"}

    monkeypatch.setattr(email_send, "send_career_application", _capture_email)
    return db, captured


def test_canada_ui_keys_map_end_to_end(monkeypatch):
    """The UI-shaped payload the Canada form actually sends must round-trip:
    no answer dropped, commission + referral-name persisted."""
    db, captured = _wire_careers(monkeypatch)

    # Exactly the wire shape CanadaCareersPage now posts.
    req = careers_mod.CareerApplication.model_validate({
        "name": "Alice Rep",
        "email": "alice@example.com",
        "phone": "416-555-0199",
        "position": "sales_rep",
        "city": "Toronto",
        "province": "ON",
        "experience": "5 years",              # canonical, from mapped yearsExperience
        "commission_experience": "yes",
        "current_employer": "XYZ Corp",
        "linkedin_url": "https://linkedin.com/in/alice",
        "referral_source": "LinkedIn",
        "referral_name": "Bob Referrer",
        "availability": "2 weeks",
        "motivation": "I love POS data.",
    })
    out = _run(careers_mod.submit_application(req, country="CA"))
    assert out["status"] == "received"

    row = next(d for t, d in db.inserts if t == "career_applications")
    # Every answer landed in its column — nothing silently dropped.
    assert row["experience"] == "5 years"
    assert row["commission_experience"] == "yes"
    assert row["current_employer"] == "XYZ Corp"
    assert row["linkedin_url"] == "https://linkedin.com/in/alice"
    assert row["referral_source"] == "LinkedIn"
    assert row["referral_name"] == "Bob Referrer"
    assert row["motivation"] == "I love POS data."
    assert row["state_province"] == "ON"
    # The commission answer also reaches the hiring inbox email.
    assert captured["commission_experience"] == "yes"
    assert captured["referral_name"] == "Bob Referrer"


def test_raw_ui_aliases_are_accepted(monkeypatch):
    """The raw UI aliases (yearsExperience/commissionExperience/employer/
    linkedin/heardFrom/referral/message) must also parse — the backend accepts
    them directly so an un-mapped caller still doesn't lose data."""
    db, _ = _wire_careers(monkeypatch)
    req = careers_mod.CareerApplication.model_validate({
        "name": "Cara Rep",
        "email": "cara@example.com",
        "position": "team_lead",
        "city": "Vancouver",
        "province": "BC",
        "yearsExperience": "8 years",
        "commissionExperience": "no",
        "employer": "Acme",
        "linkedin": "https://linkedin.com/in/cara",
        "heardFrom": "Referral",
        "referral": "Dana",
        "message": "Building a team.",
    })
    assert req.experience == "8 years"
    assert req.commission_experience == "no"
    assert req.current_employer == "Acme"
    assert req.linkedin_url == "https://linkedin.com/in/cara"
    assert req.referral_source == "Referral"
    assert req.referral_name == "Dana"
    assert req.motivation == "Building a team."
    _run(careers_mod.submit_application(req, country="CA"))
    row = next(d for t, d in db.inserts if t == "career_applications")
    assert row["commission_experience"] == "no" and row["referral_name"] == "Dana"


def test_us_canonical_keys_still_work(monkeypatch):
    """The US careers form posts canonical keys — must be unaffected."""
    _wire_careers(monkeypatch)
    req = careers_mod.CareerApplication.model_validate({
        "name": "Uma Rep", "email": "uma@example.com", "position": "sales_rep",
        "city": "Austin", "state": "TX", "experience": "3 years",
        "motivation": "Sunbelt sales.",
    })
    assert req.experience == "3 years" and req.motivation == "Sunbelt sales."
    assert req.state == "TX"
    assert req.commission_experience == "" and req.referral_name == ""


# ── B. Menu publish / unpublish (both directions) ────────────────────────────

class _MenuDB:
    def __init__(self, rows=None):
        self.menus = list(rows or [])
        self.updates: list = []
        self.inserts: list = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        if table == "merchant_menus":
            mid = (filters or {}).get("merchant_id", "")
            if mid:
                want = mid.removeprefix("eq.")
                return [dict(r) for r in self.menus if r.get("merchant_id") == want]
            return [dict(r) for r in self.menus]
        if table == "phone_agent_config":
            return [{"business_name": "Maple Bistro"}]
        return []

    async def update(self, table, data, filters):
        self.updates.append((table, data, filters))
        mid = filters.get("merchant_id", "").removeprefix("eq.")
        for r in self.menus:
            if r.get("merchant_id") == mid:
                r.update(data)
        return [data]

    async def insert(self, table, data, return_data=True):
        self.inserts.append((table, data))
        self.menus.append(dict(data))
        return [data]


class _Principal:
    email = "owner@meridian.test"


def _wire_menu(monkeypatch, db):
    async def _ok(*a, **kw):
        return None
    monkeypatch.setattr(menu_mod, "enforce_service_member", _ok)
    monkeypatch.setattr(menu_mod, "get_db", lambda: db)
    monkeypatch.setattr(menu_store, "_now", lambda: "2026-07-17T00:00:00Z")


MID = "biz_43e5ff96db22436096c83c9280a4009f"


def test_publish_then_unpublish_toggles_flag(monkeypatch):
    db = _MenuDB([{"merchant_id": MID, "public_slug": "maple-bistro", "published": True}])
    _wire_menu(monkeypatch, db)

    # Unpublish: published:false must flip the flag OFF (not re-publish).
    out = _run(menu_mod.publish_public_menu(
        MID, menu_mod.PublishRequest(published=False), _Principal()))
    assert out["published"] is False
    assert db.menus[0]["published"] is False
    # Slug retained so the URL survives a republish.
    assert db.menus[0]["public_slug"] == "maple-bistro"
    assert out["slug"] == "maple-bistro"

    # Public fetch now 404s (get_public_menu filters published=is.true).
    async def _sel_public(table, columns="*", filters=None, **kw):
        if table == "merchant_menus" and (filters or {}).get("published") == "is.true":
            return []
        return await _MenuDB.select(db, table, columns, filters, **kw)
    monkeypatch.setattr(db, "select", _sel_public)
    assert _run(menu_store.get_public_menu(db, "maple-bistro")) is None


def test_publish_republishes_after_unpublish(monkeypatch):
    db = _MenuDB([{"merchant_id": MID, "public_slug": "maple-bistro", "published": False}])
    _wire_menu(monkeypatch, db)

    # Bodyless / default publish re-publishes, reusing the same slug.
    out = _run(menu_mod.publish_public_menu(
        MID, menu_mod.PublishRequest(), _Principal()))
    assert out["published"] is True
    assert out["slug"] == "maple-bistro"
    assert db.menus[0]["published"] is True


def test_default_publish_request_is_true():
    # Backward-compat: a bodyless POST (no JSON) still publishes.
    assert menu_mod.PublishRequest().published is True
