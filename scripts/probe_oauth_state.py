#!/usr/bin/env python3
"""
Live multi-worker OAuth-state integrity probe.

Why this exists: meridian-api runs `uvicorn --workers 4`. The Square/Clover OAuth
`state` token is HMAC-signed with OAUTH_STATE_SECRET. If that env var is unset,
each worker generates its OWN ephemeral secret at boot — so a `state` signed by
the worker that served /authorize cannot be verified by the (random) worker that
serves /callback. Result: ~75% of real connect attempts die with
"403 Invalid or expired state". A single in-process test can't see this (one
process, one secret); only a probe against the live multi-worker server can.

What it does: N times, hit /api/{provider}/authorize, pull the signed `state`
out of the provider redirect, then immediately hit /api/{provider}/callback with
that state + a junk code. We assert state verification NEVER spuriously rejects.

Classification of the /callback response:
  - 403 + "Invalid or expired state"      -> STATE-REJECT  (the bug)
  - 307 whose Location has oauth=error|partial|success  -> state ACCEPTED
        (token exchange failing on the junk code is expected and fine)
  - anything else                          -> UNKNOWN (reported, counts as fail)

PASS = zero STATE-REJECTs and zero UNKNOWNs across all iterations.
This writes NOTHING: a rejected state never reaches the DB, and an accepted
state fails at token exchange (junk code) before any row is written.

Usage:
    python scripts/probe_oauth_state.py [--base http://localhost:8000]
                                        [--provider square|clover] [-n 12]
Exit 0 = PASS, 1 = FAIL, 2 = could not run (server unreachable / no redirect).
"""
import argparse
import sys
import uuid
from urllib.parse import urlparse, parse_qs

import httpx

RETURN_TO = "/canada/merchant/onboard"


def _get(base: str, path: str, params: dict):
    """One request on a FRESH connection (Connection: close + no keep-alive) so
    `uvicorn --workers N` can route each request to a different worker. Reusing a
    keep-alive connection pins every request to one worker and masks the bug."""
    with httpx.Client(
        timeout=15.0,
        limits=httpx.Limits(max_keepalive_connections=0),
        headers={"Connection": "close"},
    ) as c:
        return c.get(f"{base}{path}", params=params, follow_redirects=False)


def probe_once(base: str, provider: str) -> tuple[str, str]:
    """Returns (verdict, detail). verdict in {ACCEPT, REJECT, UNKNOWN}."""
    org_id = str(uuid.uuid4())
    # 1) /authorize -> 307 to the provider with our signed state in the query.
    a = _get(base, f"/api/{provider}/authorize", {"org_id": org_id, "return_to": RETURN_TO})
    if a.status_code != 307:
        return "UNKNOWN", f"authorize returned {a.status_code} (expected 307)"
    loc = a.headers.get("location", "")
    state = parse_qs(urlparse(loc).query).get("state", [None])[0]
    if not state:
        return "UNKNOWN", f"no state in authorize redirect: {loc[:120]}"

    # 2) /callback with that state + a junk code, on a fresh connection. State is
    #    verified BEFORE the code is exchanged, so a healthy server reaches the
    #    (failing) exchange.
    c = _get(base, f"/api/{provider}/callback", {"code": "PROBE", "state": state})
    if c.status_code == 403:
        body = (c.text or "").lower()
        if "invalid or expired state" in body or "csrf" in body:
            return "REJECT", "403 invalid/expired state (unshared secret across workers)"
        return "UNKNOWN", f"403 but unexpected body: {c.text[:120]}"
    if c.status_code in (302, 307):
        q = parse_qs(urlparse(c.headers.get("location", "")).query)
        oauth = q.get("oauth", [""])[0]
        if oauth in ("error", "partial", "success", "denied"):
            return "ACCEPT", f"state accepted (oauth={oauth}, token-exchange path reached)"
        return "UNKNOWN", f"redirect without oauth marker: {c.headers.get('location','')[:120]}"
    return "UNKNOWN", f"callback returned {c.status_code}: {c.text[:120]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--provider", default="square", choices=["square", "clover"])
    ap.add_argument("-n", "--iterations", type=int, default=12)
    args = ap.parse_args()

    print(f"OAuth state probe: {args.iterations}x {args.base}/api/{args.provider}/{{authorize,callback}}")
    accepts = rejects = unknowns = 0
    for i in range(args.iterations):
        try:
            verdict, detail = probe_once(args.base, args.provider)
        except httpx.HTTPError as e:
            print(f"  [{i+1:2}/{args.iterations}] CONNECT-ERROR: {e}")
            return 2
        mark = {"ACCEPT": "ok ", "REJECT": "BUG", "UNKNOWN": "??? "}[verdict]
        print(f"  [{i+1:2}/{args.iterations}] {mark} {detail}")
        accepts += verdict == "ACCEPT"
        rejects += verdict == "REJECT"
        unknowns += verdict == "UNKNOWN"

    ok = rejects == 0 and unknowns == 0
    print(f"\nstateprobe={accepts}/{args.iterations} accepted, "
          f"{rejects} state-rejects, {unknowns} unknown => {'PASS' if ok else 'FAIL'}")
    if rejects:
        print("  -> OAUTH_STATE_SECRET is not shared across workers. Set it in .env + restart.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
