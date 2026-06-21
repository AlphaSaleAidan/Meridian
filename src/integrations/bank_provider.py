"""
Bank/card transaction provider — thin Plaid REST abstraction for the CPA Handoff
expense feed ("Connect your business bank account").

ponytail: httpx REST only, NO plaid SDK. Plaid's product surface here is tiny
(link token → public-token exchange → transactions pull), so a heavy SDK earns
nothing. We hit the documented JSON endpoints directly:
    POST /link/token/create
    POST /item/public_token/exchange
    POST /transactions/get
at https://{PLAID_ENV or 'sandbox'}.plaid.com.

When Plaid is NOT configured (no PLAID_CLIENT_ID / PLAID_SECRET) every function
returns SYNTHETIC data so the demo "connect a bank" flow works with zero keys:
a demo link token, a synthetic item_ref, and ~25 plausible CAD debit/credit
transactions across two fake cards (last4 4821 & 9032).

No keys are ever hardcoded — credentials come from the environment at call time.
"""
from __future__ import annotations

import hashlib
import os
import random
from datetime import date, timedelta

import httpx

PLAID_TIMEOUT = 20.0

# Plausible Canadian small-business merchants for synthetic debits, mapped to the
# expense categories the CPA summary understands.
_SYNTHETIC_DEBIT_MERCHANTS = [
    ("Costco Wholesale", "supplies"),
    ("Sysco Canada", "cogs"),
    ("GFS Canada", "cogs"),
    ("Hydro One", "utilities"),
    ("Enbridge Gas", "utilities"),
    ("Bell Canada", "utilities"),
    ("Rogers Business", "utilities"),
    ("Staples Business", "supplies"),
    ("Uline Canada", "supplies"),
    ("Meta Ads", "marketing"),
    ("Google Ads", "marketing"),
    ("Square Fees", "fees"),
    ("Interac e-Transfer Fee", "fees"),
    ("City Property Mgmt", "rent"),
    ("Restaurant Depot", "cogs"),
    ("Home Depot", "equipment"),
]
_SYNTHETIC_CREDIT_SOURCES = ["Card Settlement Deposit", "Square Payout", "Customer Refund Reversal"]
_SYNTHETIC_CARDS = ["4821", "9032"]


def _plaid_env() -> str:
    return os.environ.get("PLAID_ENV", "sandbox").strip() or "sandbox"


def _plaid_base() -> str:
    return f"https://{_plaid_env()}.plaid.com"


def is_configured() -> bool:
    """True only when both Plaid credentials are present in the environment."""
    return bool(os.environ.get("PLAID_CLIENT_ID") and os.environ.get("PLAID_SECRET"))


def _creds() -> dict:
    return {
        "client_id": os.environ.get("PLAID_CLIENT_ID", ""),
        "secret": os.environ.get("PLAID_SECRET", ""),
    }


# ─── Synthetic generators (demo mode, no Plaid key) ──────────────────────────

def _synthetic_seed(item_ref: str) -> random.Random:
    """Deterministic RNG keyed on the item_ref so a given demo connection always
    produces the same transactions (stable across /bank/sync calls → dedup works)."""
    h = hashlib.md5(item_ref.encode()).hexdigest()
    return random.Random(int(h[:8], 16))


def synthetic_link_token() -> str:
    return "link-sandbox-demo-meridian-cpa"


def synthetic_item_ref() -> str:
    return "demo-item-" + hashlib.md5(b"meridian-cpa-demo").hexdigest()[:12]


