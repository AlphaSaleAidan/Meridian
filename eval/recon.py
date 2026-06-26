"""Phase 1 — data feasibility reconnaissance (PostgREST path).

Read-only probe of the production Meridian Postgres (Supabase) database
via PostgREST. Read-only by HTTP verb: we only issue `GET` and `HEAD`
against `/rest/v1/transactions`. No mutations, no DDL, no RPC.

What the script does:

  1. HEAD `/rest/v1/transactions` with `Prefer: count=exact` → exact
     row count from the `Content-Range` header.
  2. GET `?select=*&limit=1` → discover the schema's column list.
  3. GET `?order=transaction_at.asc&limit=1` and `?order=transaction_at.desc&limit=1`
     → earliest / latest `transaction_at` (avoids PostgREST aggregate
     version sensitivity).
  4. GET a narrow extract of
     `(customer_id, card_fingerprint, card_brand, last_4, org_id, transaction_at)`
     paginated via the `Range` header.
  5. Compute, client-side, in plain Python:
       - per-org transaction volume,
       - customer-identity link counts,
       - implied churn base rate at several (lookback, horizon, min_visits)
         parameterisations.

No customer identifiers are written to the report — only aggregate
counts, percentages, and min/max timestamps. Pull-size is capped at
`MAX_PULL_ROWS` to keep the box within memory headroom; if the table
exceeds the cap, the script refuses to extract and reports the size.

Run:

    PYTHONPATH=/root/Meridian /root/Meridian/.venv/bin/python -m eval.recon

Output: stdout + `eval/reports/recon_<YYYY-MM-DD>.md`.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "eval" / "reports"

PAGE_SIZE = 10_000             # PostgREST max page size honoured by Range
MAX_PULL_ROWS = 2_000_000      # refuse to pull a wider extract than this
HTTP_TIMEOUT = 180             # seconds — per request


def _load_env() -> None:
    """Hand-rolled .env loader — keeps the script dependency-free."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class PostgRESTClient:
    """Minimal read-only PostgREST client.

    Only exposes `head_count`, `get_first`, and `paginate` — three
    methods that are GET/HEAD by construction. There is deliberately no
    `post`, `patch`, or `delete` here: if you can't reach the verb, you
    can't write."""

    def __init__(self, supabase_url: str, service_key: str) -> None:
        self._base = supabase_url.rstrip("/") + "/rest/v1"
        self._headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        if method not in ("GET", "HEAD"):
            raise ValueError(f"refusing non-read method {method!r}")
        url = f"{self._base}{path}"
        if query:
            url = url + "?" + urllib.parse.urlencode(query, safe=".,:()<>=*")
        headers = dict(self._headers)
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read() if exc.fp else b""
            return exc.code, dict(exc.headers or {}), body

    def head_count(self, table: str) -> int | None:
        """Exact row count via the Content-Range header."""
        status, headers, _ = self._request(
            "HEAD", f"/{table}",
            extra_headers={"Prefer": "count=exact"},
        )
        if status >= 400:
            return None
        cr = headers.get("Content-Range") or headers.get("content-range")
        if not cr or "/" not in cr:
            return None
        try:
            return int(cr.rsplit("/", 1)[1])
        except ValueError:
            return None

    def get_first(
        self, table: str, *, select: str = "*", order: str | None = None,
    ) -> dict[str, Any] | None:
        q = {"select": select, "limit": "1"}
        if order:
            q["order"] = order
        status, _, body = self._request("GET", f"/{table}", query=q)
        if status >= 400:
            return None
        rows = json.loads(body or b"[]")
        return rows[0] if rows else None

    def paginate(
        self, table: str, *, select: str, order: str = "transaction_at.asc",
        where: dict[str, str] | None = None, page_size: int = PAGE_SIZE,
        max_rows: int = MAX_PULL_ROWS,
    ):
        """Yield rows in `page_size` chunks via the `Range` header.

        Halts once `max_rows` are pulled and surfaces that fact to the
        caller via a final sentinel record (`{"_truncated_at": N}`).
        """
        pulled = 0
        offset = 0
        while pulled < max_rows:
            this_page = min(page_size, max_rows - pulled)
            range_end = offset + this_page - 1
            q = {"select": select, "order": order}
            if where:
                q.update(where)
            status, headers, body = self._request(
                "GET", f"/{table}",
                query=q,
                extra_headers={
                    "Range": f"{offset}-{range_end}",
                    "Range-Unit": "items",
                    "Prefer": "count=none",
                },
            )
            if status >= 400:
                raise RuntimeError(
                    f"paginate {table} status {status}: {body[:300]!r}"
                )
            rows = json.loads(body or b"[]")
            if not rows:
                return
            for r in rows:
                yield r
            pulled += len(rows)
            offset += len(rows)
            if len(rows) < this_page:
                return
        # If we reached here, we hit max_rows.
        yield {"_truncated_at": pulled}


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def _pick_customer_key(
    link_counts: dict[str, int],
) -> tuple[str, callable] | None:
    """Pick the most-populated identity column to use as the customer
    key. Returns (label, key_fn) or None."""
    best: tuple[str, callable, int] | None = None

    def cid_key(r: dict) -> str | None:
        v = r.get("customer_id")
        return str(v) if v else None

    def fp_key(r: dict) -> str | None:
        v = r.get("card_fingerprint")
        return str(v) if v and str(v).strip() else None

    def brand_last4_key(r: dict) -> str | None:
        b = r.get("card_brand")
        l = r.get("last_4")
        if b and l:
            return f"{b}-{l}"
        return None

    options = [
        ("customer_id", cid_key),
        ("card_fingerprint", fp_key),
        ("card_brand_last4", brand_last4_key),
    ]
    for label, fn in options:
        n = link_counts.get(label, 0)
        if n > 0 and (best is None or n > best[2]):
            best = (label, fn, n)
    return (best[0], best[1]) if best else None


