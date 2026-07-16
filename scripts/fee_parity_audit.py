#!/usr/bin/env python3
"""
Fee-parity audit — READ-ONLY reconciliation of sold deal terms vs live billing.

Diffs every closed/won lead (canada_leads + us_leads) against what the matched
live merchant is actually billed (subscriptions.monthly_price_cents,
phone_agent_config.order_fee_cents, merchant_websites.ordering_fee_pct) and
reports: matched / mismatched (who is OVERBILLED — needs proactive correction)
/ unmatchable (no lead↔merchant linkage — the structural gap this PR's
merchant_billing_terms table closes).

STRICTLY READ-ONLY: the only HTTP verb this script can emit is GET — the
transport asserts it. No insert/update/delete/rpc anywhere.

Usage:
    set -a; source <supabase env file>; set +a
    python scripts/fee_parity_audit.py [--out docs/fee_parity_audit_YYYYMMDD.md]

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_KEY).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

# Canonical tier table — import from the backend module (single source of truth).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.billing.fee_terms import (  # noqa: E402
    CANONICAL_FEE_TERMS,
    closest_plan_for_monthly,
    terms_from_lead_row,
)

READ_ONLY_METHOD = "GET"


def redact_email(email: str) -> str:
    """first3***@domain — never print full merchant emails in the report."""
    e = (email or "").strip()
    if "@" not in e:
        return (e[:3] + "***") if e else "(none)"
    local, domain = e.split("@", 1)
    return f"{local[:3]}***@{domain}"


class ReadOnlySupabase:
    """Minimal PostgREST client that can ONLY select. Any attempt to use a
    non-GET verb trips an assertion before a request is built."""

    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def build_request(self, method: str, table: str, params: dict[str, str]) -> urllib.request.Request:
        """Build the HTTP request. READ-ONLY GUARD lives here: every call path
        funnels through this method and non-GET is rejected outright."""
        assert method.upper() == READ_ONLY_METHOD, (
            f"fee_parity_audit is READ-ONLY — refused HTTP {method} on {table}"
        )
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(  # noqa: S310 — https URL from env
            f"{self.base}/{table}?{qs}",
            method=READ_ONLY_METHOD,
            headers={
                "Authorization": f"Bearer {self.key}",
                "apikey": self.key,
                "Accept": "application/json",
            },
        )
        assert req.get_method() == READ_ONLY_METHOD
        return req

    def select(self, table: str, select: str = "*", limit: int = 10000,
               **filters: str) -> list[dict[str, Any]]:
        params = {"select": select, "limit": str(limit), **filters}
        req = self.build_request(READ_ONLY_METHOD, table, params)
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return json.loads(resp.read().decode())


def _lead_contracted(market: str, lead: dict[str, Any]) -> dict[str, Any]:
    """Contracted terms for a lead. Locked structured columns win when present
    (post-migration); otherwise infer the closest canonical tier from the
    lead's monthly_value — flagged as inferred."""
    inferred = not lead.get("fee_terms_locked_at")
    terms = terms_from_lead_row(market, lead)
    monthly_cents = None
    try:
        if lead.get("monthly_value"):
            monthly_cents = int(round(float(lead["monthly_value"]) * 100))
    except (TypeError, ValueError):
        pass
    if inferred and monthly_cents:
        # For unlocked leads keep the REP-SOLD monthly (canonical clamp would
        # hide real drift); the tier/order-fee stay canonical-inferred.
        terms["monthly_fee_cents"] = monthly_cents
        terms["plan_tier"] = closest_plan_for_monthly(market, monthly_cents)
        terms["order_fee_cents"] = CANONICAL_FEE_TERMS[market][terms["plan_tier"]]["order_fee_cents"]
    return {**terms, "inferred": inferred}


