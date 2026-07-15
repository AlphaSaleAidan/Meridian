"""
Hardening (2026-07-15 bug hunt round 2):
  - inventory-docs list is bounded (no all-rows OOM) + paginated
  - status updates carry org_id (defense in depth)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

aio = pytest.mark.asyncio


class _DB:
    def __init__(self):
        self.select_calls = []
        self.update_calls = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        self.select_calls.append({"table": table, "filters": filters, "order": order,
                                  "limit": limit, "offset": offset})
        return []

    async def update(self, table, data, filters=None):
        self.update_calls.append({"table": table, "data": data, "filters": filters})
        return []


@aio
async def test_list_docs_is_bounded_and_ordered(monkeypatch):
    import src.api.routes.inventory_docs as inv
    import src.db as dbmod
    db = _DB()
    monkeypatch.setattr(dbmod, "_db_instance", db, raising=False)
    inv_db = sys.modules["src.db"]
    monkeypatch.setattr(inv_db, "_db_instance", db, raising=False)

    # default caps
    await inv.list_docs("org-1")
    call = db.select_calls[-1]
    assert call["limit"] == 200 and call["offset"] == 0
    assert call["order"] == "created_at.desc"
    assert call["filters"] == {"org_id": "eq.org-1"}

    # over-max is clamped to 500; negative offset floored to 0
    await inv.list_docs("org-1", limit=99999, offset=-5)
    call = db.select_calls[-1]
    assert call["limit"] == 500 and call["offset"] == 0


@aio
async def test_process_update_is_org_scoped(monkeypatch):
    import src.api.routes.inventory_docs as inv
    import src.db as dbmod

    class _DB2(_DB):
        async def select(self, *a, **k):
            self.select_calls.append(k)
            return [{"id": "doc-9", "status": "pending", "org_id": "org-1"}]

    db = _DB2()
    monkeypatch.setattr(dbmod, "_db_instance", db, raising=False)
    monkeypatch.setattr(sys.modules["src.db"], "_db_instance", db, raising=False)

    class _BG:
        def add_task(self, *a, **k):
            pass

    await inv.process_doc("org-1", "doc-9", _BG())
    # the status flip must be scoped to the org, not just the doc id
    upd = db.update_calls[-1]
    assert upd["filters"] == {"id": "eq.doc-9", "org_id": "eq.org-1"}
