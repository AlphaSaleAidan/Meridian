"""
CPA Handoff API Routes — Taxes & Expenses (user-facing label "Taxes & Expenses";
the backend path stays /api/cpa, the exported packet is titled "CPA Handoff").

This is a tax-paperwork PREPARATION tool. It organizes a merchant's existing
POS/phone-order numbers (revenue, sales tax collected) plus merchant-entered
expenses AND bank/card transactions (the "Connect your business bank account"
feed) into a clean, CPA-ready summary, CSV, and printable HTML report. Meridian
does NOT calculate income tax, file returns, or give tax advice.

Routes (all org-scoped; router-level require_org_access fires on ?org_id=):
  GET    /api/cpa/summary             → revenue + sales tax + expenses + net + per-card
  GET    /api/cpa/expenses            → list merchant-entered expenses
  POST   /api/cpa/expenses            → add an expense
  DELETE /api/cpa/expenses/{id}       → delete an expense
  GET    /api/cpa/export.csv          → CSV packet (stdlib csv)
  GET    /api/cpa/export.html         → printable HTML packet (zero-dep)
  POST   /api/cpa/bank/link-token     → Plaid Link token (synthetic in demo)
  POST   /api/cpa/bank/connect        → exchange public_token → connection → sync
  GET    /api/cpa/bank/connections    → list connected banks
  GET    /api/cpa/bank/transactions   → list card transactions (filter by card_last4)
  POST   /api/cpa/bank/sync           → pull + upsert transactions
"""
import csv
import io
import logging
import re
from datetime import date, datetime, timezone
from html import escape
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from ..auth import require_org_access
from ...db.cache import dashboard_cache, TTL_FAST
from ...integrations import bank_provider

logger = logging.getLogger("meridian.api.cpa")

router = APIRouter(
    prefix="/api/cpa",
    tags=["cpa"],
    dependencies=[Depends(require_org_access)],
)

# ─── Disclaimer (single source of truth — byte-identical to the design doc and
#     the frontend CPA_DISCLAIMER constant) ──────────────────────────────────
CPA_DISCLAIMER = (
    "We prepare, your CPA files. Meridian organizes your sales and expense records into\n"
    "a CPA-ready summary. These figures are a starting point for your accountant — Meridian\n"
    "does not calculate income tax, file returns, or provide tax advice. Confirm all numbers\n"
    "with your CPA before filing."
)

CURRENT_YEAR = datetime.now(timezone.utc).year

EXPENSE_CATEGORIES = {
    "supplies", "cogs", "rent", "utilities", "payroll",
    "marketing", "equipment", "fees", "other",
}

# Owner-readable labels for each expense category (used in the by-category
# breakdown that the summary, CSV, and printable report all share).
CATEGORY_LABELS = {
    "supplies": "Supplies", "cogs": "Cost of goods", "rent": "Rent",
    "utilities": "Utilities", "payroll": "Payroll", "marketing": "Marketing",
    "equipment": "Equipment", "fees": "Fees", "other": "Other",
}

# Bank-transaction debits in this category are NOT counted as deductible expenses
# (account transfers / settlements / refunds are not spend).
NON_EXPENSE_TXN_CATEGORY = "transfer"


# ─── Shared helpers copied from dashboard.py (do not re-derive) ──────────────

_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def _validate_org_id(org_id: str = Query(..., description="Organization ID")) -> str:
    if not _UUID_RE.match(org_id) and not org_id.startswith('biz_'):
        raise HTTPException(422, "org_id must be a valid UUID or business ID")
    return org_id


OrgId = Annotated[str, Depends(_validate_org_id)]


def _get_db():
    from ...db import _db_instance
    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


def _sanitize_text(v: str) -> str:
    """Strip HTML tags and dangerous characters from user input (mirrors canada.py)."""
    v = re.sub(r'<[^>]+>', '', v)
    v = v.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#x27;')
    return v.strip()


_YEAR = Query(default=CURRENT_YEAR, ge=2020, le=2100, description="Calendar year")


# ─── Core data assembly (shared by summary + exports) ────────────────────────

