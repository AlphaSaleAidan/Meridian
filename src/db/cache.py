import hashlib
import json
import logging
import os
import time
from typing import Any

import redis

logger = logging.getLogger("meridian.cache")

TTL_FAST = 30
TTL_SLOW = 300

REDIS_URL = os.environ.get("REDIS_CACHE_URL", "redis://localhost:6379/1")


class RedisTTLCache:
    """Redis-backed TTL cache for dashboard queries. Falls back to in-memory."""

    def __init__(self, redis_url: str = REDIS_URL, prefix: str = "dash"):
        self._prefix = prefix
        self._fallback: dict[str, tuple[float, Any]] = {}
        try:
            self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            self._use_redis = True
            logger.info("Cache connected to Redis")
        except Exception:
            self._redis = None
            self._use_redis = False
            logger.warning("Redis unavailable — using in-memory fallback")

    def _rkey(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any | None:
        if self._use_redis:
            try:
                raw = self._redis.get(self._rkey(key))
                if raw is None:
                    return None
                return json.loads(raw)
            except Exception:
                pass

        entry = self._fallback.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._fallback[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int):
        if self._use_redis:
            try:
                self._redis.setex(self._rkey(key), ttl_seconds, json.dumps(value, default=str))
                return
            except Exception:
                pass

        self._fallback[key] = (time.monotonic() + ttl_seconds, value)
        if len(self._fallback) > 1000:
            self._evict_expired()

    def _evict_expired(self):
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._fallback.items() if now > exp]
        for k in expired:
            del self._fallback[k]

    def invalidate(self, prefix: str = ""):
        if self._use_redis:
            try:
                pattern = f"{self._prefix}:{prefix}*" if prefix else f"{self._prefix}:*"
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=200)
                    if keys:
                        self._redis.delete(*keys)
                    if cursor == 0:
                        break
                return
            except Exception:
                pass

        if not prefix:
            self._fallback.clear()
            return
        keys = [k for k in self._fallback if k.startswith(prefix)]
        for k in keys:
            del self._fallback[k]

    def invalidate_org(self, org_id: str):
        if self._use_redis:
            try:
                pattern = f"{self._prefix}:*:{org_id}:*"
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=200)
                    if keys:
                        self._redis.delete(*keys)
                    if cursor == 0:
                        break
                return
            except Exception:
                pass

        keys = [k for k in self._fallback if f":{org_id}:" in k]
        for k in keys:
            del self._fallback[k]

    @staticmethod
    def make_key(endpoint: str, org_id: str, **params) -> str:
        parts = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
        suffix = hashlib.md5(parts.encode()).hexdigest()[:8] if parts else "0"
        return f"{endpoint}:{org_id}:{suffix}"


dashboard_cache = RedisTTLCache()


class EventBus:
    """Redis pub/sub for real-time order and webhook events."""

    CHANNEL_ORDER = "meridian:orders"
    CHANNEL_INVENTORY = "meridian:inventory"
    CHANNEL_ALERT = "meridian:alerts"

    def __init__(self, redis_url: str = REDIS_URL):
        try:
            self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            self._available = True
        except Exception:
            self._redis = None
            self._available = False
            logger.warning("EventBus: Redis unavailable — events will not be published")

    def publish(self, channel: str, event: dict) -> int:
        if not self._available:
            return 0
        try:
            return self._redis.publish(channel, json.dumps(event, default=str))
        except Exception as e:
            logger.debug("EventBus publish failed: %s", e)
            return 0

    def publish_order(self, org_id: str, event_type: str, data: dict | None = None):
        self.publish(self.CHANNEL_ORDER, {
            "org_id": org_id,
            "type": event_type,
            "data": data or {},
            "ts": time.time(),
        })

    def publish_inventory(self, org_id: str, data: dict | None = None):
        self.publish(self.CHANNEL_INVENTORY, {
            "org_id": org_id,
            "type": "inventory.updated",
            "data": data or {},
            "ts": time.time(),
        })

    def publish_alert(self, org_id: str, title: str, priority: str = "normal"):
        self.publish(self.CHANNEL_ALERT, {
            "org_id": org_id,
            "type": "alert",
            "title": title,
            "priority": priority,
            "ts": time.time(),
        })


event_bus = EventBus()