def run_audit(db: ReadOnlySupabase) -> tuple[str, dict[str, Any]]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    leads: list[dict[str, Any]] = []
    for market, table, closed in (
        ("ca", "canada_leads", "in.(closed_won,customer_walkthrough)"),
        ("us", "us_leads", "eq.closed_won"),
    ):
        for row in db.select(table, stage=closed, order="updated_at.desc"):
            row["_market"], row["_table"] = market, table
            leads.append(row)

    businesses = db.select("businesses", select="id,name,email,plan_tier,status")
    subs = db.select(
        "subscriptions",
        select="org_id,tier,status,monthly_price_cents,current_period_end",
        status="in.(active,trialing,pending_payment,past_due)",
    )
    pac = db.select("phone_agent_config", select="merchant_id,order_fee_cents,plan_tier")
    try:
        sites = db.select("merchant_websites", select="merchant_id,ordering_fee_pct,ordering_enabled")
    except Exception:
        sites = []
    try:
        terms_rows = db.select("merchant_billing_terms", superseded_at="is.null")
    except Exception:
        terms_rows = []  # table not created yet (migration pending) — expected

    biz_by_email = {(b.get("email") or "").strip().lower(): b for b in businesses if b.get("email")}
    subs_by_org = {s["org_id"]: s for s in subs if s.get("org_id")}
    pac_by_merchant = {p["merchant_id"]: p for p in pac if p.get("merchant_id")}
    sites_by_merchant = {s["merchant_id"]: s for s in sites if s.get("merchant_id")}
    terms_by_merchant = {t["merchant_id"]: t for t in terms_rows if t.get("merchant_id")}

    matched: list[dict[str, Any]] = []
    mismatched: list[dict[str, Any]] = []
    unmatchable: list[dict[str, Any]] = []

    for lead in leads:
        market = lead["_market"]
        email = (lead.get("contact_email") or "").strip().lower()
        biz = biz_by_email.get(email)
        contracted = _lead_contracted(market, lead)
        entry: dict[str, Any] = {
            "market": market,
            "business": lead.get("business_name") or "(unnamed)",
            "email": redact_email(email),
            "stage": lead.get("stage"),
            "contracted": contracted,
        }
        sub = subs_by_org.get(biz["id"]) if biz else None
        if not biz or not sub:
            entry["reason"] = "no business row for lead email" if not biz else "no live subscription"
            unmatchable.append(entry)
            continue

        merchant_id = biz["id"]
        entry["merchant_id"] = merchant_id
        entry["has_billing_terms_row"] = merchant_id in terms_by_merchant
        diffs: list[dict[str, Any]] = []

        applied_monthly = sub.get("monthly_price_cents")
        if applied_monthly is not None and int(applied_monthly) != int(contracted["monthly_fee_cents"]):
            diffs.append({
                "field": "monthly_fee_cents",
                "contracted": int(contracted["monthly_fee_cents"]),
                "applied": int(applied_monthly),
                "delta": int(applied_monthly) - int(contracted["monthly_fee_cents"]),
            })

        p = pac_by_merchant.get(merchant_id) or {}
        applied_order_fee = p.get("order_fee_cents")
        if applied_order_fee is None:
            applied_order_fee = int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0)
            order_fee_src = "env-default"
        else:
            applied_order_fee = int(applied_order_fee)
            order_fee_src = "phone_agent_config"
        if int(contracted["order_fee_cents"]) != applied_order_fee:
            diffs.append({
                "field": f"order_fee_cents ({order_fee_src})",
                "contracted": int(contracted["order_fee_cents"]),
                "applied": applied_order_fee,
                "delta": applied_order_fee - int(contracted["order_fee_cents"]),
            })

        site = sites_by_merchant.get(merchant_id)
        if site and site.get("ordering_enabled"):
            pct = float(site.get("ordering_fee_pct") or 0.0299)
            website_fee = int(round(3000 * pct))  # % fee on a $30 reference order
            if website_fee != int(contracted["order_fee_cents"]):
                diffs.append({
                    "field": "website_order_fee_cents (pct model, $30 order)",
                    "contracted": int(contracted["order_fee_cents"]),
                    "applied": website_fee,
                    "delta": website_fee - int(contracted["order_fee_cents"]),
                })

        entry["subscription_status"] = sub.get("status")
        if diffs:
            entry["diffs"] = diffs
            entry["overbilled_monthly_cents"] = max(
                (d["delta"] for d in diffs if d["field"] == "monthly_fee_cents"), default=0)
            mismatched.append(entry)
        else:
            matched.append(entry)

    # Subscriptions with NO closed lead pointing at them (reverse linkage gap).
    lead_emails = {(ld.get("contact_email") or "").strip().lower() for ld in leads}
    orphan_subs = []
    for s in subs:
        b = next((x for x in businesses if x["id"] == s["org_id"]), None)
        bemail = (b.get("email") or "").strip().lower() if b else ""
        if not b or bemail not in lead_emails:
            orphan_subs.append({
                "merchant_id": s["org_id"],
                "business": (b or {}).get("name") or "(unknown)",
                "email": redact_email(bemail),
                "status": s.get("status"),
                "monthly_price_cents": s.get("monthly_price_cents"),
                "has_billing_terms_row": s["org_id"] in terms_by_merchant,
            })

    overbilled = [m for m in mismatched if m.get("overbilled_monthly_cents", 0) > 0]
    total_delta = sum(
        d["delta"] for m in mismatched for d in m["diffs"]
        if d["field"] == "monthly_fee_cents")

    summary = {
        "date": today,
        "leads_examined": len(leads),
        "matched": len(matched),
        "mismatched": len(mismatched),
        "unmatchable": len(unmatchable),
        "orphan_subscriptions": len(orphan_subs),
        "overbilled_merchants": len(overbilled),
        "total_monthly_delta_cents": total_delta,
        "billing_terms_rows": len(terms_rows),
    }

    # ── markdown ──
    def money(cents: Optional[int]) -> str:
        return "—" if cents is None else f"${cents / 100:,.2f}"

    lines = [
        f"# Fee Parity Audit — {today}",
        "",
        "READ-ONLY reconciliation of rep-sold deal terms (closed/won `canada_leads` +",
        "`us_leads`) against live billing (`subscriptions`, `phone_agent_config`,",
        "`merchant_websites`). Generated by `scripts/fee_parity_audit.py`.",
        "Merchant emails are redacted (`first3***@domain`).",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Closed/won leads examined | {summary['leads_examined']} |",
        f"| Matched (parity OK) | {summary['matched']} |",
        f"| **Mismatched (billing ≠ deal)** | **{summary['mismatched']}** |",
        f"| Unmatchable leads (no linkage — the structural finding) | {summary['unmatchable']} |",
        f"| Live subscriptions with no closed lead | {summary['orphan_subscriptions']} |",
        f"| **Overbilled merchants (need proactive correction)** | **{summary['overbilled_merchants']}** |",
        f"| Net monthly delta (applied − contracted) | {money(total_delta)} |",
        f"| merchant_billing_terms rows (post-migration) | {summary['billing_terms_rows']} |",
        "",
    ]

    if mismatched:
        lines += ["## Mismatched — billing does not match the deal", ""]
        for m in mismatched:
            flag = " ⚠️ **OVERBILLED — correct proactively**" if m.get("overbilled_monthly_cents", 0) > 0 else ""
            lines += [f"### {m['business']} ({m['market'].upper()}, {m['email']}){flag}", "",
                      f"- Subscription: `{m.get('subscription_status')}` · lead stage `{m['stage']}`"
                      f" · contracted terms {'locked' if not m['contracted'].get('inferred') else 'INFERRED from monthly_value (pre-migration lead)'}",
                      "", "| Field | Contracted | Applied | Delta |", "|---|---|---|---|"]
            for d in m["diffs"]:
                lines.append(f"| {d['field']} | {money(d['contracted'])} | {money(d['applied'])} | {money(d['delta'])} |")
            lines.append("")

    if matched:
        lines += ["## Matched — parity OK", "",
                  "| Business | Market | Email | Monthly | Sub status |", "|---|---|---|---|---|"]
        for m in matched:
            lines.append(
                f"| {m['business']} | {m['market'].upper()} | {m['email']} "
                f"| {money(m['contracted']['monthly_fee_cents'])} | {m.get('subscription_status')} |")
        lines.append("")

    if unmatchable:
        lines += ["## Unmatchable — no lead → merchant linkage (expected today)", "",
                  "This is the root-cause finding: deal terms recorded on leads never",
                  "provision live billing, and nothing links a closed lead to the merchant",
                  "it became. `merchant_billing_terms.source_lead_id` closes this gap for",
                  "every deal closed after this PR.", "",
                  "| Business | Market | Email | Stage | Sold monthly | Why unmatchable |",
                  "|---|---|---|---|---|---|"]
        for u in unmatchable:
            lines.append(
                f"| {u['business']} | {u['market'].upper()} | {u['email']} | {u['stage']} "
                f"| {money(u['contracted']['monthly_fee_cents'])} | {u['reason']} |")
        lines.append("")

    if orphan_subs:
        lines += ["## Live subscriptions with no closed lead", "",
                  "Billed merchants whose deal terms exist nowhere structured — cannot be",
                  "verified against what was sold without a manual paper-trail check.", "",
                  "| Business | Email | Status | Billed monthly | Has terms row |",
                  "|---|---|---|---|---|"]
        for o in orphan_subs:
            lines.append(
                f"| {o['business']} | {o['email']} | {o['status']} "
                f"| {money(o['monthly_price_cents'])} | {'yes' if o['has_billing_terms_row'] else 'no'} |")
        lines.append("")

    return "\n".join(lines) + "\n", summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = f"docs/fee_parity_audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    parser.add_argument("--out", default=default_out, help="markdown report path")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
              "(source the supabase env file).", file=sys.stderr)
        return 2

    report, summary = run_audit(ReadOnlySupabase(url, key))
    print(report)
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[audit] report written to {out_path}", file=sys.stderr)
    print(f"[audit] summary: {json.dumps(summary)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