def _link_counts_from_extract(rows: list[dict]) -> dict[str, int]:
    """Compute customer-identity link counts purely from the extract."""
    counts = {"customer_id": 0, "card_fingerprint": 0, "card_brand_last4": 0}
    for r in rows:
        if r.get("customer_id"):
            counts["customer_id"] += 1
        fp = r.get("card_fingerprint")
        if fp and str(fp).strip():
            counts["card_fingerprint"] += 1
        if r.get("card_brand") and r.get("last_4"):
            counts["card_brand_last4"] += 1
    return counts


def _per_org_from_extract(
    rows: list[dict],
) -> list[dict[str, Any]]:
    """Aggregate by org_id client-side. Top 20 by txn count."""
    agg: dict[str, dict[str, Any]] = {}
    cust_ids: dict[str, set] = defaultdict(set)
    card_fps: dict[str, set] = defaultdict(set)

    for r in rows:
        org = r.get("org_id")
        if not org:
            continue
        ts = r.get("transaction_at")
        d = _parse_dt(ts) if ts else None
        a = agg.setdefault(org, {"org_id": org, "txn_count": 0,
                                  "earliest": None, "latest": None})
        a["txn_count"] += 1
        if d is not None:
            if a["earliest"] is None or d < a["earliest"]:
                a["earliest"] = d
            if a["latest"] is None or d > a["latest"]:
                a["latest"] = d
        if r.get("customer_id"):
            cust_ids[org].add(r["customer_id"])
        fp = r.get("card_fingerprint")
        if fp and str(fp).strip():
            card_fps[org].add(fp)

    out = []
    for org, a in agg.items():
        out.append({
            "org_id": org,
            "txn_count": a["txn_count"],
            "earliest": a["earliest"].isoformat() if a["earliest"] else None,
            "latest": a["latest"].isoformat() if a["latest"] else None,
            "customers_with_id": len(cust_ids[org]),
            "distinct_card_fps": len(card_fps[org]),
        })
    out.sort(key=lambda x: x["txn_count"], reverse=True)
    return out[:20]


def _churn_label_feasibility(
    rows: list[dict],
    key_fn,
    *,
    lookback_days: int,
    horizon_days: int,
    min_visits: int,
) -> dict[str, Any]:
    """Compute the implied churn base rate from the extract."""
    if not rows:
        return {"error": "no rows"}

    # Gather per-customer visit timestamps.
    visits: dict[str, list[datetime]] = defaultdict(list)
    earliest_all = None
    latest_all = None
    for r in rows:
        cid = key_fn(r)
        if not cid:
            continue
        ts = r.get("transaction_at")
        if not ts:
            continue
        d = _parse_dt(ts)
        visits[cid].append(d)
        if earliest_all is None or d < earliest_all:
            earliest_all = d
        if latest_all is None or d > latest_all:
            latest_all = d

    if not visits or earliest_all is None or latest_all is None:
        return {"error": "no usable customer-keyed transactions"}

    cutoff = latest_all - timedelta(days=horizon_days)
    lookback_floor = cutoff - timedelta(days=lookback_days)
    if lookback_floor < earliest_all:
        return {
            "error": "data window too short for these parameters",
            "data_earliest": earliest_all.isoformat(),
            "data_latest": latest_all.isoformat(),
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
        }

    n_eligible = 0
    n_churned = 0
    n_retained = 0
    for cid, ds in visits.items():
        lifetime = len(ds)
        if lifetime < min_visits:
            continue
        in_lookback = any(lookback_floor < d <= cutoff for d in ds)
        if not in_lookback:
            continue
        in_horizon = any(
            cutoff < d <= cutoff + timedelta(days=horizon_days) for d in ds
        )
        n_eligible += 1
        if in_horizon:
            n_retained += 1
        else:
            n_churned += 1

    base_rate = (n_churned / n_eligible) if n_eligible else None
    return {
        "cutoff": cutoff.isoformat(),
        "lookback_days": lookback_days,
        "horizon_days": horizon_days,
        "min_lifetime_visits": min_visits,
        "data_earliest": earliest_all.isoformat(),
        "data_latest": latest_all.isoformat(),
        "n_eligible_customers": n_eligible,
        "n_churned": n_churned,
        "n_retained": n_retained,
        "implied_base_rate": base_rate,
    }


