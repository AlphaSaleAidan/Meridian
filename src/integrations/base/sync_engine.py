from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable

from .models import SyncProgress, SyncResult


class BaseSyncEngine(ABC):
    """Abstract base for POS sync engines.

    Subclasses implement the POS-specific fetch methods.
    The shared orchestration (progress tracking, error handling,
    result aggregation) lives here.
    """

    def __init__(
        self,
        org_id: str,
        pos_connection_id: str | None = None,
        on_progress: Callable[[SyncProgress], Any] | None = None,
    ):
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id
        self.on_progress = on_progress
        self._progress = SyncProgress(pos_connection_id or org_id)

    @abstractmethod
    async def run_initial_backfill(self, **kwargs) -> SyncResult:
        ...

    @abstractmethod
    async def run_incremental_sync(
        self,
        since: datetime | str | None = None,
        **kwargs,
    ) -> SyncResult:
        ...

    def _update_progress(self, phase: str, detail: str, pct: float):
        self._progress.update(phase, detail, pct)
        if self.on_progress:
            self.on_progress(self._progress)
