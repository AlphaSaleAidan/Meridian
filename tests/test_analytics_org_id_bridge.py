"""Read-path org-id bridge regression.

OAuth-connected merchants authenticate as `biz_<hex>` but their transactions /
products / revenue aggregates are stored under the deterministic uuid5 companion
(connection_org_id) by the write path (oauth.py, pos sync). The analytics + AI
read helpers used to pass the raw biz_ id straight to the uuid-keyed tables, so
the query matched nothing (the 22P02 cast error is swallowed as empty) and the
merchant saw blank dashboards / the AI ran on no data. The helpers must map the
org id the same way the write path does.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.db.supabase_rest import SupabaseREST  # noqa: E402
from src.db.org_ids import connection_org_id  # noqa: E402

BIZ = "biz_0123456789abcdef0123"
COMPANION = connection_org_id(BIZ)  # the uuid5 the write path stores under

aio = pytest.mark.asyncio


def _rest_with_capture():
    """A SupabaseREST whose .select records the org_id filter it was called with."""
    rest = SupabaseREST.__new__(SupabaseREST)  # skip __init__/network
    captured = []

    async def fake_select(table, columns="*", filters=None, order=None, limit=None, offset=None):
        captured.append({"table": table, "org_id": (filters or {}).get("org_id")})
        return []

    rest.select = fake_select
    return rest, captured


@aio
async def test_transactions_read_maps_biz_to_companion_uuid():
    rest, captured = _rest_with_capture()
    await rest.get_recent_transactions(BIZ, days=7)
    assert captured[0]["table"] == "transactions"
    assert captured[0]["org_id"] == f"eq.{COMPANION}"     # NOT the raw biz_ id
    assert COMPANION != BIZ


@aio
async def test_all_uuid_keyed_helpers_map_biz():
    rest, captured = _rest_with_capture()
    await rest.get_daily_revenue(BIZ)
    await rest.get_hourly_revenue(BIZ)
    await rest.get_product_performance(BIZ)
    await rest.get_products(BIZ)
    await rest.get_transaction_details(BIZ)          # delegates to get_recent_transactions
    for c in captured:
        assert c["org_id"] == f"eq.{COMPANION}", c


@aio
async def test_uuid_org_passes_through_unchanged():
    # A native-uuid org (organizations case) must not be re-mapped.
    rest, captured = _rest_with_capture()
    uuid_org = "11111111-2222-4333-8444-555566667777"
    await rest.get_recent_transactions(uuid_org)
    assert captured[0]["org_id"] == f"eq.{uuid_org}"
