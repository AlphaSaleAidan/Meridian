import logging
from datetime import datetime, timezone

logger = logging.getLogger("meridian.integrations")


class SyncProgress:
    """Tracks sync progress for UI display."""

    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.phase: str = "starting"
        self.detail: str = ""
        self.progress_pct: float = 0.0
        self.items_synced: int = 0
        self.errors: list[str] = []

    def update(self, phase: str, detail: str = "", progress_pct: float = 0.0):
        self.phase = phase
        self.detail = detail
        self.progress_pct = progress_pct
        logger.info(f"[{self.connection_id}] Sync: {phase} — {detail} ({progress_pct:.0f}%)")

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "detail": self.detail,
            "progress_pct": self.progress_pct,
            "items_synced": self.items_synced,
            "errors": self.errors[-10:],
        }


class SyncResult:
    """Result of a sync operation."""

    def __init__(self):
        self.locations: list[dict] = []
        self.categories: list[dict] = []
        self.products: list[dict] = []
        self.transactions: list[dict] = []
        self.transaction_items: list[dict] = []
        self.inventory_snapshots: list[dict] = []
        self.employee_cache: dict[str, str] = {}
        self.errors: list[str] = []
        self.started_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    @property
    def summary(self) -> dict:
        return {
            "locations": len(self.locations),
            "categories": len(self.categories),
            "products": len(self.products),
            "transactions": len(self.transactions),
            "transaction_items": len(self.transaction_items),
            "inventory_snapshots": len(self.inventory_snapshots),
            "employees_cached": len(self.employee_cache),
            "errors": len(self.errors),
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at
                else None
            ),
        }
