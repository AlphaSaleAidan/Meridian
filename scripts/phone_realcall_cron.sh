#!/usr/bin/env bash
# Nightly real-call self-training run for the Meridian phone agent.
# Mines the last few days of calls, scores them into phone_call_insights, and
# emails the proposal report. NEVER changes the live agent — data + proposals only.
#
# Wired into crontab (see `crontab -l`). Env is extracted from /root/Meridian/.env
# key-by-key because that file has unquoted values that break `source`.
set -uo pipefail

ENV_FILE=/root/Meridian/.env
OUT=/tmp/phone-realcall-out
LOG=/tmp/meridian-phone-realcall.log
REPORT_TO="aidanpierce72@gmail.com"

getenv() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'; }

export SUPABASE_URL="$(getenv SUPABASE_URL)"
export SUPABASE_SERVICE_ROLE_KEY="$(getenv SUPABASE_SERVICE_ROLE_KEY)"
export DEEPSEEK_API_KEY="$(getenv DEEPSEEK_API_KEY)"
RESEND_API_KEY="$(getenv RESEND_API_KEY)"

cd /root/Meridian || exit 1
echo "=== $(date -u +%FT%TZ) phone real-call training ===" >> "$LOG"

# --days 3 gives overlap if a night is missed; already-judged calls are skipped.
run_out="$(timeout 1200 python3 scripts/phone_realcall_train.py \
  --days 3 --min-duration 10 --concurrency 3 --out "$OUT" 2>&1)"
echo "$run_out" >> "$LOG"

# Skip the email when nothing new was scored (no nightly noise).
if echo "$run_out" | grep -q "nothing to do"; then
  echo "no new calls — skipping email" >> "$LOG"
  exit 0
fi

# Email the proposal report (only if a Resend key is configured).
if [ -n "$RESEND_API_KEY" ] && [ -f "$OUT/report.md" ]; then
  RESEND_API_KEY="$RESEND_API_KEY" REPORT_TO="$REPORT_TO" REPORT_FILE="$OUT/report.md" \
  python3 - <<'PY' >> "$LOG" 2>&1
import os, json, urllib.request
key = os.environ["RESEND_API_KEY"]
body = open(os.environ["REPORT_FILE"]).read()
html = "<pre style='font:13px ui-monospace,monospace;white-space:pre-wrap'>" + \
       body.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + "</pre>"
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
def send(frm):
    req = urllib.request.Request("https://api.resend.com/emails",
        data=json.dumps({"from": frm, "to": [os.environ["REPORT_TO"]],
            "subject": "Meridian phone agent — nightly quality report", "html": html}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": ua},
        method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=25)
        print("email sent:", r.status); return True
    except urllib.error.HTTPError as e:
        print("email failed:", e.code, e.read().decode()[:200]); return False
# reports@meridian.tips is the verified sender used by the other report jobs.
if not send("Meridian <reports@meridian.tips>"):
    send("Meridian <onboarding@resend.dev>")
PY
else
  echo "no RESEND_API_KEY or report — skipping email" >> "$LOG"
fi
