"""
Token-bucket rate limiter for Square API calls.

Square limits:
  - Standard endpoints: ~10 req/s per application
  - Batch / SearchOrders: ~5 req/s
We stay safely under with 8 req/s standard, 4 req/s batch.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Async token-bucket rate limiter."""

    rate: float              # tokens added per second
    capacity: float          # max burst size
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0) -> float:
        """Block until *tokens* are available. Returns seconds waited."""
        waited = 0.0
        async with self._lock:
            self._refill()
            while self._tokens < tokens:
                deficit = tokens - self._tokens
                sleep_for = deficit / self.rate
                waited += sleep_for
                await asyncio.sleep(sleep_for)
                self._refill()
            self._tokens -= tokens
        return waited


class SquareRateLimiter:
    """Facade that exposes separate buckets for standard and batch calls."""

    def __init__(
        self,
        standard_rate: float = 8.0,
        batch_rate: float = 4.0,
        standard_burst: float = 10.0,
        batch_burst: float = 5.0,
    ) -> None:
        self.standard = TokenBucket(rate=standard_rate, capacity=standard_burst)
        self.batch = TokenBucket(rate=batch_rate, capacity=batch_burst)

    async def acquire_standard(self) -> float:
        return await self.standard.acquire()

    async def acquire_batch(self) -> float:
        return await self.batch.acquire()
