"""Tests for the outbound test-call param builder (no network / no dial)."""
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import place_test_call as ptc  # noqa: E402


def test_build_params_targets_voice_handler_with_merchant_override():
    p = ptc.build_call_params(
        to="+15551234567", frm="+17820001111",
        base_url="https://api.meridian.tips/", merchant_id="demo-merchant",
    )
    assert p["To"] == "+15551234567"
    assert p["From"] == "+17820001111"
    u = urlparse(p["Url"])
    assert u.scheme == "https" and u.netloc == "api.meridian.tips" and u.path == "/twilio/voice"
    assert parse_qs(u.query)["merchant_id"] == ["demo-merchant"]
    # trailing slash on base_url must not double up
    assert "//twilio" not in p["Url"]
    assert p["StatusCallback"] == "https://api.meridian.tips/twilio/status"


def test_build_params_specific_merchant():
    p = ptc.build_call_params("+1555", "+1782", "https://api.meridian.tips", "biz_abc123")
    assert parse_qs(urlparse(p["Url"]).query)["merchant_id"] == ["biz_abc123"]


def test_dry_run_main_no_dial(capsys):
    rc = ptc.main(["--to", "+15551234567", "--from", "+17820001111", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY RUN" in out and "/twilio/voice?merchant_id=" in out
