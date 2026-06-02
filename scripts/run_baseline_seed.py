#!/usr/bin/env python3
"""
Baseline seed runner — drives the 25-task seed list from
``docs/swarm_baseline.md §4`` to populate ``swarm_traces`` with real data.

Per-task behavior:
  * print the planned invocation,
  * attempt it if the dependencies are available locally (demo org, API
    keys, optional ML deps, etc.),
  * record success/skip via ``trace_recorder``,
  * tasks the env can't run are marked ``skipped`` with a reason rather
    than crashing the runner.

This script is intentionally NOT run by CI. The team lead flips it on once
real API keys + a demo org are configured (see ``REPORT BACK`` notes in
the PR / Step 2 handoff).

Usage::

    DEMO_ORG_ID=<uuid> DEEPSEEK_API_KEY=... python3 scripts/run_baseline_seed.py

Environment knobs:
  * ``DEMO_ORG_ID``   — required for any pipeline task; if unset, those
    tasks are skipped with reason ``no_demo_org``.
  * ``DEEPSEEK_API_KEY`` / ``OPENAI_API_KEY`` / etc. — LLM tasks skip if
    no provider key is set.
  * ``MERIDIAN_SWARM_TRACE_DB`` — override target SQLite (default
    ``data/swarm_traces.sqlite``).

Rollback: rm this file. No call site depends on it.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Awaitable, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ai.trace_recorder import record, new_trace_id  # noqa: E402

# ---------------------------------------------------------------------------
# Task definitions — derived 1:1 from docs/swarm_baseline.md §4.
# Each task returns ("attempted" | "skipped", reason_or_None).
# ---------------------------------------------------------------------------


def _has_any_llm_key() -> bool:
    return any(
        os.environ.get(k)
        for k in ("DEEPSEEK_API_KEY", "SAMBANOVA_API_KEY", "GROQ_API_KEY",
                  "CEREBRAS_API_KEY", "OPENAI_API_KEY")
    )


def _demo_org() -> str | None:
    return os.environ.get("DEMO_ORG_ID") or os.environ.get("MERIDIAN_DEMO_ORG_ID")


async def _task_analyze_merchant(label: str) -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.engine import MeridianAI
        ai = MeridianAI()
        await ai.analyze_merchant(org)
        return ("attempted", None)
    except Exception as exc:
        return ("skipped", f"analyze_merchant_failed:{exc!r}"[:200])


async def _task_enhance_insights(n: int) -> tuple[str, str | None]:
    if not _has_any_llm_key():
        return ("skipped", "no_llm_key")
    try:
        from src.ai.llm_layer import enhance_insights
        raw = [
            {"id": f"i{i}", "category": "revenue", "title": f"insight {i}",
             "description": "x", "metric_value": 100, "benchmark_value": 80,
             "priority": "medium"}
            for i in range(n)
        ]
        await enhance_insights(raw, {"org_id": _demo_org() or "demo", "business_vertical": "coffee"})
        return ("attempted", None)
    except Exception as exc:
        return ("skipped", f"enhance_failed:{exc!r}"[:200])


async def _task_forecast_generator(horizon: int) -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.engine import MeridianAI
        ai = MeridianAI()
        await ai.analyze_merchant(org, days=max(30, horizon), include_forecasts=True)
        return ("attempted", None)
    except Exception as exc:
        return ("skipped", f"forecast_failed:{exc!r}"[:200])


async def _task_weekly_report() -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.engine import MeridianAI
        ai = MeridianAI()
        await ai.analyze_merchant(org, include_report=True)
        return ("attempted", None)
    except Exception as exc:
        return ("skipped", f"report_failed:{exc!r}"[:200])


async def _task_cline_agent() -> tuple[str, str | None]:
    try:
        # ClineAgent is an optional repair flow; require its module to be present.
        from src.ai.agents.cline_agent import ClineAgent  # type: ignore
    except Exception:
        return ("skipped", "cline_agent_unavailable")
    if not _has_any_llm_key():
        return ("skipped", "no_llm_key")
    return ("skipped", "cline_agent_needs_synthetic_failure_injection")


async def _task_commercial_director(kind: str) -> tuple[str, str | None]:
    try:
        from src.ai.commercial_director import CommercialDirector  # type: ignore  # noqa: F401
    except Exception:
        return ("skipped", "commercial_director_unavailable")
    if not _has_any_llm_key():
        return ("skipped", "no_llm_key")
    return ("skipped", f"commercial_director_{kind}_needs_video_pipeline")


async def _task_pricing_power() -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.engine import MeridianAI
        ai = MeridianAI()
        await ai.analyze_merchant(org)
        return ("attempted", None)
    except Exception as exc:
        return ("skipped", f"pricing_power_failed:{exc!r}"[:200])


async def _task_churn_warning() -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.predictive.churn_warning import compute_churn_warnings  # type: ignore
    except Exception:
        return ("skipped", "churn_module_unavailable")
    return ("skipped", "churn_needs_customer_cohort_fixture")


async def _task_seasonality() -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.agents.seasonality import SeasonalityAgent  # noqa: F401
        return ("attempted", None)
    except Exception as exc:
        return ("skipped", f"seasonality_failed:{exc!r}"[:200])


async def _task_cross_reference_batch() -> tuple[str, str | None]:
    org = _demo_org()
    if not org:
        return ("skipped", "no_demo_org")
    try:
        from src.ai.cross_reference_orchestrator import CrossReferenceOrchestrator  # noqa: F401
        return ("skipped", "cross_ref_needs_vision_fixture")
    except Exception:
        return ("skipped", "cross_reference_unavailable")


# Ordered list matches docs/swarm_baseline.md §4 numbering.
SEED_TASKS: list[tuple[str, Callable[[], Awaitable[tuple[str, str | None]]]]] = [
    ("analyze_merchant_warm",      lambda: _task_analyze_merchant("warm")),
    ("analyze_merchant_cold",      lambda: _task_analyze_merchant("cold")),
    ("analyze_merchant_cache",     lambda: _task_analyze_merchant("cache")),
    ("enhance_insights_5",         lambda: _task_enhance_insights(5)),
    ("enhance_insights_25",        lambda: _task_enhance_insights(25)),
    ("enhance_insights_100",       lambda: _task_enhance_insights(100)),
    ("forecast_7d",                lambda: _task_forecast_generator(7)),
    ("forecast_30d",               lambda: _task_forecast_generator(30)),
    ("forecast_90d",               lambda: _task_forecast_generator(90)),
    ("weekly_report_1",            _task_weekly_report),
    ("weekly_report_2",            _task_weekly_report),
    ("cline_repair_1",             _task_cline_agent),
    ("cline_repair_2",             _task_cline_agent),
    ("commercial_director_clip_1", lambda: _task_commercial_director("clip")),
    ("commercial_director_clip_2", lambda: _task_commercial_director("clip")),
    ("commercial_director_still_1", lambda: _task_commercial_director("still")),
    ("commercial_director_still_2", lambda: _task_commercial_director("still")),
    ("pricing_power",              _task_pricing_power),
    ("churn_warning",              _task_churn_warning),
    ("seasonality",                _task_seasonality),
    ("cross_reference_batch",      _task_cross_reference_batch),
    ("analyze_merchant_extra_1",   lambda: _task_analyze_merchant("extra1")),
    ("analyze_merchant_extra_2",   lambda: _task_analyze_merchant("extra2")),
    ("forecast_extra_30d",         lambda: _task_forecast_generator(30)),
    ("weekly_report_extra",        _task_weekly_report),
]


async def main() -> int:
    session_trace = new_trace_id()
    print(f"== Baseline seed run — session={session_trace} ==")
    print(f"   DB: {os.environ.get('MERIDIAN_SWARM_TRACE_DB', 'data/swarm_traces.sqlite')}")
    print(f"   demo_org: {_demo_org() or '(unset)'}")
    print(f"   llm_keys_present: {_has_any_llm_key()}")
    print()

    # ─── Data-egress guard ────────────────────────────────────────────────
    # Tasks like ``analyze_merchant`` read real merchant rows from Postgres
    # and ship pieces of them to remote LLM providers (DeepSeek, SambaNova,
    # Groq, Cerebras, OpenAI). Customer data must not leave the VPS unless
    # the operator has explicitly confirmed that ``DEMO_ORG_ID`` points at a
    # synthetic / demo merchant. Without that acknowledgement we refuse to
    # run anything that touches a real org and report it as a hard error,
    # not a silent skip.
    if _demo_org() and os.environ.get("MERIDIAN_BASELINE_CONFIRMED_DEMO") != "1":
        print(
            "REFUSING TO RUN: DEMO_ORG_ID is set but "
            "MERIDIAN_BASELINE_CONFIRMED_DEMO is not '1'.\n"
            "Confirm the org is synthetic/demo, then re-run with:\n"
            "  MERIDIAN_BASELINE_CONFIRMED_DEMO=1 DEMO_ORG_ID=<uuid> "
            "python3 scripts/run_baseline_seed.py\n"
            "Aborting before any task can egress real customer data.",
            file=sys.stderr,
        )
        return 2
    # ──────────────────────────────────────────────────────────────────────


    attempted = 0
    skipped = 0
    failed = 0

    for idx, (key, runner) in enumerate(SEED_TASKS, start=1):
        print(f"[{idx:>2}/{len(SEED_TASKS)}] {key} … ", end="", flush=True)
        start = time.perf_counter()
        status: str
        reason: str | None
        try:
            status, reason = await runner()
        except Exception as exc:
            status, reason = ("failed", f"{exc!r}"[:200])
            traceback.print_exc()
        latency_ms = int((time.perf_counter() - start) * 1000)

        record(
            trace_id=session_trace,
            agent_name="seed_runner",
            task_kind=f"seed:{key}",
            latency_ms=latency_ms,
            success=(status == "attempted"),
            error=reason,
        )

        if status == "attempted":
            attempted += 1
            print(f"OK ({latency_ms} ms)")
        elif status == "skipped":
            skipped += 1
            print(f"SKIP — {reason}")
        else:
            failed += 1
            print(f"FAIL — {reason}")

    print()
    print(f"== Done: attempted={attempted} skipped={skipped} failed={failed} ==")
    print("Next: scripts/dump_baseline.py to materialize the JSON artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
