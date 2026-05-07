"""
Persistent agent memory via mem0.

Stores merchant-specific patterns, preferences, and historical context
so agents can recall previous analysis results and improve over time.
Falls back to a simple dict cache when mem0 is not installed.
"""
import logging
import os
from typing import Any

logger = logging.getLogger("meridian.ai.agent_memory")

MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")

_mem0_available = False
try:
    from mem0 import Memory
    _mem0_available = True
except ImportError:
    logger.info("mem0 not installed — using in-memory fallback")


class AgentMemory:
    """Persistent memory for Meridian agents, keyed by merchant_id + agent_name."""

    def __init__(self):
        self._client = None
        self._fallback: dict[str, list[dict]] = {}
        if _mem0_available and MEM0_API_KEY:
            try:
                self._client = Memory.from_config({
                    "llm": {
                        "provider": "openai",
                        "config": {"model": "gpt-4o-mini", "temperature": 0.1},
                    },
                    "version": "v1.1",
                })
                logger.info("mem0 agent memory initialized")
            except Exception as e:
                logger.warning(f"mem0 init failed: {e}")

    def store(self, merchant_id: str, agent_name: str, content: str, metadata: dict | None = None):
        user_id = f"{merchant_id}:{agent_name}"
        if self._client:
            try:
                self._client.add(content, user_id=user_id, metadata=metadata or {})
                return
            except Exception as e:
                logger.warning(f"mem0 store failed: {e}")
        self._fallback.setdefault(user_id, []).append({"content": content, "metadata": metadata or {}})

    def recall(self, merchant_id: str, agent_name: str, query: str, limit: int = 5) -> list[dict]:
        user_id = f"{merchant_id}:{agent_name}"
        if self._client:
            try:
                results = self._client.search(query, user_id=user_id, limit=limit)
                return [
                    {"content": r.get("memory", r.get("text", "")), "metadata": r.get("metadata", {})}
                    for r in results.get("results", results)
                    if isinstance(r, dict)
                ]
            except Exception as e:
                logger.warning(f"mem0 recall failed: {e}")
        entries = self._fallback.get(user_id, [])
        q_lower = query.lower()
        matched = [e for e in entries if q_lower in e["content"].lower()]
        return matched[:limit] if matched else entries[-limit:]

    def get_all(self, merchant_id: str, agent_name: str) -> list[dict]:
        user_id = f"{merchant_id}:{agent_name}"
        if self._client:
            try:
                results = self._client.get_all(user_id=user_id)
                return [
                    {"content": r.get("memory", r.get("text", "")), "metadata": r.get("metadata", {})}
                    for r in results.get("results", results)
                    if isinstance(r, dict)
                ]
            except Exception as e:
                logger.warning(f"mem0 get_all failed: {e}")
        return self._fallback.get(user_id, [])

    def forget(self, merchant_id: str, agent_name: str):
        user_id = f"{merchant_id}:{agent_name}"
        if self._client:
            try:
                memories = self._client.get_all(user_id=user_id)
                for m in memories.get("results", memories):
                    if isinstance(m, dict) and "id" in m:
                        self._client.delete(m["id"])
                return
            except Exception as e:
                logger.warning(f"mem0 forget failed: {e}")
        self._fallback.pop(user_id, None)

    @property
    def is_connected(self) -> bool:
        return self._client is not None


_shared_memory: AgentMemory | None = None


def get_agent_memory() -> AgentMemory:
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = AgentMemory()
    return _shared_memory
