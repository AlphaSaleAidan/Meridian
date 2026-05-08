"""
Structured JSON logging for Meridian AI agents.

Writes JSON-lines to logs/agents/{agent_name}.log so Evolver
can scan for signals (errors, warnings, patterns).
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

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