async def _load_year_data(db, org_id: str, year: int) -> dict:
    """Fetch + reduce all the numbers for one org-year.

    Revenue + sales tax come from phone_orders (merchant_id == org_id), expenses
    from cpa_expenses, and card debits from cpa_transactions. Returns the fully
    computed structure the summary/CSV/HTML all render from.
    """
    start = f"{year}-01-01T00:00:00Z"
    end = f"{year + 1}-01-01T00:00:00Z"

    # phone_orders: PostgREST can't carry two created_at filters in one dict, so
    # pass the gte bound and drop rows >= end in Python (same idiom dashboard.py
    # uses for ranged created_at — see transactions/day).
    orders = await db.select(
        "phone_orders",
        filters={"merchant_id": f"eq.{org_id}", "created_at": f"gte.{start}"},
        order="created_at.asc",
        limit=50000,
    )
    orders = [o for o in orders if (o.get("created_at") or "") < end]

    expenses = await db.select(
        "cpa_expenses",
        filters={"org_id": f"eq.{org_id}", "expense_date": f"gte.{year}-01-01"},
        order="expense_date.asc",
        limit=10000,
    )
    expenses = [e for e in expenses if (e.get("expense_date") or "") <= f"{year}-12-31"]

    transactions = await db.select(
        "cpa_transactions",
        filters={"org_id": f"eq.{org_id}", "posted_date": f"gte.{year}-01-01"},
        order="posted_date.asc",
        limit=50000,
    )
    transactions = [t for t in transactions if (t.get("posted_date") or "") <= f"{year}-12-31"]

    revenue_cents = sum(round(float(o.get("total", 0) or 0) * 100) for o in orders)
    sales_tax_cents = sum(round(float(o.get("tax", 0) or 0) * 100) for o in orders)
    order_count = len(orders)

    manual_expense_cents = sum(int(e.get("amount_cents", 0) or 0) for e in expenses)

    # Deductible debits = card debits that aren't transfers/settlements.
    debit_expense_cents = sum(
        int(t.get("amount_cents", 0) or 0)
        for t in transactions
        if t.get("direction") == "debit" and (t.get("category") or "") != NON_EXPENSE_TXN_CATEGORY
    )

    expenses_total_cents = manual_expense_cents + debit_expense_cents
    net_cents = revenue_cents - expenses_total_cents

    # ── Monthly buckets (Jan..Dec, zero-filled) ──
    monthly = {
        f"{year}-{m:02d}": {
            "month": f"{year}-{m:02d}",
            "revenue_cents": 0,
            "sales_tax_collected_cents": 0,
            "order_count": 0,
            "expenses_total_cents": 0,
        }
        for m in range(1, 13)
    }
    for o in orders:
        key = (o.get("created_at") or "")[:7]
        if key in monthly:
            monthly[key]["revenue_cents"] += round(float(o.get("total", 0) or 0) * 100)
            monthly[key]["sales_tax_collected_cents"] += round(float(o.get("tax", 0) or 0) * 100)
            monthly[key]["order_count"] += 1
    for e in expenses:
        key = (e.get("expense_date") or "")[:7]
        if key in monthly:
            monthly[key]["expenses_total_cents"] += int(e.get("amount_cents", 0) or 0)
    for t in transactions:
        if t.get("direction") != "debit" or (t.get("category") or "") == NON_EXPENSE_TXN_CATEGORY:
            continue
        key = (t.get("posted_date") or "")[:7]
        if key in monthly:
            monthly[key]["expenses_total_cents"] += int(t.get("amount_cents", 0) or 0)
    monthly_list = [monthly[f"{year}-{m:02d}"] for m in range(1, 13)]

    # ── Per-card debit breakdown ──
    cards: dict[str, dict] = {}
    for t in transactions:
        if t.get("direction") != "debit":
            continue
        last4 = t.get("card_last4") or "????"
        c = cards.setdefault(last4, {"card_last4": last4, "total_cents": 0, "txn_count": 0})
        c["total_cents"] += int(t.get("amount_cents", 0) or 0)
        c["txn_count"] += 1
    cards_list = sorted(cards.values(), key=lambda c: c["total_cents"], reverse=True)

    # ── Deductible spend by category (the owner-readable "where the money went")
    # Combines manual expenses + card debits (excluding transfers). This is the
    # same number set the expenses_total is built from, just sliced by category so
    # an owner can see their biggest deductible costs at a glance.
    by_cat: dict[str, int] = {}
    for e in expenses:
        cat = (e.get("category") or "other")
        by_cat[cat] = by_cat.get(cat, 0) + int(e.get("amount_cents", 0) or 0)
    for t in transactions:
        if t.get("direction") != "debit":
            continue
        cat = (t.get("category") or "other")
        if cat == NON_EXPENSE_TXN_CATEGORY:
            continue
        by_cat[cat] = by_cat.get(cat, 0) + int(t.get("amount_cents", 0) or 0)
    cat_total = sum(by_cat.values()) or 1
    by_category = [
        {
            "category": cat,
            "label": CATEGORY_LABELS.get(cat, cat.title()),
            "amount_cents": cents,
            "pct": round(cents * 100 / cat_total, 1),
        }
        for cat, cents in sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)
        if cents > 0
    ]

    return {
        "orders": orders,
        "expenses": expenses,
        "transactions": transactions,
        "revenue_cents": revenue_cents,
        "sales_tax_collected_cents": sales_tax_cents,
        "order_count": order_count,
        "expenses_total_cents": expenses_total_cents,
        "manual_expense_cents": manual_expense_cents,
        "debit_expense_cents": debit_expense_cents,
        "net_cents": net_cents,
        "monthly": monthly_list,
        "cards": cards_list,
        "by_category": by_category,
    }


