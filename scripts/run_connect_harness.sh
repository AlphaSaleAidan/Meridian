#!/usr/bin/env bash
#
# run_connect_harness.sh — deterministic test harness for the Square POS-connect path.
#
# Three independent layers, each a different control plane:
#   inproc      Layer 1: real FastAPI app driven end-to-end (authorize→callback→backfill),
#               FakeDB + stubbed Square network. Asserts every dashboard-gating row/flag.
#   ingestion   Mock tier: real Square+Clover sync engines over canned fixtures, proving
#               connect→read→normalize→digest lands normalized transactions.
#   stateprobe  Layer 2: live HMAC OAuth-state sign/verify probe (already passing).
#
# Exit 0 only if all three PASS.
set -u
cd /root/Meridian || { echo "HARNESS: cannot cd /root/Meridian => FAIL"; exit 1; }

PY=.venv/bin/python

run_layer() {
  # $1 = label, rest = command
  local label="$1"; shift
  echo "────────────────────────────────────────────────────────────────────"
  echo "▶ ${label}: $*"
  echo "────────────────────────────────────────────────────────────────────"
  if "$@"; then
    echo "✅ ${label} PASS"
    return 0
  else
    echo "❌ ${label} FAIL"
    return 1
  fi
}

inproc=FAIL
ingestion=FAIL
stateprobe=FAIL

run_layer "inproc"     "$PY" -m pytest tests/e2e/test_portal_connect.py -q && inproc=PASS
run_layer "ingestion"  "$PY" -m src.tests.test_pos_ingestion                && ingestion=PASS
run_layer "stateprobe" "$PY" scripts/probe_oauth_state.py --provider square -n 12 && stateprobe=PASS

overall=PASS
[ "$inproc" = PASS ] && [ "$ingestion" = PASS ] && [ "$stateprobe" = PASS ] || overall=FAIL

echo
echo "===================================================================="
echo "HARNESS: inproc=${inproc} ingestion=${ingestion} stateprobe=${stateprobe} => ${overall}"
echo "===================================================================="

[ "$overall" = PASS ] && exit 0 || exit 1