def synthetic_transactions(item_ref: str, start: date, end: date, count: int = 25) -> list[dict]:
    """~25 plausible CAD debit/credit transactions across two fake cards.

    Shape matches the normalized dict that fetch_transactions returns (see below):
    {account_id, card_last4, posted_date, amount_cents, direction, merchant_name,
     category, raw_json}.
    """
    rng = _synthetic_seed(item_ref)
    span_days = max((end - start).days, 1)
    txns: list[dict] = []
    for i in range(count):
        card = _SYNTHETIC_CARDS[i % len(_SYNTHETIC_CARDS)]
        posted = start + timedelta(days=rng.randint(0, span_days))
        # ~1 in 6 rows is a credit (settlement/refund), the rest are debits.
        if i % 6 == 5:
            direction = "credit"
            merchant = rng.choice(_SYNTHETIC_CREDIT_SOURCES)
            category = "transfer"
            amount_cents = rng.randint(15000, 120000)
        else:
            direction = "debit"
            merchant, category = rng.choice(_SYNTHETIC_DEBIT_MERCHANTS)
            amount_cents = rng.randint(1200, 85000)
        txns.append({
            "account_id": f"acct_{card}",
            "card_last4": card,
            "account_label": f"Business Card •••• {card}",
            "posted_date": posted.isoformat(),
            "amount_cents": amount_cents,
            "direction": direction,
            "merchant_name": merchant,
            "category": category,
            # Stable per-item id so re-syncs dedup on (connection_id, provider_txn_id).
            "provider_txn_id": f"{item_ref}-{i:04d}",
            "raw_json": {"synthetic": True, "name": merchant},
        })
    txns.sort(key=lambda t: t["posted_date"])
    return txns


# ─── Plaid REST calls (live mode) ────────────────────────────────────────────

async def _plaid_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=PLAID_TIMEOUT) as client:
        resp = await client.post(
            f"{_plaid_base()}{path}",
            json={**_creds(), **payload},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def create_link_token(org_id: str) -> str:
    """Return a Plaid Link token the frontend uses to open Plaid Link.

    Demo (no key): a fixed sandbox link token so the UI can render the connect
    flow without a real Plaid project.
    """
    if not is_configured():
        return synthetic_link_token()
    data = await _plaid_post("/link/token/create", {
        "user": {"client_user_id": org_id},
        "client_name": "Meridian",
        "products": ["transactions"],
        "country_codes": ["CA", "US"],
        "language": "en",
    })
    return data.get("link_token", "")


async def exchange_public_token(public_token: str) -> str:
    """Exchange a Link public_token for a durable item reference (Plaid access token).

    Demo (no key): a synthetic item_ref so /bank/connect can persist a connection
    row and seed synthetic transactions.
    """
    if not is_configured():
        return synthetic_item_ref()
    data = await _plaid_post("/item/public_token/exchange", {"public_token": public_token})
    return data.get("access_token", "")


def _card_last4(account: dict) -> str:
    """Best-effort card/account last-4 from a Plaid account object."""
    mask = account.get("mask") or ""
    return str(mask)[-4:] if mask else ""


async def fetch_transactions(item_ref: str, start: date, end: date) -> list[dict]:
    """Return normalized transactions for an item over [start, end].

    Normalized dict:
      account_id, card_last4, posted_date (YYYY-MM-DD), amount_cents (positive int),
      direction ('debit'|'credit'), merchant_name, category, raw_json.

    Plaid sign convention: positive `amount` = money leaving the account (debit),
    negative = money in (credit). We normalize to a positive amount_cents +
    explicit direction so downstream code never juggles signs.

    Demo (no key, or a synthetic item_ref): synthetic transactions.
    """
    if not is_configured() or item_ref.startswith("demo-item-"):
        return synthetic_transactions(item_ref, start, end)

    data = await _plaid_post("/transactions/get", {
        "access_token": item_ref,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "options": {"count": 500, "offset": 0},
    })
    accounts = {a.get("account_id"): a for a in data.get("accounts", [])}
    out: list[dict] = []
    for t in data.get("transactions", []):
        amount = float(t.get("amount", 0) or 0)
        direction = "debit" if amount >= 0 else "credit"
        cats = t.get("category") or []
        acct = accounts.get(t.get("account_id"), {})
        out.append({
            "account_id": t.get("account_id", ""),
            "card_last4": _card_last4(acct),
            "account_label": acct.get("name") or acct.get("official_name") or "",
            "posted_date": (t.get("date") or "")[:10],
            "amount_cents": abs(round(amount * 100)),
            "direction": direction,
            "merchant_name": t.get("merchant_name") or t.get("name") or "",
            "category": (cats[0].lower() if cats else "other"),
            "provider_txn_id": t.get("transaction_id") or "",
            "raw_json": t,
        })
    return out
