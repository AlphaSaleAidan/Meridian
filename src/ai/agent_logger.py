"""
Structured JSON logging for Meridian AI agents.

Writes JSON-lines to logs/agents/{agent_name}.log so Evolver
can scan for signals (errors, warnings, patterns).

Also tees per-agent-run metadata (name, latency, success) into the
``swarm_traces`` SQLite table via ``src/ai/trace_recorder.py``. The JSONL log
remains the primary detail log; the SQLite tee is the structured baseline
view the ML eval harness will compare against.
"""
import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Trace recorder is no-op-safe — failure to import or write must never break
# the agent loop. Import lazily inside the helpers so a missing file or DB
# error stays contained.

LOG_DIR = Path(os.environ.get("MERIDIAN_AGENT_LOG_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "logs", "agents")))


class AgentJsonHandler(logging.Handler):
    """Writes JSON-lines to a per-agent log file."""

    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = LOG_DIR / f"{agent_name}.log"

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": self.agent_name,
                "level": record.levelname.lower(),
                "event": getattr(record, "event", record.funcName or "log"),
                "message": record.getMessage(),
            }
            if record.exc_info and record.exc_info[1]:
                entry["error"] = str(record.exc_info[1])
            ctx = getattr(record, "context", None)
            if ctx:
                entry["context"] = ctx
            mid = getattr(record, "merchant_id", None)
            if mid:
                entry["merchant_id"] = mid
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get a logger with both console and JSON file output for an agent."""
    logger = logging.getLogger(f"meridian.agents.{agent_name}")
    if not any(isinstance(h, AgentJsonHandler) for h in logger.handlers):
        logger.addHandler(AgentJsonHandler(agent_name))
    return logger


def record_agent_run(
    agent_name: str,
    *,
    latency_ms: int,
    success: bool,
    error: str | None = None,
    task_kind: str = "agent_run",
    trace_id: str | None = None,
) -> None:
    """Write one swarm_traces row for an agent invocation. Never raises."""
    try:
        from .trace_recorder import record as _trace_record, new_trace_id as _new_trace_id
        _trace_record(
            trace_id=trace_id or _new_trace_id(),
            agent_name=agent_name,
            tier=None,            # tier resolver lands in Step 3
            provider=None,        # statistical agents do not call an LLM
            model=None,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=int(latency_ms or 0),
            success=success,
            task_kind=task_kind,
            error=(error[:500] if error else None),
        )
    except Exception:
        pass


@contextmanager
def agent_run_tracer(agent_name: str, *, task_kind: str = "agent_run", trace_id: str | None = None):
    """Time an agent invocation and tee a swarm_traces row on exit.

    The JSONL log emitted by ``AgentJsonHandler`` already captures the
    detailed event stream; this context manager is the additional structured
    row the baseline aggregator reads.
    """
    start = time.perf_counter()
    err: str | None = None
    ok = True
    try:
        yield
    except Exception as exc:
        ok = False
        err = repr(exc)[:500]
        raise
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        record_agent_run(
            agent_name,
            latency_ms=latency_ms,
            success=ok,
            error=err,
            task_kind=task_kind,
            trace_id=trace_id,
        )