# ─── GET /summary ────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_summary(
    org_id: OrgId,
    year: int = _YEAR,
    db=Depends(_get_db),
):
    """Read-only tax summary: revenue, sales tax collected, expenses (manual +
    card debits), net, monthly breakdown, and a per-card debit breakdown."""
    cache_key = dashboard_cache.make_key("cpa_summary", org_id, year=year)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    d = await _load_year_data(db, org_id, year)
    result = {
        "org_id": org_id,
        "year": year,
        "currency": "CAD",
        "revenue_cents": d["revenue_cents"],
        "sales_tax_collected_cents": d["sales_tax_collected_cents"],
        "order_count": d["order_count"],
        "expenses_total_cents": d["expenses_total_cents"],
        "net_cents": d["net_cents"],
        "monthly": d["monthly"],
        "cards": d["cards"],
        "by_category": d["by_category"],
        "disclaimer": CPA_DISCLAIMER,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Expenses CRUD ───────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    org_id: str
    expense_date: str
    category: str
    vendor: str
    amount_cents: int
    note: str | None = None

    @field_validator("expense_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("expense_date must be YYYY-MM-DD")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(EXPENSE_CATEGORIES)}")
        return v

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: str) -> str:
        v = _sanitize_text(v)
        if not 1 <= len(v) <= 120:
            raise ValueError("vendor must be 1..120 chars")
        return v

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not 0 < v <= 100_000_000:
            raise ValueError("amount_cents must be > 0 and <= 100000000")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = _sanitize_text(v)
        if len(v) > 500:
            raise ValueError("note must be <= 500 chars")
        return v


def _expense_view(e: dict) -> dict:
    return {
        "id": e.get("id"),
        "expense_date": e.get("expense_date"),
        "category": e.get("category"),
        "vendor": e.get("vendor"),
        "amount_cents": e.get("amount_cents"),
        "note": e.get("note"),
    }


@router.get("/expenses")
async def list_expenses(
    org_id: OrgId,
    year: int = _YEAR,
    db=Depends(_get_db),
):
    """List merchant-entered expenses for a calendar year."""
    rows = await db.select(
        "cpa_expenses",
        filters={"org_id": f"eq.{org_id}", "expense_date": f"gte.{year}-01-01"},
        order="expense_date.asc",
        limit=10000,
    )
    rows = [e for e in rows if (e.get("expense_date") or "") <= f"{year}-12-31"]
    return {"expenses": [_expense_view(e) for e in rows], "total": len(rows)}


@router.post("/expenses")
async def create_expense(
    org_id: OrgId,
    req: ExpenseCreate = Body(...),
    db=Depends(_get_db),
):
    """Add an expense. The verified org_id (query param) wins over the body so a
    caller can never write into another org by spoofing the body field."""
    row = {
        "org_id": org_id,
        "expense_date": req.expense_date,
        "category": req.category,
        "vendor": req.vendor,
        "amount_cents": req.amount_cents,
        "note": req.note,
    }
    created = await db.insert("cpa_expenses", row)
    dashboard_cache.invalidate_org(org_id)
    expense = created[0] if isinstance(created, list) and created else created
    return {"expense": _expense_view(expense) if isinstance(expense, dict) else expense}


