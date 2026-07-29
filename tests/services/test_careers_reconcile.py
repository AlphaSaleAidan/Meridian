"""Careers reconciliation invariant tests (pure logic, no DB).

Run:  python -m pytest tests/services/test_careers_reconcile.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.services.careers_reconcile import find_careers_gaps  # noqa: E402

NOW = datetime(2026, 7, 29, 15, 0, tzinfo=timezone.utc)


def _app(email, name="Some Applicant", country="CA", hours_ago=2.0):
    return {
        "name": name,
        "email": email,
        "country": country,
        "created_at": (NOW - timedelta(hours=hours_ago)).isoformat(),
    }


def _log(hours_ago):
    return {"created_at": (NOW - timedelta(hours=hours_ago)).isoformat()}


def test_healthy_pipeline_reports_no_gaps():
    apps = [_app("a@x.com", hours_ago=2)]
    vis, mail = find_careers_gaps(apps, {"a@x.com"}, [_log(1.9)], now=NOW)
    assert vis == [] and mail == []


def test_missing_rep_row_is_a_visibility_gap():
    apps = [_app("ghost@x.com", name="Ghost")]
    vis, mail = find_careers_gaps(apps, {"other@x.com"}, [_log(1.9)], now=NOW)
    assert [a["email"] for a in vis] == ["ghost@x.com"]


def test_rep_email_match_is_case_insensitive():
    apps = [_app("MiXeD@X.com")]
    vis, _ = find_careers_gaps(apps, {"mixed@x.com"}, [_log(1.9)], now=NOW)
    assert vis == []


def test_recent_application_without_email_log_is_an_email_gap():
    apps = [_app("a@x.com", hours_ago=2)]
    vis, mail = find_careers_gaps(apps, {"a@x.com"}, [], now=NOW)
    assert vis == [] and [a["email"] for a in mail] == ["a@x.com"]


def test_old_application_is_not_an_email_gap():
    # Older than the 25h window: email history has been trimmed / irrelevant.
    apps = [_app("a@x.com", hours_ago=48)]
    _, mail = find_careers_gaps(apps, {"a@x.com"}, [], now=NOW)
    assert mail == []


def test_email_log_outside_the_hour_window_does_not_count():
    # A log entry from before the application can't be its alert.
    apps = [_app("a@x.com", hours_ago=2)]
    _, mail = find_careers_gaps(apps, {"a@x.com"}, [_log(5)], now=NOW)
    assert [a["email"] for a in mail] == ["a@x.com"]


def test_e2e_test_rows_are_ignored():
    apps = [_app("e2e-careers-test-z@meridian.tips")]
    vis, mail = find_careers_gaps(apps, set(), [], now=NOW)
    assert vis == [] and mail == []
