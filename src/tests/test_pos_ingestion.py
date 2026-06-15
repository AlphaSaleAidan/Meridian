"""
POS Ingestion Verification Harness — Square + Clover.

Proves the connect→read→normalize→digest pipeline actually intakes data and
lands normalized rows in the `transactions` shape. Two auto-selected tiers:

  • MOCK tier (default, ZERO credentials): stubs each client's `_request` HTTP
    chokepoint with canned API payloads, runs the REAL sync engines + mappers,
    and asserts normalized transactions are produced. Proves the digest logic
    with no network/keys.

  • SANDBOX tier (auto-on when creds present): runs the real client against
    Square/Clover sandbox. Set SQUARE_ACCESS_TOKEN (+ SQUARE_ENVIRONMENT=sandbox)
    and/or CLOVER_ACCESS_TOKEN + CLOVER_MERCHANT_ID. Proves the keys read live data.

Run:  uv run python -m src.tests.test_pos_ingestion
Exit: 0 = all ran tiers PASS, 1 = any FAIL.
"""
import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("test_pos_ingestion")

# A "digested" transaction must carry the economic essentials. Field NAMES differ
# between the Square and Clover mappers (a known schema divergence we also flag),
# so the check is tolerant: identifier + money + a timestamp + payment method.
TS_FIELDS = ("transaction_at", "transaction_time", "created_at")
ID_FIELDS = ("external_id", "id")


# ─────────────────────────── Fixtures ───────────────────────────
SQUARE_LOCATION = {
    "id": "LOC1", "name": "Test Cafe (Sandbox)", "status": "ACTIVE",
    "currency": "CAD", "country": "CA", "timezone": "America/Toronto",
    "address": {"address_line_1": "1 King St W", "locality": "Toronto", "administrative_district_level_1": "ON"},
}

def _sq_order(oid: str, total: int) -> dict:
    return {
        "id": oid, "location_id": "LOC1", "state": "COMPLETED",
        "created_at": "2026-06-10T15:04:00Z",
        "total_money": {"amount": total, "currency": "CAD"},
        "total_tax_money": {"amount": int(total * 0.08), "currency": "CAD"},
        "total_tip_money": {"amount": 200, "currency": "CAD"},
        "total_discount_money": {"amount": 0, "currency": "CAD"},
        "tenders": [{"type": "CARD", "employee_id": "EMP1"}],
        "line_items": [
            {"uid": "li1", "name": "Latte", "quantity": "2",
             "base_price_money": {"amount": 550, "currency": "CAD"},
             "total_money": {"amount": 1100, "currency": "CAD"}},
        ],
    }

SQUARE_FIXTURES = {
    "locations": {"locations": [SQUARE_LOCATION]},
    "merchant": {"merchant": {"id": "MERCH_SQ", "country": "CA", "currency": "CAD", "business_name": "Test Cafe"}},
    "orders": {"orders": [_sq_order("SQORDER1", 1299), _sq_order("SQORDER2", 2450)]},
    "catalog": {"objects": []},
    "team": {"team_members": []},
    "inventory": {"counts": []},
}

CLOVER_MERCHANT = {"id": "MERCH_CL", "name": "Test Shop (Sandbox)", "defaultCurrency": "CAD"}

def _cl_order(oid: str, total: int) -> dict:
    return {
        "id": oid, "total": total, "state": "paid",
        "clientCreatedTime": 1749567840000, "createdTime": 1749567840000,
        "employee": {"id": "E1"},
        "payments": {"elements": [{"id": "P_" + oid, "amount": total, "result": "SUCCESS",
                                   "tender": {"label": "Credit Card", "labelKey": "com.clover.tender.credit_card"}}]},
        "lineItems": {"elements": [{"id": "L_" + oid, "name": "Drip Coffee", "price": total}]},
    }

CLOVER_FIXTURES = {
    "merchant": CLOVER_MERCHANT,
    "orders": {"elements": [_cl_order("CLORDER1", 1500), _cl_order("CLORDER2", 875)]},
    "categories": {"elements": [{"id": "C1", "name": "Beverages", "sortOrder": 0}]},
    "items": {"elements": [{"id": "I1", "name": "Drip Coffee", "price": 300, "categories": {"elements": [{"id": "C1", "name": "Beverages"}]}}]},
    "employees": {"elements": [{"id": "E1", "name": "Alex Staff"}]},
    "stocks": {"elements": []},
    "payments": {"elements": []},
}


# ─────────────────────────── Stubs ───────────────────────────
def _stub_square(client):
    """Replace SquareClient._request with a path-routed fixture responder."""
    async def _request(method, path, json=None, params=None, **kw):
        p = path.lower()
        if "/locations" in p: return SQUARE_FIXTURES["locations"]
        if "/merchants" in p: return SQUARE_FIXTURES["merchant"]
        if "/orders/search" in p: return SQUARE_FIXTURES["orders"]   # no "cursor" → one page
        if "/catalog" in p: return SQUARE_FIXTURES["catalog"]
        if "/team-members" in p: return SQUARE_FIXTURES["team"]
        if "/inventory" in p: return SQUARE_FIXTURES["inventory"]
        return {}
    client._request = _request


