#!/usr/bin/env python3
"""
Mercury voice-cost reconcile — funnel revenue to cover Vapi expenses.

The AI phone agent earns money per paid order (the Stripe service fee, tracked as
`credit` rows in voice_ledger) and costs money per call (Vapi, tracked as `debit`
rows). Stripe pays the revenue out to Mercury Checking; Vapi's auto-top-up card
draws from Checking. This job keeps that cash-flow healthy, fully unattended:

  1. Sizes a RESERVE in Checking large enough to cover recent Vapi run-rate
     (max of a floor and the last-30-day debits from the ledger — auto-scaling).
  2. SWEEP: when Checking is above reserve + a threshold, move the surplus
     (profit) Checking → Savings so it accrues instead of being burned.
  3. TOP-UP (failsafe): when Checking dips below the reserve, pull from Savings
     back to Checking so the Vapi card never bounces.

SAFETY — moving real money is gated behind TWO independent switches that must
BOTH be set (independent control planes), plus a per-run cap, a minimum-move
floor, and a reserve floor that a sweep can never breach. Default is REPORT-ONLY:
it computes and prints/emails the intended move but calls no write endpoint.

    MERCURY_RECONCILE_ENABLED=1     # gate 1: arm the job
    MERCURY_TRANSFER_CONFIRMED=1    # gate 2: the /transfer contract is verified

Run on the Contabo box (209.126.80.45 — the IP the Mercury token is whitelisted
to). Reads secrets from /root/.secrets/{mercury,supabase}.env.

  python3 scripts/voice/mercury_reconcile.py            # report-only
  python3 scripts/voice/mercury_reconcile.py --execute  # honor the gates
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

SUPABASE_PROJECT = "kbuzufjxwflrutowwnfl"
SUPABASE_SQL_URL = f"https://api.supabase.com/v1/projects/{SUPABASE_PROJECT}/database/query"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── tunables (env-overridable) ───────────────────────────────────────
RESERVE_FLOOR_CENTS = int(os.getenv("VOICE_RESERVE_FLOOR_CENTS", "10000"))   # $100 min reserve
MAX_MOVE_CENTS      = int(os.getenv("MERCURY_MAX_MOVE_CENTS", "50000"))      # $500 per-run cap
MIN_MOVE_CENTS      = int(os.getenv("MERCURY_MIN_MOVE_CENTS", "2000"))       # $20 — skip dust
SWEEP_THRESHOLD     = int(os.getenv("MERCURY_SWEEP_THRESHOLD_CENTS", "2000"))# only sweep if surplus > this

# ── two independent money-movement gates ─────────────────────────────
GATE_ENABLED   = os.getenv("MERCURY_RECONCILE_ENABLED", "0") == "1"
GATE_CONFIRMED = os.getenv("MERCURY_TRANSFER_CONFIRMED", "0") == "1"


def _load_env(path: str) -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


def _post_json(url: str, token: str, body: dict, extra_headers: dict | None = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _sql(query: str) -> list[dict]:
    token = os.environ["SUPABASE_MGMT_TOKEN"]
    return _post_json(SUPABASE_SQL_URL, token, {"query": query})


def ledger_totals() -> dict:
    """Lifetime credit/debit + last-30-day debit run-rate, in cents."""
    rows = _sql("""
        select
          coalesce(sum(amount_cents) filter (where kind='credit'),0)            as credits,
          coalesce(sum(amount_cents) filter (where kind='debit'),0)             as debits,
          coalesce(sum(amount_cents) filter (where kind='debit'
                     and created_at > now() - interval '30 days'),0)            as debits_30d
        from voice_ledger;
    """)
    r = rows[0] if rows else {}
    return {
        "credits": int(r.get("credits") or 0),
        "debits": int(r.get("debits") or 0),
        "debits_30d": int(r.get("debits_30d") or 0),
    }


def mercury_accounts() -> dict:
    token = os.environ["MERCURY_API_TOKEN"]
    base = os.environ["MERCURY_API_BASE"]
    data = _get_json(f"{base}/accounts", token)
    out = {}
    for a in data.get("accounts", []):
        kind = (a.get("kind") or a.get("type") or "").lower()
        out[kind] = {
            "id": a.get("id"),
            "name": a.get("name"),
            "available_cents": int(round(float(a.get("availableBalance") or 0) * 100)),
        }
    return out


def mercury_transfer(from_id: str, to_id: str, cents: int, idem: str, note: str) -> dict:
    """Move money between two own accounts. GATED — never reached in report-only.

    Mercury's internal-transfer endpoint requires the SendMoney scope. The exact
    body is confirmed once with a supervised $1 test before GATE_CONFIRMED is set;
    until then this raises so a misconfigured run can never silently move money.
    """
    if not (GATE_ENABLED and GATE_CONFIRMED):
        raise RuntimeError("both MERCURY_RECONCILE_ENABLED and MERCURY_TRANSFER_CONFIRMED must be 1")
    token = os.environ["MERCURY_API_TOKEN"]
    base = os.environ["MERCURY_API_BASE"]
    # Confirmed 2026-06-26 with a $1 test: POST /transfer, amount in DOLLARS,
    # InternalTransferAPIRequest = {sourceAccountId, destinationAccountId, amount,
    # idempotencyKey, note}. Returns {creditTransaction, debitTransaction}.
    body = {
        "sourceAccountId": from_id,
        "destinationAccountId": to_id,
        "amount": round(cents / 100, 2),
        "idempotencyKey": idem,
        "note": note,
    }
    return _post_json(f"{base}/transfer", token, body)


def decide(checking_c: int, savings_c: int, reserve_c: int) -> dict:
    """Return {action, amount_cents, from_id?, to_id?, reason}."""
    surplus = checking_c - reserve_c
    if surplus > SWEEP_THRESHOLD:
        amt = min(surplus, MAX_MOVE_CENTS)
        if amt < MIN_MOVE_CENTS:
            return {"action": "none", "amount_cents": 0, "reason": f"surplus ${surplus/100:.2f} below min move"}
        # never breach the reserve
        amt = min(amt, checking_c - reserve_c)
        return {"action": "sweep", "amount_cents": amt,
                "reason": f"Checking ${checking_c/100:.2f} > reserve ${reserve_c/100:.2f}; sweep profit to Savings"}
    if checking_c < reserve_c and savings_c > 0:
        need = reserve_c - checking_c
        amt = min(need, savings_c, MAX_MOVE_CENTS)
        if amt < MIN_MOVE_CENTS:
            return {"action": "none", "amount_cents": 0, "reason": f"top-up ${need/100:.2f} below min move / no savings"}
        return {"action": "topup", "amount_cents": amt,
                "reason": f"Checking ${checking_c/100:.2f} < reserve ${reserve_c/100:.2f}; pull from Savings"}
    return {"action": "none", "amount_cents": 0,
            "reason": f"Checking ${checking_c/100:.2f} within reserve band"}


def main() -> int:
    _load_env("/root/.secrets/mercury.env")
    _load_env("/root/.secrets/supabase.env")
    execute = "--execute" in sys.argv

    led = ledger_totals()
    accts = mercury_accounts()
    chk, sav = accts.get("checking"), accts.get("savings")
    if not chk or not sav:
        print("ERROR: could not resolve Checking/Savings accounts:", list(accts))
        return 2

    reserve = max(RESERVE_FLOOR_CENTS, led["debits_30d"])  # auto-size to Vapi run-rate
    plan = decide(chk["available_cents"], sav["available_cents"], reserve)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== Mercury voice-cost reconcile — {now} ===")
    print(f"voice_ledger: credits ${led['credits']/100:.2f}  debits ${led['debits']/100:.2f}  "
          f"net ${ (led['credits']-led['debits'])/100:.2f}  (30d Vapi spend ${led['debits_30d']/100:.2f})")
    print(f"Mercury: Checking ${chk['available_cents']/100:.2f}  Savings ${sav['available_cents']/100:.2f}  "
          f"reserve target ${reserve/100:.2f}")
    print(f"PLAN: {plan['action'].upper()} ${plan['amount_cents']/100:.2f} — {plan['reason']}")

    if plan["action"] == "none" or plan["amount_cents"] <= 0:
        return 0

    if plan["action"] == "sweep":
        frm, to = chk["id"], sav["id"]
    else:  # topup
        frm, to = sav["id"], chk["id"]

    armed = execute and GATE_ENABLED and GATE_CONFIRMED
    if not armed:
        why = []
        if not execute: why.append("no --execute")
        if not GATE_ENABLED: why.append("MERCURY_RECONCILE_ENABLED!=1")
        if not GATE_CONFIRMED: why.append("MERCURY_TRANSFER_CONFIRMED!=1")
        print(f"REPORT-ONLY (no money moved) — {', '.join(why)}")
        return 0

    # idempotency: one move per (date, direction, amount) — re-run safe
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    idem = f"voicecost-{plan['action']}-{day}-{plan['amount_cents']}"
    try:
        res = mercury_transfer(frm, to, plan["amount_cents"], idem,
                               note=f"Meridian voice-cost {plan['action']} {day}")
        tx = (res.get("debitTransaction") or {}) if isinstance(res, dict) else {}
        print(f"EXECUTED {plan['action']} ${plan['amount_cents']/100:.2f}: "
              f"txn={tx.get('id') or 'ok'} status={tx.get('status') or '?'}")
        return 0
    except urllib.error.HTTPError as e:
        print(f"TRANSFER FAILED ({e.code}): {e.read().decode()[:300]}")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"TRANSFER ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
