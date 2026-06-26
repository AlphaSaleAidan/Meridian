"""Stage A — Square API feasibility recon.

Phase 1 found prod Meridian Postgres holds 3 transactions and no
customer-identity column at all. Square (`SQUARE_ACCESS_TOKEN`) is the
system of record for the live US locations; this script asks Square,
read-only, whether the real data needed to train and evaluate a churn
model is actually there.

What this does (all read-only):

  1. Hit `GET /v2/locations` — confirms the token authenticates and
     lists the connected Square locations.
  2. Sample the Customers directory (`GET /v2/customers`, paginated,
     capped) — confirms the customer directory is populated and which
     identity fields are present.
  3. Search Orders (`POST /v2/orders/search`, paginated DESC by
     `created_at`) — confirms the orders carry `customer_id`, finds
     the date range, and counts at a few rolling windows.

Caps: orders pull stops at `MAX_ORDERS_SAMPLE` or `MAX_PULL_SECONDS`,
whichever comes first. The script reports whichever happened so a
truncated sample never poses as a complete count.

What it does NOT do:

  - Write anything back to Square or Meridian (no POST/PUT/DELETE on
    Meridian; the Orders `POST /v2/orders/search` is a *search*
    endpoint, not a writer);
  - Send customer data to any LLM/external API — Square is the only
    egress and only the input direction;
  - Persist any customer-identifying data. The on-disk report contains
    only counts, percentages, and timestamps.

Run:

    PYTHONPATH=/root/Meridian /root/Meridian/.venv/bin/python -m eval.square_recon

Output: stdout + `eval/reports/square_recon_<YYYY-MM-DD>.md`.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "eval" / "reports"

SQUARE_API_VERSION = "2024-12-18"
PROD_BASE = "https://connect.squareup.com"
SANDBOX_BASE = "https://connect.squareupsandbox.com"

PAGE_SIZE_ORDERS = 500       # Square's max per page on Orders search
PAGE_SIZE_CUSTS = 100         # Square's default; max is 100 on Customers list
MAX_ORDERS_SAMPLE = 50_000    # refuse to bulk-pull more than this in Stage A
MAX_CUST_SAMPLE = 2_000       # enough to characterise identity coverage
MAX_PULL_SECONDS = 300        # 5 min ceiling for either pull
HTTP_TIMEOUT = 90             # per-request


def _load_env() -> None:
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


class SquareClient:
    """Minimal read-only Square API client.

    Exposes only `get` and `search_orders` (the only POST endpoint we
    use is `/v2/orders/search`, which is a *search* operation despite
    the verb). No write methods are defined."""

    def __init__(self, token: str, environment: str) -> None:
        self._token = token
        self._base = PROD_BASE if environment.lower() == "production" else SANDBOX_BASE
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Square-Version": SQUARE_API_VERSION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _req(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        if method not in ("GET", "POST"):
            raise ValueError(f"refusing method {method!r}")
        url = f"{self._base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method, headers=self._headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace") if exc.fp else ""
            try:
                payload = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                payload = {"raw": body_text[:400]}
            return exc.code, payload

    def get(self, path: str) -> tuple[int, dict[str, Any]]:
        return self._req("GET", path)

    def search_orders(self, query: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return self._req("POST", "/v2/orders/search", body=query)


def _check_auth(client: SquareClient) -> dict[str, Any]:
    """Validate the token by hitting `/v2/locations` — cheapest call
    on the API. Returns merchant + locations summary or an `error`
    field."""
    status, body = client.get("/v2/locations")
    if status >= 400:
        return {"error": f"locations API returned {status}", "detail": body}
    locations = body.get("locations") or []
    # Extract a small public-information summary per location.
    summary = []
    for loc in locations:
        summary.append({
            "id": loc.get("id"),
            "name": loc.get("name"),
            "type": loc.get("type"),
            "status": loc.get("status"),
            "country": loc.get("country"),
            "currency": loc.get("currency"),
            "created_at": loc.get("created_at"),
        })
    return {
        "n_locations": len(locations),
        "locations": summary,
    }


def _customer_sample(client: SquareClient) -> dict[str, Any]:
    """Pull a capped customer sample to estimate identity coverage."""
    started = time.monotonic()
    pulled = 0
    has_email = 0
    has_phone = 0
    has_name = 0
    has_address = 0
    cursor: str | None = None
    earliest_created: datetime | None = None
    latest_created: datetime | None = None
    truncated = False

    while pulled < MAX_CUST_SAMPLE:
        if time.monotonic() - started > MAX_PULL_SECONDS:
            truncated = True
            break
        path = f"/v2/customers?limit={PAGE_SIZE_CUSTS}"
        if cursor:
            path = path + f"&cursor={urllib.parse.quote(cursor)}"
        status, body = client.get(path)
        if status >= 400:
            return {"error": f"customers API returned {status}", "detail": body}
        customers = body.get("customers") or []
        if not customers:
            break
        for c in customers:
            pulled += 1
            if c.get("email_address"):
                has_email += 1
            if c.get("phone_number"):
                has_phone += 1
            if c.get("given_name") or c.get("family_name"):
                has_name += 1
            if c.get("address"):
                has_address += 1
            created_at = c.get("created_at")
            if created_at:
                d = _parse_dt(created_at)
                if earliest_created is None or d < earliest_created:
                    earliest_created = d
                if latest_created is None or d > latest_created:
                    latest_created = d
        cursor = body.get("cursor")
        if not cursor:
            break
        if pulled >= MAX_CUST_SAMPLE:
            truncated = True
            break

    return {
        "sampled": pulled,
        "truncated_at_cap": truncated,
        "with_email_pct": (has_email / pulled) if pulled else 0.0,
        "with_phone_pct": (has_phone / pulled) if pulled else 0.0,
        "with_name_pct": (has_name / pulled) if pulled else 0.0,
        "with_address_pct": (has_address / pulled) if pulled else 0.0,
        "created_at_earliest": earliest_created.isoformat() if earliest_created else None,
        "created_at_latest": latest_created.isoformat() if latest_created else None,
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }


def _orders_sample(
    client: SquareClient, location_ids: list[str],
) -> dict[str, Any]:
    """Paginate `POST /v2/orders/search` DESC by created_at, capped at
    `MAX_ORDERS_SAMPLE` or `MAX_PULL_SECONDS`. Tracks identity-link
    rate, unique customer count, date range, and per-month volume."""
    if not location_ids:
        return {"error": "no location_ids passed to orders search"}

    started = time.monotonic()
    pulled = 0
    with_customer_id = 0
    unique_customers: set[str] = set()
    earliest: datetime | None = None
    latest: datetime | None = None
    per_month_count: dict[str, int] = {}
    cursor: str | None = None
    truncated = False
    last_error: dict[str, Any] | None = None
    per_status_count: dict[str, int] = {}

    while pulled < MAX_ORDERS_SAMPLE:
        if time.monotonic() - started > MAX_PULL_SECONDS:
            truncated = True
            break
        query: dict[str, Any] = {
            "location_ids": location_ids,
            "query": {
                "sort": {
                    "sort_field": "CREATED_AT",
                    "sort_order": "DESC",
                },
            },
            "limit": PAGE_SIZE_ORDERS,
        }
        if cursor:
            query["cursor"] = cursor
        status, body = client.search_orders(query)
        if status >= 400:
            last_error = {"http": status, "body": body}
            break
        orders = body.get("orders") or []
        if not orders:
            break
        for o in orders:
            pulled += 1
            cid = o.get("customer_id")
            if cid:
                with_customer_id += 1
                unique_customers.add(cid)
            created_at = o.get("created_at")
            if created_at:
                d = _parse_dt(created_at)
                if earliest is None or d < earliest:
                    earliest = d
                if latest is None or d > latest:
                    latest = d
                ym = f"{d.year:04d}-{d.month:02d}"
                per_month_count[ym] = per_month_count.get(ym, 0) + 1
            state = o.get("state", "UNKNOWN")
            per_status_count[state] = per_status_count.get(state, 0) + 1
        cursor = body.get("cursor")
        if not cursor:
            break
        if pulled >= MAX_ORDERS_SAMPLE:
            truncated = True
            break

    return {
        "sampled": pulled,
        "truncated_at_cap": truncated,
        "last_error": last_error,
        "with_customer_id": with_customer_id,
        "with_customer_id_pct": (with_customer_id / pulled) if pulled else 0.0,
        "unique_customers_in_sample": len(unique_customers),
        "earliest_created_at": earliest.isoformat() if earliest else None,
        "latest_created_at": latest.isoformat() if latest else None,
        "per_month": sorted(per_month_count.items()),
        "per_status": sorted(per_status_count.items()),
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }


def _repeat_customer_estimate(orders_sample: dict[str, Any]) -> dict[str, Any]:
    """From the per_month + with_customer_id figures, give a rough
    "are there enough repeat customers to label churn" reading.

    We can't get exact repeat counts without per-customer-grouped
    data, but we can estimate:
      - If `with_customer_id_pct` is high (~80%+) and
        `unique_customers_in_sample` is much smaller than `sampled`,
        the average orders-per-customer is high → repeat behaviour
        present.
      - The implied `orders_per_unique_customer` is the headline
        metric for "is there a churn signal here at all".
    """
    sampled = orders_sample.get("sampled", 0)
    uniq = orders_sample.get("unique_customers_in_sample", 0)
    with_id = orders_sample.get("with_customer_id", 0)
    if sampled == 0 or uniq == 0:
        return {"orders_per_unique_customer": None}
    return {
        "orders_with_customer_id": with_id,
        "unique_customers": uniq,
        "orders_per_unique_customer": round(with_id / uniq, 2),
    }


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def main() -> int:
    _load_env()

    token = os.environ.get("SQUARE_ACCESS_TOKEN", "")
    environment = os.environ.get("SQUARE_ENVIRONMENT", "production")
    if not token:
        print("ABORT: SQUARE_ACCESS_TOKEN not set in .env")
        return 2

    client = SquareClient(token, environment)
    print(f"Square API: {client._base} (env: {environment})")

    # ── A1: auth + locations ──────────────────────────────────
    auth = _check_auth(client)
    if "error" in auth:
        print(f"ABORT: {auth}")
        return 3
    print(f"locations: {auth['n_locations']}")

    location_ids = [loc["id"] for loc in auth["locations"] if loc.get("id")]
    if not location_ids:
        print("ABORT: no location IDs returned")
        return 4

    # ── A2: customer directory sample ────────────────────────
    customers = _customer_sample(client)
    print(f"customers sampled: {customers.get('sampled', 'err')}")

    # ── A3: orders sample (DESC by created_at) ───────────────
    print("orders search starting (cap "
          f"{MAX_ORDERS_SAMPLE:,} / {MAX_PULL_SECONDS}s)...")
    orders = _orders_sample(client, location_ids)
    print(f"orders sampled: {orders.get('sampled', 'err')}")

    repeat = _repeat_customer_estimate(orders)

    # ── A4: render report ────────────────────────────────────
    report_lines = _format_report(
        environment=environment,
        base=client._base,
        auth=auth,
        customers=customers,
        orders=orders,
        repeat=repeat,
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"square_recon_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(report_lines) + "\n")

    for line in report_lines:
        print(line)
    print(f"\nReport written to: {report_path}")
    return 0


def _format_report(
    *,
    environment: str,
    base: str,
    auth: dict[str, Any],
    customers: dict[str, Any],
    orders: dict[str, Any],
    repeat: dict[str, Any],
) -> list[str]:
    out: list[str] = []
    today = date.today().isoformat()
    out.append(f"# Square API recon — Stage A feasibility ({today})")
    out.append("")
    out.append(f"- Environment (from `SQUARE_ENVIRONMENT`): **{environment}**")
    out.append(f"- API base: `{base}`")
    out.append(f"- Square-Version header: `{SQUARE_API_VERSION}`")
    out.append("")
    out.append("All output is aggregate; no customer identifiers recorded.")
    out.append("Read-only across both Square (this script) and Meridian (untouched).")
    out.append("")
    out.append("## A1 — Authentication + locations")
    out.append("")
    out.append(f"- Token authenticates: **YES** (HTTP 200 on `/v2/locations`)")
    out.append(f"- Locations connected: **{auth['n_locations']}**")
    if auth["locations"]:
        out.append("")
        out.append("| id | name | type | status | country | currency | created_at |")
        out.append("|----|------|------|--------|---------|----------|------------|")
        for loc in auth["locations"]:
            out.append(
                f"| {loc.get('id', '-')} "
                f"| {loc.get('name', '-')} "
                f"| {loc.get('type', '-')} "
                f"| {loc.get('status', '-')} "
                f"| {loc.get('country', '-')} "
                f"| {loc.get('currency', '-')} "
                f"| {loc.get('created_at', '-')} |"
            )
    out.append("")

    out.append("## A2 — Customers directory sample")
    out.append("")
    if customers.get("error"):
        out.append(f"- Probe error: `{customers['error']}` — {customers.get('detail')}")
    else:
        out.append(f"- Customers sampled: **{customers['sampled']:,}** "
                   f"({'TRUNCATED at cap' if customers['truncated_at_cap'] else 'complete'})")
        out.append(f"- With `email_address`: {customers['with_email_pct']:.0%}")
        out.append(f"- With `phone_number`: {customers['with_phone_pct']:.0%}")
        out.append(f"- With `given_name` or `family_name`: {customers['with_name_pct']:.0%}")
        out.append(f"- With `address`: {customers['with_address_pct']:.0%}")
        out.append(f"- Earliest `created_at` in sample: {customers['created_at_earliest']}")
        out.append(f"- Latest `created_at` in sample: {customers['created_at_latest']}")
        out.append(f"- Sample wall time: {customers['elapsed_seconds']}s")
    out.append("")

    out.append("## A3 — Orders search (DESC by `created_at`)")
    out.append("")
    if orders.get("last_error"):
        out.append(f"- Last error mid-sample: `{orders['last_error']}`")
    out.append(
        f"- Orders sampled: **{orders.get('sampled', 0):,}** "
        f"({'TRUNCATED at cap' if orders.get('truncated_at_cap') else 'complete'})"
    )
    out.append(f"- With `customer_id` populated: "
               f"**{orders.get('with_customer_id', 0):,}** "
               f"({orders.get('with_customer_id_pct', 0):.1%})")
    out.append(f"- Distinct `customer_id` values in sample: "
               f"**{orders.get('unique_customers_in_sample', 0):,}**")
    out.append(f"- Earliest `created_at` in sample: {orders.get('earliest_created_at')}")
    out.append(f"- Latest `created_at` in sample: {orders.get('latest_created_at')}")
    out.append(f"- Sample wall time: {orders.get('elapsed_seconds', '?')}s")

    if orders.get("per_status"):
        out.append("")
        out.append("Order state distribution (sample):")
        out.append("")
        out.append("| state | count |")
        out.append("|-------|------:|")
        for k, v in orders["per_status"]:
            out.append(f"| {k} | {v:,} |")

    if orders.get("per_month"):
        out.append("")
        out.append("Monthly distribution (sample, oldest → newest):")
        out.append("")
        out.append("| YYYY-MM | orders |")
        out.append("|---------|-------:|")
        for ym, n in orders["per_month"]:
            out.append(f"| {ym} | {n:,} |")
    out.append("")

    out.append("## A4 — Repeat-customer signal")
    out.append("")
    if not repeat.get("orders_per_unique_customer"):
        out.append("_(insufficient data — no customer-linked orders in sample)_")
    else:
        out.append(
            f"- Average orders per unique customer (sample): "
            f"**{repeat['orders_per_unique_customer']}**"
        )
        out.append(
            "  - <1.5 → mostly one-off purchasers; churn label "
            "would be near-100% by construction."
        )
        out.append(
            "  - 1.5–3 → moderate repeat behaviour; supports a "
            "churn label but the eligible cohort is smaller."
        )
        out.append(
            "  - ≥3 → solid repeat-purchase signal; cohort fully "
            "supports a defensible churn label and a temporal split."
        )
    out.append("")

    out.append("## Verdict — does Square have enough real data for a churn eval?")
    out.append("")
    n_orders = orders.get("sampled", 0)
    cid_rate = orders.get("with_customer_id_pct", 0.0)
    uniq = orders.get("unique_customers_in_sample", 0)
    opc = repeat.get("orders_per_unique_customer") or 0
    truncated = orders.get("truncated_at_cap", False)
    earliest_dt = orders.get("earliest_created_at")
    latest_dt = orders.get("latest_created_at")
    span_days: float | None = None
    if earliest_dt and latest_dt:
        span_days = (_parse_dt(latest_dt) - _parse_dt(earliest_dt)).days

    if environment.lower() != "production":
        out.append("**SANDBOX TOKEN** — data is synthetic; disqualifies for real-data eval.")
    elif n_orders == 0:
        out.append("**NO DATA** — orders search returned zero rows.")
    elif cid_rate < 0.5:
        out.append(
            f"**THIN ON IDENTITY** — only {cid_rate:.1%} of sampled orders "
            f"carry a `customer_id`. Churn-by-customer is not labelable "
            "from this data without a different identity strategy."
        )
    elif uniq < 200:
        out.append(
            f"**TOO FEW CUSTOMERS** — only {uniq:,} distinct customers in "
            f"the sample. A defensible eval wants several hundred minimum."
        )
    elif opc < 1.5:
        out.append(
            f"**MOSTLY ONE-OFFS** — {opc} orders/customer means almost "
            "everyone churns by construction. No useful signal for a "
            "repeat-purchase churn model."
        )
    elif span_days is not None and span_days < 90:
        out.append(
            f"**HISTORY TOO SHORT** — sample spans {span_days} days; "
            "a temporal train/test split with a sensible lookback + "
            "horizon needs at least 6–9 months of history."
        )
    else:
        out.append("**FEASIBLE.** Sufficient volume, identity coverage, and history span.")
        out.append(
            f"- Orders in sample: {n_orders:,} "
            f"({'TRUNCATED — true total is larger' if truncated else 'complete'})"
        )
        out.append(f"- Identity coverage: {cid_rate:.1%}")
        out.append(f"- Distinct customers: {uniq:,}")
        out.append(f"- Orders per customer (avg): {opc}")
        out.append(f"- History span: {span_days} days")
        out.append("")
        out.append("Stage B can proceed: pull a representative read-only sample to")
        out.append("`eval/data/square_sample/` (gitignored), build the temporal-split")
        out.append("eval dataset, run the survival-vs-incumbent comparison.")
    out.append("")
    return out


if __name__ == "__main__":
    sys.exit(main())