@router.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    org_id: OrgId,
    db=Depends(_get_db),
):
    """Delete one expense. The org_id filter guarantees a caller can only delete
    their own org's rows even if they guess another org's expense_id."""
    if not _UUID_RE.match(expense_id):
        raise HTTPException(400, "Invalid expense_id format")
    await db.delete(
        "cpa_expenses",
        filters={"id": f"eq.{expense_id}", "org_id": f"eq.{org_id}"},
    )
    dashboard_cache.invalidate_org(org_id)
    return {"ok": True, "expense_id": expense_id}


# ─── Exports: CSV + printable HTML ───────────────────────────────────────────

def _dollars(cents) -> str:
    return f"{(int(cents or 0)) / 100:.2f}"


@router.get("/export.csv")
async def export_csv(
    org_id: OrgId,
    year: int = _YEAR,
    db=Depends(_get_db),
):
    """CPA Handoff packet as CSV (stdlib csv)."""
    d = await _load_year_data(db, org_id, year)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Meridian CPA Handoff", f"Year {year}", "Currency CAD"])
    w.writerow([CPA_DISCLAIMER])
    w.writerow([])
    w.writerow(["Summary"])
    w.writerow(["Revenue", _dollars(d["revenue_cents"])])
    w.writerow(["Sales tax collected", _dollars(d["sales_tax_collected_cents"])])
    w.writerow(["Order count", d["order_count"]])
    w.writerow(["Expenses total", _dollars(d["expenses_total_cents"])])
    w.writerow(["Net (revenue - expenses)", _dollars(d["net_cents"])])
    w.writerow([])
    w.writerow(["Monthly breakdown"])
    w.writerow(["Month", "Revenue", "Sales tax collected", "Orders", "Expenses"])
    for m in d["monthly"]:
        w.writerow([
            m["month"], _dollars(m["revenue_cents"]),
            _dollars(m["sales_tax_collected_cents"]), m["order_count"],
            _dollars(m["expenses_total_cents"]),
        ])
    w.writerow([])
    w.writerow(["Deductible spend by category"])
    w.writerow(["Category", "Amount", "% of spend"])
    for c in d["by_category"]:
        w.writerow([c["label"], _dollars(c["amount_cents"]), f"{c['pct']}%"])
    w.writerow([])
    w.writerow(["Per-card spend (card debits)"])
    w.writerow(["Card", "Total spend", "Transactions"])
    for c in d["cards"]:
        w.writerow([f"•••• {c['card_last4']}", _dollars(c["total_cents"]), c["txn_count"]])
    w.writerow([])
    w.writerow(["Expenses detail"])
    w.writerow(["Date", "Category", "Vendor", "Amount", "Note"])
    for e in d["expenses"]:
        w.writerow([
            e.get("expense_date"), e.get("category"), e.get("vendor"),
            _dollars(e.get("amount_cents")), e.get("note") or "",
        ])
    w.writerow([])
    w.writerow(["Bank/card transactions detail"])
    w.writerow(["Date", "Card", "Direction", "Merchant", "Category", "Amount"])
    for t in d["transactions"]:
        w.writerow([
            t.get("posted_date"), t.get("card_last4") or "",
            t.get("direction"), t.get("merchant_name") or "",
            t.get("category") or "", _dollars(t.get("amount_cents")),
        ])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="meridian-cpa-{year}.csv"'},
    )


def _category_lead(d: dict) -> str:
    """Plain-English one-liner so a business owner — not just a CPA — instantly
    reads the breakdown: total deductible spend + the single biggest category."""
    cats = d.get("by_category") or []
    total = d.get("expenses_total_cents", 0)
    if not cats or total <= 0:
        return "<p class='lead'>No deductible expenses recorded yet for this year.</p>"
    top = cats[0]
    return (
        f"<p class='lead'>You recorded <b>${_dollars(total)}</b> in deductible "
        f"business spending. Your biggest cost was <b>{escape(top['label'])}</b> at "
        f"${_dollars(top['amount_cents'])} ({top['pct']}% of all spend). Every dollar "
        f"here lowers the income your CPA reports.</p>"
    )


