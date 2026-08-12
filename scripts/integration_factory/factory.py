#!/usr/bin/env python3
"""
Integration Factory — pipeline CLI for onboarding new integration providers.

The point: collapse "Aidan is the bottleneck" into a short, batched approval
list. Agents execute every automatable step (portal registration via browser
automation, credential storage, sandbox round-trips, questionnaire drafts);
this CLI is the shared ledger and the verification gate.

  python3 scripts/integration_factory/factory.py status
      Full pipeline board: stage, who's blocking, next step.

  python3 scripts/integration_factory/factory.py train
      THE APPROVAL TRAIN — only the items waiting on Aidan, with the exact
      artifact to review. Work through it top to bottom in one sitting.

  python3 scripts/integration_factory/factory.py verify <key> [--org-id ID]
      Live OAuth round-trip gate against a running backend (default
      http://localhost:8020). Prints the authorize URL for the sandbox
      consent (open it, or let a browser agent drive it), polls /status
      until the connection lands, then prints the exact registry patch to
      flip verified=True. Credentials must already be in the environment.

  python3 scripts/integration_factory/factory.py set <key> <stage>
      Advance the ledger (todo|applied|creds_stored|sandbox_ok|verified|live).

State lives in providers.json next to this file — commit ledger changes so
the pipeline history rides the branch.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LEDGER = HERE / "providers.json"
STAGES = ["todo", "applied", "creds_stored", "sandbox_ok", "verified", "live"]


def load_ledger() -> dict:
    return json.loads(LEDGER.read_text())


def save_ledger(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, indent=2) + "\n")


def registry_state() -> dict:
    """verified/configured flags straight from the live registry code."""
    sys.path.insert(0, str(REPO))
    os.environ.setdefault("TESTING", "1")
    from src.pos_connect.registry import PROVIDERS  # noqa: PLC0415
    return {
        k: {"verified": p.verified, "configured": p.credentials_present()}
        for k, p in PROVIDERS.items()
    }


def cmd_status(_args) -> None:
    ledger = load_ledger()
    reg = registry_state()
    fmt = "{:<14} {:<13} {:<7} {:<9} {:<9} {}"
    print(fmt.format("PROVIDER", "STAGE", "OWNER", "REGISTRY", "CREDS", "NEXT STEP"))
    print("-" * 100)
    for p in ledger["providers"]:
        r = reg.get(p["key"], {})
        nxt = p["path_to_live"][0] if p["path_to_live"] else "—"
        print(fmt.format(
            p["key"], p["stage"], p["owner_next"],
            "verified" if r.get("verified") else ("built" if p["key"] in reg else "partner"),
            "yes" if r.get("configured") else "no",
            nxt[:55],
        ))


def cmd_train(_args) -> None:
    ledger = load_ledger()
    waiting = [p for p in ledger["providers"] if p["owner_next"] == "aidan"]
    if not waiting:
        print("Nothing waiting on Aidan. The train is empty — agents are unblocked.")
        return
    print(f"APPROVAL TRAIN — {len(waiting)} item(s). Everything below is prepared; "
          "each needs only review + click/send.\n")
    for i, p in enumerate(waiting, 1):
        print(f"{i}. {p['key']}  [{p['stage']}]")
        for step in p["path_to_live"]:
            if step.startswith("aidan") or "aidan approves" in step:
                print(f"     → {step}")
        print(f"     portal: {p['portal']}")
        if p.get("notes"):
            print(f"     note: {p['notes']}")
        print()


def cmd_set(args) -> None:
    if args.stage not in STAGES:
        sys.exit(f"stage must be one of {STAGES}")
    ledger = load_ledger()
    for p in ledger["providers"]:
        if p["key"] == args.key:
            p["stage"] = args.stage
            if args.owner:
                p["owner_next"] = args.owner
            save_ledger(ledger)
            print(f"{args.key} → {args.stage}" + (f" (owner_next={args.owner})" if args.owner else ""))
            return
    sys.exit(f"unknown provider {args.key}")


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def cmd_verify(args) -> None:
    """OAuth round-trip gate. Requires: backend running with the provider's
    client credentials in its environment, and a sandbox account to approve
    the consent screen (human or browser agent)."""
    base = args.backend.rstrip("/")
    key, org = args.key, args.org_id

    reg = registry_state()
    if key not in reg:
        sys.exit(f"{key} is not a registry provider (partner-tier entries verify differently)")
    if not reg[key]["configured"]:
        sys.exit(f"{key}: client credentials not present in this environment — "
                 "store them first (secrets file + env), then re-run.")

    authorize = f"{base}/api/pos/{key}/authorize?org_id={urllib.parse.quote(org)}"
    status_url = f"{base}/api/pos/{key}/status?org_id={urllib.parse.quote(org)}"

    print(f"1. Open (or point a browser agent at):\n\n   {authorize}\n")
    print("2. Complete the provider consent with the SANDBOX account.")
    print(f"3. Polling {status_url} every 5s (Ctrl-C aborts)…\n")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        try:
            st = _get_json(status_url)
            if st.get("connected"):
                print(f"\n✓ ROUND-TRIP OK — merchant_id={st.get('merchant_id', '?')}")
                print("\nFlip the registry flag (then commit + PR):\n")
                print(f"  src/pos_connect/registry.py → ProviderConfig(key=\"{key}\", …)")
                print("  verified=False  →  verified=True   # validated "
                      f"{time.strftime('%Y-%m-%d')} via factory verify")
                print(f"\nThen: python3 {Path(__file__).relative_to(REPO)} set {key} verified")
                return
        except Exception:
            pass
        time.sleep(5)
    sys.exit("Timed out waiting for the connection to land. Check backend logs.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("train").set_defaults(func=cmd_train)

    p_set = sub.add_parser("set")
    p_set.add_argument("key")
    p_set.add_argument("stage")
    p_set.add_argument("--owner", choices=["agent", "aidan", "vendor"], default=None)
    p_set.set_defaults(func=cmd_set)

    p_ver = sub.add_parser("verify")
    p_ver.add_argument("key")
    p_ver.add_argument("--org-id", default="00000000-0000-4000-8000-000000000001")
    p_ver.add_argument("--backend", default="http://localhost:8020")
    p_ver.add_argument("--timeout", type=int, default=600)
    p_ver.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