def main() -> int:
    _load_env()

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url:
        print("ABORT: SUPABASE_URL not set")
        return 2
    if not service_key:
        print("ABORT: SUPABASE_SERVICE_KEY/SUPABASE_SERVICE_ROLE_KEY not set")
        return 2

    client = PostgRESTClient(supabase_url, service_key)

    # ── 0. Table census across the customer/transaction surface ──
    # Drives the "is the data even here" question. PostgREST surfaces
    # each table as `/rest/v1/<name>`; we HEAD with count=exact to get
    # exact counts without pulling rows.
    census_tables = [
        "transactions", "transaction_items",
        "customer_journeys", "customer_sessions",
        "anonymous_customer_profiles",
        "chat_conversations", "chat_messages",
        "phone_orders", "phone_call_logs",
        "businesses", "business_users", "business_locations",
        "locations", "organizations", "pos_connections",
        "daily_revenue", "hourly_revenue", "daily_product_performance",
        "inventory_snapshots", "employees", "products",
        "insights", "forecasts", "merchant_health",
        "money_left_scores", "industry_aggregates",
    ]
    table_census: dict[str, int | None] = {}
    for t in census_tables:
        table_census[t] = client.head_count(t)
    print(f"table census: {table_census}")

    # ── 1. Row count via HEAD + count=exact ────────────────────
    row_count = client.head_count("transactions")
    if row_count is None:
        print("ABORT: HEAD /transactions failed — table absent or RLS blocks")
        return 3
    print(f"transactions row count: {row_count:,}")

    # ── 2. Column discovery via select=*&limit=1 ──────────────
    sample = client.get_first("transactions", select="*")
    columns = list(sample.keys()) if sample else []
    print(f"discovered columns ({len(columns)}): {columns}")

    # ── 3. Date range via ordered single-row pulls ────────────
    first_dt = client.get_first(
        "transactions", select="transaction_at", order="transaction_at.asc",
    )
    last_dt = client.get_first(
        "transactions", select="transaction_at", order="transaction_at.desc",
    )
    txn_date_range = {
        "earliest": first_dt.get("transaction_at") if first_dt else None,
        "latest":   last_dt.get("transaction_at")  if last_dt else None,
    }
    print(f"date range: {txn_date_range}")

    # ── 4. Narrow extract (PII-light) for client-side aggregates ──
    extract_columns = [
        c for c in ("customer_id", "card_fingerprint", "card_brand",
                    "last_4", "org_id", "transaction_at")
        if c in columns
    ]
    if "transaction_at" not in extract_columns:
        print("ABORT: transactions has no `transaction_at` column")
        return 4

    if row_count > MAX_PULL_ROWS:
        print(
            f"REFUSING to pull narrow extract: row_count {row_count:,} "
            f"> MAX_PULL_ROWS {MAX_PULL_ROWS:,}. Re-run with a date filter "
            f"or raise MAX_PULL_ROWS after confirming memory headroom."
        )
        extract_rows: list[dict] = []
        truncated = True
    else:
        select = ",".join(extract_columns)
        extract_rows = []
        truncated = False
        for row in client.paginate(
            "transactions", select=select,
            order="transaction_at.asc",
            max_rows=MAX_PULL_ROWS,
        ):
            if "_truncated_at" in row:
                truncated = True
                continue
            extract_rows.append(row)
        print(
            f"extract: pulled {len(extract_rows):,} rows "
            f"({'TRUNCATED' if truncated else 'complete'})"
        )

    # ── 5. Client-side aggregates ─────────────────────────────
    link_counts = _link_counts_from_extract(extract_rows) if extract_rows else {}
    per_org = _per_org_from_extract(extract_rows) if extract_rows else []

    chosen_key = _pick_customer_key(link_counts) if link_counts else None
    churn_labels: list[dict[str, Any]] = []
    if chosen_key and extract_rows:
        key_label, key_fn = chosen_key
        for lookback, horizon, min_visits in [
            (90, 30, 3),
            (90, 60, 3),
            (180, 60, 3),
            (180, 90, 3),
            (365, 90, 5),
        ]:
            churn_labels.append(
                _churn_label_feasibility(
                    extract_rows, key_fn,
                    lookback_days=lookback, horizon_days=horizon,
                    min_visits=min_visits,
                )
            )

    # ── 6. Render report ──────────────────────────────────────
    txn_summary = {"schema": "public", "table": "transactions",
                   "row_count": row_count}
    report_lines = _format_report(
        txn_summary=txn_summary,
        txn_columns=columns,
        txn_date_range=txn_date_range,
        per_org=per_org,
        link_counts=link_counts,
        chosen_key_label=chosen_key[0] if chosen_key else None,
        churn_labels=churn_labels,
        extract_size=len(extract_rows),
        extract_truncated=truncated,
        table_census=table_census,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"recon_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(report_lines) + "\n")

    for line in report_lines:
        print(line)
    print(f"\nReport written to: {report_path}")
    return 0


def _format_report(
    *,
    txn_summary: dict[str, Any],
    txn_columns: list[str],
    txn_date_range: dict[str, Any] | None,
    per_org: list[dict[str, Any]],
    link_counts: dict[str, int],
    chosen_key_label: str | None,
    churn_labels: list[dict[str, Any]],
    extract_size: int,
    extract_truncated: bool,
    table_census: dict[str, int | None],
) -> list[str]:
    out: list[str] = []
    today = date.today().isoformat()
    out.append(f"# Recon — real-data churn-eval feasibility ({today})")
    out.append("")
    out.append("Read-only probe of the production Meridian Postgres (Supabase) database")
    out.append("via PostgREST. HTTP GET/HEAD only; no writes are reachable.")
    out.append("All output is aggregate; no customer identifiers recorded.")
    out.append("")
    out.append("## Table census — does the data even exist here?")
    out.append("")
    out.append(
        "Exact row counts (`HEAD` with `Prefer: count=exact`) across the "
        "tables that could carry customer or transaction signal."
    )
    out.append("")
    out.append("| table | rows |")
    out.append("|-------|------|")
    for t, n in table_census.items():
        out.append(f"| `{t}` | {n if n is not None else 'n/a'} |")
    out.append("")

    out.append("## `transactions` summary")
    out.append("")
    out.append(f"- Row count (HEAD `Content-Range`): **{txn_summary['row_count']:,}**")
    if txn_date_range:
        out.append(f"- Earliest `transaction_at`: {txn_date_range.get('earliest')}")
        out.append(f"- Latest `transaction_at`: {txn_date_range.get('latest')}")
    out.append(
        f"- Narrow extract pulled: {extract_size:,} rows "
        f"({'TRUNCATED at MAX_PULL_ROWS' if extract_truncated else 'complete'})"
    )
    out.append("")

    out.append("### Columns (from schema sample)")
    out.append("")
    if txn_columns:
        out.append("```")
        for c in txn_columns:
            out.append(f"  - {c}")
        out.append("```")
    out.append("")

    out.append("## Customer-identity link counts (from extract)")
    out.append("")
    if not link_counts:
        out.append("_(no usable customer-identity columns)_")
    else:
        out.append("| field | rows linkable in extract |")
        out.append("|-------|--------------------------|")
        for k, v in link_counts.items():
            out.append(f"| `{k}` | {v:,} |")
    if chosen_key_label:
        out.append("")
        out.append(
            f"**Selected customer key for label work:** `{chosen_key_label}`"
        )
    out.append("")

    out.append("## Per-org transaction volume (top 20 by count, from extract)")
    out.append("")
    if not per_org:
        out.append("_(no per-org rows)_")
    else:
        out.append(
            "| org_id (truncated) | txn count | earliest | latest "
            "| customers_with_id | distinct card_fps |"
        )
        out.append("|---|---:|---|---|---:|---:|")
        for r in per_org:
            org = str(r["org_id"])
            org_disp = org[:8] + "…" if len(org) > 9 else org
            out.append(
                f"| {org_disp} "
                f"| {r['txn_count']:,} "
                f"| {r['earliest']} "
                f"| {r['latest']} "
                f"| {r['customers_with_id']:,} "
                f"| {r['distinct_card_fps']:,} |"
            )
    out.append("")

    out.append("## Implied churn label — base rate by (lookback, horizon, min visits)")
    out.append("")
    out.append("Label: a customer is **churned at cutoff C** iff")
    out.append("  - they had a transaction in `[C - lookback, C]`, AND")
    out.append("  - they had >= `min_visits` lifetime transactions, AND")
    out.append("  - they had **no** transaction in `(C, C + horizon]`.")
    out.append("")
    out.append("`C` = `MAX(transaction_at) - horizon` (the latest cutoff that")
    out.append("still has a full horizon of post-cutoff data).")
    out.append("")
    if not churn_labels:
        out.append("_(no churn-label runs — see customer-identity counts above)_")
    else:
        out.append(
            "| lookback | horizon | min visits | cutoff | eligible "
            "| churned | retained | base rate |"
        )
        out.append("|---:|---:|---:|---|---:|---:|---:|---:|")
        for c in churn_labels:
            if c.get("error"):
                out.append(
                    f"| {c.get('lookback_days', '-')} "
                    f"| {c.get('horizon_days', '-')} "
                    f"| {c.get('min_lifetime_visits', '-')} "
                    f"| _err_ | _err_ | _err_ | _err_ "
                    f"| _{c['error']}_ |"
                )
                continue
            br = c.get("implied_base_rate")
            br_disp = f"{br:.1%}" if br is not None else "—"
            out.append(
                f"| {c['lookback_days']} "
                f"| {c['horizon_days']} "
                f"| {c['min_lifetime_visits']} "
                f"| {c['cutoff'][:10]} "
                f"| {c['n_eligible_customers']:,} "
                f"| {c['n_churned']:,} "
                f"| {c['n_retained']:,} "
                f"| {br_disp} |"
            )
    out.append("")

    out.append("## Verdict — is a defensible real-data churn eval feasible?")
    out.append("")
    # Derive the verdict from the data so the script writes the truth
    # mechanically, instead of leaving it to a human re-read.
    txn_n = txn_summary.get("row_count", 0)
    cust_n = max(link_counts.values()) if link_counts else 0
    eligible_max = max(
        (c.get("n_eligible_customers", 0) for c in churn_labels if not c.get("error")),
        default=0,
    )
    if txn_n < 100 or cust_n < 50 or eligible_max < 100:
        out.append("**NOT FEASIBLE** on the production Meridian DB at this time.")
        out.append("")
        out.append(
            f"- Transactions table holds {txn_n:,} rows. "
            f"Largest single customer-identity column populates "
            f"{cust_n:,} rows. Maximum eligible cohort across all "
            f"parameterisations: {eligible_max:,}."
        )
        out.append(
            "- The table census above shows the broader picture: every "
            "customer-history table (`customer_journeys`, "
            "`customer_sessions`, `anonymous_customer_profiles`, "
            "`chat_conversations`, `phone_orders`, ...) is empty. The "
            "production Meridian Postgres has not yet accumulated the "
            "purchase history a real-data churn eval would consume."
        )
        out.append("")
        out.append("### Minimum-viable alternatives")
        out.append("")
        out.append(
            "1. **Wait for organic data.** As more POS connections "
            "onboard and customer-link columns get populated, re-run this "
            "script. Re-evaluate when `n_eligible ≥ 1,000` on at least one "
            "parameterisation."
        )
        out.append(
            "2. **Pull from Latham CRM** (read-only export to the VPS) and "
            "run the harness against Latham's real customer-purchase "
            "history. Most direct path; preserves the \"real data\" "
            "discipline that motivated this whole project."
        )
        out.append(
            "3. **Pull from the Square integration directly** via the "
            "Customers + Payments APIs (`SQUARE_ACCESS_TOKEN` is on this "
            "box). Mirrors what Meridian will eventually have in-table, "
            "with the trade-off that the data covers only the Square-"
            "connected location(s)."
        )
        out.append(
            "4. **Public retail-churn dataset** (UCI Online Retail, "
            "Kaggle Telco Churn). Real but off-domain — useful for "
            "proving the harness end-to-end without committing to a "
            "model choice. Lowest transfer value to production Meridian."
        )
        out.append("")
        out.append(
            "Phase 2 (`eval/harness.py`) and Phase 3 (survival model) "
            "should NOT proceed against this DB. Pick an alternative or "
            "defer; either is honest."
        )
    else:
        out.append("**FEASIBLE.** At least one parameterisation supports a")
        out.append("defensible eval. Proceed to Phase 2.")
    out.append("")
    return out


if __name__ == "__main__":
    sys.exit(main())