def _build_html(org_id: str, year: int, d: dict) -> str:
    """Self-contained printable HTML packet (zero-dep; merchant uses Save-as-PDF)."""
    def rows_monthly() -> str:
        return "".join(
            f"<tr><td>{escape(m['month'])}</td><td class='r'>${_dollars(m['revenue_cents'])}</td>"
            f"<td class='r'>${_dollars(m['sales_tax_collected_cents'])}</td>"
            f"<td class='r'>{m['order_count']}</td>"
            f"<td class='r'>${_dollars(m['expenses_total_cents'])}</td></tr>"
            for m in d["monthly"]
        )

    def rows_category() -> str:
        if not d["by_category"]:
            return "<tr><td colspan='3' class='muted'>No expenses recorded.</td></tr>"
        out = []
        for c in d["by_category"]:
            pct = c["pct"]
            out.append(
                f"<tr><td>{escape(c['label'])}</td>"
                f"<td class='r'>${_dollars(c['amount_cents'])}</td>"
                f"<td><div class='bar'><span style='width:{pct}%'></span></div>"
                f"<span class='pct'>{pct}%</span></td></tr>"
            )
        return "".join(out)

    def rows_cards() -> str:
        if not d["cards"]:
            return "<tr><td colspan='3' class='muted'>No connected cards.</td></tr>"
        return "".join(
            f"<tr><td>•••• {escape(c['card_last4'])}</td>"
            f"<td class='r'>${_dollars(c['total_cents'])}</td>"
            f"<td class='r'>{c['txn_count']}</td></tr>"
            for c in d["cards"]
        )

    def rows_expenses() -> str:
        if not d["expenses"]:
            return "<tr><td colspan='5' class='muted'>No expenses entered.</td></tr>"
        return "".join(
            f"<tr><td>{escape(str(e.get('expense_date') or ''))}</td>"
            f"<td>{escape(str(e.get('category') or ''))}</td>"
            f"<td>{escape(str(e.get('vendor') or ''))}</td>"
            f"<td class='r'>${_dollars(e.get('amount_cents'))}</td>"
            f"<td>{escape(str(e.get('note') or ''))}</td></tr>"
            for e in d["expenses"]
        )

    def rows_txns() -> str:
        if not d["transactions"]:
            return "<tr><td colspan='6' class='muted'>No bank/card transactions.</td></tr>"
        return "".join(
            f"<tr><td>{escape(str(t.get('posted_date') or ''))}</td>"
            f"<td>•••• {escape(str(t.get('card_last4') or ''))}</td>"
            f"<td>{escape(str(t.get('direction') or ''))}</td>"
            f"<td>{escape(str(t.get('merchant_name') or ''))}</td>"
            f"<td>{escape(str(t.get('category') or ''))}</td>"
            f"<td class='r'>${_dollars(t.get('amount_cents'))}</td></tr>"
            for t in d["transactions"]
        )

    disclaimer_html = escape(CPA_DISCLAIMER).replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meridian CPA Handoff — {year}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         color: #14213d; margin: 0; padding: 32px; background: #fff; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 28px 0 8px; border-bottom: 2px solid #14213d; padding-bottom: 4px; }}
  .sub {{ color: #5b6478; font-size: 13px; margin-bottom: 18px; }}
  .disclaimer {{ border: 1px solid #c9a227; background: #fdf8e7; padding: 12px 14px;
                border-radius: 6px; font-size: 12px; line-height: 1.5; margin: 16px 0; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-bottom: 8px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e6ee; }}
  th {{ background: #f4f6fb; font-weight: 600; }}
  td.r, th.r {{ text-align: right; }}
  .muted {{ color: #8a93a6; font-style: italic; }}
  .summary td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
  .bar {{ display: inline-block; width: 140px; height: 9px; background: #eef0f6;
         border-radius: 5px; overflow: hidden; vertical-align: middle; margin-right: 8px; }}
  .bar span {{ display: block; height: 100%; background: #1a8fd6; border-radius: 5px; }}
  .pct {{ font-size: 12px; color: #5b6478; font-variant-numeric: tabular-nums; }}
  .lead {{ font-size: 13px; color: #14213d; margin: 4px 0 14px; line-height: 1.55; }}
  .lead b {{ color: #1a8fd6; }}
  @media print {{
    body {{ padding: 0; }}
    h2 {{ page-break-after: avoid; }}
    tr {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
  <h1>CPA Handoff</h1>
  <div class="sub">Meridian · Tax year {year} · Currency CAD</div>
  <div class="disclaimer">{disclaimer_html}</div>

  <h2>Summary</h2>
  <table class="summary">
    <tr><td>Revenue</td><td>${_dollars(d['revenue_cents'])}</td></tr>
    <tr><td>Sales tax collected</td><td>${_dollars(d['sales_tax_collected_cents'])}</td></tr>
    <tr><td>Order count</td><td>{d['order_count']}</td></tr>
    <tr><td>Expenses total</td><td>${_dollars(d['expenses_total_cents'])}</td></tr>
    <tr><td>Net (revenue − expenses)</td><td>${_dollars(d['net_cents'])}</td></tr>
  </table>

  <h2>Where your money went — deductible spend by category</h2>
  {_category_lead(d)}
  <table>
    <tr><th>Category</th><th class="r">Amount</th><th>Share of spend</th></tr>
    {rows_category()}
  </table>

  <h2>Monthly breakdown</h2>
  <table>
    <tr><th>Month</th><th class="r">Revenue</th><th class="r">Sales tax</th>
        <th class="r">Orders</th><th class="r">Expenses</th></tr>
    {rows_monthly()}
  </table>

  <h2>Per-card spend</h2>
  <table>
    <tr><th>Card</th><th class="r">Total spend</th><th class="r">Transactions</th></tr>
    {rows_cards()}
  </table>

  <h2>Expenses detail</h2>
  <table>
    <tr><th>Date</th><th>Category</th><th>Vendor</th><th class="r">Amount</th><th>Note</th></tr>
    {rows_expenses()}
  </table>

  <h2>Bank/card transactions detail</h2>
  <table>
    <tr><th>Date</th><th>Card</th><th>Direction</th><th>Merchant</th><th>Category</th><th class="r">Amount</th></tr>
    {rows_txns()}
  </table>
</body>
</html>"""


@router.get("/export.html")
async def export_html(
    org_id: OrgId,
    year: int = _YEAR,
    db=Depends(_get_db),
):
    """CPA Handoff packet as a self-contained printable HTML document (no PDF lib)."""
    d = await _load_year_data(db, org_id, year)
    html = _build_html(org_id, year, d)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="meridian-cpa-{year}.html"'},
    )


# ─── Bank connections + transactions (the expense feed) ──────────────────────

def _connection_view(c: dict) -> dict:
    # Never surface access_ref / item_id (the provider secret refs) to the client.
    return {
        "id": c.get("id"),
        "provider": c.get("provider"),
        "institution_name": c.get("institution_name"),
        "status": c.get("status"),
        "created_at": c.get("created_at"),
    }


def _txn_view(t: dict) -> dict:
    return {
        "id": t.get("id"),
        "connection_id": t.get("connection_id"),
        "account_id": t.get("account_id"),
        "card_last4": t.get("card_last4"),
        "account_label": t.get("account_label"),
        "posted_date": t.get("posted_date"),
        "amount_cents": t.get("amount_cents"),
        "direction": t.get("direction"),
        "merchant_name": t.get("merchant_name"),
        "category": t.get("category"),
    }


async def _sync_connection(db, org_id: str, connection: dict, year: int) -> int:
    """Pull transactions for one connection over `year` and upsert them.

    Dedup is on (org_id, account_id, posted_date, amount_cents, merchant_name) — a
    stable natural key — backed in the DB by UNIQUE (connection_id, provider_txn_id)
    on cpa_transactions. We compute the natural key in Python (so the fake-db tests
    exercise it) and only insert rows we haven't seen. Returns NEW rows inserted."""
    access_ref = connection.get("access_ref") or ""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    fetched = await bank_provider.fetch_transactions(access_ref, start, end)

    existing = await db.select(
        "cpa_transactions",
        filters={"org_id": f"eq.{org_id}", "posted_date": f"gte.{year}-01-01"},
        limit=50000,
    )
    existing = [t for t in existing if (t.get("posted_date") or "") <= f"{year}-12-31"]
    seen = {
        (e.get("account_id"), e.get("posted_date"), e.get("amount_cents"), e.get("merchant_name"))
        for e in existing
    }

    new_rows = []
    for t in fetched:
        key = (t.get("account_id"), t.get("posted_date"), t.get("amount_cents"), t.get("merchant_name"))
        if key in seen:
            continue
        seen.add(key)
        new_rows.append({
            "org_id": org_id,
            "connection_id": connection.get("id"),
            "account_id": t.get("account_id"),
            "card_last4": t.get("card_last4"),
            "account_label": t.get("account_label"),
            "posted_date": t.get("posted_date"),
            "amount_cents": t.get("amount_cents"),
            "direction": t.get("direction"),
            "merchant_name": t.get("merchant_name"),
            "category": t.get("category") or "other",
            "provider_txn_id": t.get("provider_txn_id"),
            "raw_json": t.get("raw_json"),
        })

    if new_rows:
        await db.insert("cpa_transactions", new_rows)
        dashboard_cache.invalidate_org(org_id)
    return len(new_rows)


@router.post("/bank/link-token")
async def bank_link_token(org_id: OrgId):
    """Return a Plaid Link token for the frontend. Synthetic in demo mode."""
    token = await bank_provider.create_link_token(org_id)
    return {"link_token": token, "demo": not bank_provider.is_configured()}


class BankConnectRequest(BaseModel):
    org_id: str
    public_token: str
    institution_name: str | None = None


@router.post("/bank/connect")
async def bank_connect(
    org_id: OrgId,
    req: BankConnectRequest = Body(...),
    year: int = _YEAR,
    db=Depends(_get_db),
):
    """Exchange a Link public_token for an item_ref, persist the connection, and
    immediately sync transactions. In demo mode (no Plaid key) this seeds the
    synthetic transaction feed."""
    item_ref = await bank_provider.exchange_public_token(req.public_token)
    inst = _sanitize_text(req.institution_name) if req.institution_name else "Connected Bank"
    # Migration schema: secret ref lives in access_ref; provider item id in item_id;
    # status enum is connected|error|disconnected.
    row = {
        "org_id": org_id,
        "provider": "plaid" if bank_provider.is_configured() else "demo",
        "access_ref": item_ref,
        "item_id": item_ref,
        "institution_name": inst,
        "status": "connected",
    }
    created = await db.insert("cpa_bank_connections", row)
    connection = created[0] if isinstance(created, list) and created else created
    if not isinstance(connection, dict):
        raise HTTPException(500, "Bank connection could not be saved")

    synced = await _sync_connection(db, org_id, connection, year)
    return {
        "connection": _connection_view(connection),
        "synced_transactions": synced,
        "demo": not bank_provider.is_configured(),
    }


@router.get("/bank/connections")
async def bank_connections(
    org_id: OrgId,
    db=Depends(_get_db),
):
    """List the org's connected bank/card accounts."""
    rows = await db.select(
        "cpa_bank_connections",
        filters={"org_id": f"eq.{org_id}"},
        order="created_at.desc",
        limit=200,
    )
    return {"connections": [_connection_view(c) for c in rows], "total": len(rows)}


@router.get("/bank/transactions")
async def bank_transactions(
    org_id: OrgId,
    year: int = _YEAR,
    card_last4: str | None = Query(None, description="Filter to a single card's last 4"),
    db=Depends(_get_db),
):
    """List card transactions for a year, optionally filtered to one card."""
    filters = {"org_id": f"eq.{org_id}", "posted_date": f"gte.{year}-01-01"}
    if card_last4:
        filters["card_last4"] = f"eq.{card_last4}"
    rows = await db.select(
        "cpa_transactions",
        filters=filters,
        order="posted_date.asc",
        limit=50000,
    )
    rows = [t for t in rows if (t.get("posted_date") or "") <= f"{year}-12-31"]
    return {"transactions": [_txn_view(t) for t in rows], "total": len(rows)}


@router.post("/bank/sync")
async def bank_sync(
    org_id: OrgId,
    year: int = _YEAR,
    db=Depends(_get_db),
):
    """Re-pull transactions for every active connection and upsert new rows."""
    connections = await db.select(
        "cpa_bank_connections",
        filters={"org_id": f"eq.{org_id}", "status": "eq.connected"},
        limit=200,
    )
    total_new = 0
    for c in connections:
        total_new += await _sync_connection(db, org_id, c, year)
    return {
        "connections_synced": len(connections),
        "new_transactions": total_new,
        "demo": not bank_provider.is_configured(),
    }