def _stub_clover(client):
    """Replace CloverClient._request with a path-routed fixture responder.
    Returns each list fixture once, then empty pages so _paginate terminates."""
    seen: set[str] = set()
    def _key(p):
        for k in ("orders", "categories", "item_stocks", "items", "employees", "payments"):
            if k in p: return k
        return "merchant"

    async def _request(method, path, params=None, json=None, **kw):
        p = path.lower()
        k = _key(p)
        if k == "merchant":
            return CLOVER_FIXTURES["merchant"]
        # paginated list endpoints: serve once, then empty
        fixture = {
            "orders": CLOVER_FIXTURES["orders"], "categories": CLOVER_FIXTURES["categories"],
            "items": CLOVER_FIXTURES["items"], "employees": CLOVER_FIXTURES["employees"],
            "item_stocks": CLOVER_FIXTURES["stocks"], "payments": CLOVER_FIXTURES["payments"],
        }[k]
        if k in seen:
            return {"elements": []}
        seen.add(k)
        return fixture
    client._request = _request


# ─────────────────────────── Assertions ───────────────────────────
def _first(d: dict, names: tuple) -> tuple[str | None, object]:
    for n in names:
        if d.get(n) not in (None, ""):
            return n, d[n]
    return None, None

def _check_txns(provider: str, txns: list[dict], items: list[dict] | None = None) -> tuple[bool, str]:
    if not txns:
        return False, "0 transactions produced (nothing ingested)"
    sample = txns[0]
    id_name, id_val = _first(sample, ID_FIELDS)
    ts_name, ts_val = _first(sample, TS_FIELDS)
    problems = []
    if id_val is None: problems.append("no identifier (external_id/id)")
    if ts_val is None: problems.append("no timestamp (transaction_at/transaction_time/created_at)")
    if sample.get("payment_method") in (None, ""): problems.append("no payment_method")
    if not all(isinstance(t.get("total_cents"), int) for t in txns):
        problems.append("non-int/missing total_cents")
    # Line items (transaction_items) persist with on_conflict="…,transaction_at",
    # so each must carry transaction_at + a transaction_id link.
    items = items or []
    li_note = ""
    if items:
        li = items[0]
        if li.get("transaction_at") in (None, ""): problems.append("line items missing transaction_at")
        if li.get("transaction_id") in (None, ""): problems.append("line items missing transaction_id")
        li_note = f" + {len(items)} line items"
    if problems:
        return False, f"{len(txns)} txns but: {'; '.join(problems)} · keys={sorted(sample)}"
    return True, (f"{len(txns)} transactions{li_note} digested · sample {id_val}="
                  f"{sample['total_cents']}¢ {sample['payment_method']} @ {ts_val} "
                  f"(ts field: {ts_name})")


# ─────────────────────────── Runners ───────────────────────────
async def run_square(tier: str) -> tuple[bool, str]:
    from src.square.client import SquareClient
    from src.square.sync_engine import SyncEngine
    token = os.getenv("SQUARE_ACCESS_TOKEN", "")
    client = SquareClient(access_token=token or "mock-sandbox-token")
    if tier == "mock":
        _stub_square(client)
    engine = SyncEngine(client, org_id="test-org", pos_connection_id="test-conn-sq")
    try:
        result = await engine.run_initial_backfill()
        return _check_txns("square", result.transactions, result.transaction_items)
    except Exception as e:
        return False, f"backfill raised: {type(e).__name__}: {e}"
    finally:
        await client.close()


async def run_clover(tier: str) -> tuple[bool, str]:
    from src.clover.client import CloverClient
    from src.clover.sync_engine import CloverSyncEngine
    token = os.getenv("CLOVER_ACCESS_TOKEN", "")
    mid = os.getenv("CLOVER_MERCHANT_ID", "")
    client = CloverClient(access_token=token or "mock-token", merchant_id=mid or "MERCH_CL")
    if tier == "mock":
        _stub_clover(client)
    engine = CloverSyncEngine(client, org_id="test-org", pos_connection_id="test-conn-cl")
    try:
        result = await engine.run_initial_backfill()
        return _check_txns("clover", result.transactions, result.transaction_items)
    except Exception as e:
        return False, f"backfill raised: {type(e).__name__}: {e}"
    finally:
        await client.close()


async def main() -> int:
    print("=" * 72)
    print("  POS INGESTION VERIFICATION  (Square + Clover)")
    print("=" * 72)
    results: dict[str, tuple[bool, str]] = {}

    sq_tier = "sandbox" if os.getenv("SQUARE_ACCESS_TOKEN") else "mock"
    cl_tier = "sandbox" if (os.getenv("CLOVER_ACCESS_TOKEN") and os.getenv("CLOVER_MERCHANT_ID")) else "mock"

    print(f"\n▶ Square  [{sq_tier} tier]")
    results["square"] = await run_square(sq_tier)
    ok, msg = results["square"]
    print(f"  {'✅ PASS' if ok else '❌ FAIL'} — {msg}")

    print(f"\n▶ Clover  [{cl_tier} tier]")
    results["clover"] = await run_clover(cl_tier)
    ok, msg = results["clover"]
    print(f"  {'✅ PASS' if ok else '❌ FAIL'} — {msg}")

    all_ok = all(ok for ok, _ in results.values())
    print("\n" + "=" * 72)
    print(f"  RESULT: {'✅ ALL PASS — data is being intaken & digested' if all_ok else '❌ FAILURES — see above'}")
    print(f"  (Square={sq_tier}, Clover={cl_tier}. Set *_ACCESS_TOKEN to exercise live sandbox.)")
    print("=" * 72)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
