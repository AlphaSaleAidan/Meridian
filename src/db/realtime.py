"""
Supabase Realtime — Subscribe to table changes for live dashboard updates.

Uses Supabase's Realtime channels to push INSERT/UPDATE events to connected
clients via the EventBus (Redis pub/sub). Falls back gracefully when
supabase-py or the Realtime server is unavailable.
"""
import asyncio
import logging
import os
from typing import Callable

logger = logging.getLogger("meridian.db.realtime")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


class RealtimeSubscriber:
    """Manages Supabase Realtime subscriptions for an org."""

    def __init__(self):
        self._client = None
        self._channels: dict[str, object] = {}
        self._running = False

    async def connect(self) -> bool:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            logger.warning("Supabase Realtime: missing URL or key")
            return False
        try:
            from supabase import acreate_client
            self._client = await acreate_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            self._running = True
            logger.info("Supabase Realtime connected")
            return True
        except ImportError:
            logger.warning("supabase-py not installed — Realtime disabled")
            return False
        except Exception as e:
            logger.warning("Supabase Realtime connect failed: %s", e)
            return False

    async def subscribe_table(
        self,
        table: str,
        org_id: str,
        callback: Callable[[dict], None],
        event: str = "INSERT",
    ) -> bool:
        if not self._client:
            return False
        channel_key = f"{table}:{org_id}"
        if channel_key in self._channels:
            return True
        try:
            channel = self._client.channel(channel_key)
            channel.on_postgres_changes(
                event,
                schema="public",
                table=table,
                filter=f"org_id=eq.{org_id}",
                callback=callback,
            )
            await channel.subscribe()
            self._channels[channel_key] = channel
            logger.info("Subscribed to %s changes for org %s", table, org_id)
            return True
        except Exception as e:
            logger.warning("Realtime subscribe failed for %s: %s", channel_key, e)
            return False

    async def unsubscribe(self, table: str, org_id: str):
        channel_key = f"{table}:{org_id}"
        channel = self._channels.pop(channel_key, None)
        if channel:
            try:
                await channel.unsubscribe()
            except Exception:
                pass

    async def close(self):
        self._running = False
        for key in list(self._channels):
            channel = self._channels.pop(key)
            try:
                await channel.unsubscribe()
            except Exception:
                pass


_subscriber: RealtimeSubscriber | None = None


def get_realtime() -> RealtimeSubscriber:
    global _subscriber
    if _subscriber is None:
        _subscriber = RealtimeSubscriber()
    return _subscriber


async def subscribe_org_events(org_id: str):
    """Subscribe to transaction + inventory changes for an org, publishing to EventBus."""
    from .cache import event_bus

    rt = get_realtime()
    if not rt._client:
        connected = await rt.connect()
        if not connected:
            return

    def on_transaction(payload: dict):
        event_bus.publish_order(org_id, "transaction.realtime", payload.get("new", {}))

    def on_inventory(payload: dict):
        event_bus.publish_inventory(org_id, payload.get("new", {}))

    await rt.subscribe_table("transactions", org_id, on_transaction, "INSERT")
    await rt.subscribe_table("inventory_snapshots", org_id, on_inventory, "*")
