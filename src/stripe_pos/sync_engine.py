"""
Stripe Sync Engine — Orchestrates data flow from Stripe → Meridian.

Two modes (no webhooks in v1 — the scheduler's incremental sweep is the
freshness path):
  1. INITIAL BACKFILL — run once on connect (charges for the backfill window)
  2. INCREMENTAL SYNC — scheduled (new charges since last sync)

Mirrors the Square/Clover engine contract: both modes return a SyncResult; the
CALLER persists it (_write_sync_result for backfill, pos_sync_runner for
incrementals). Backfill folds fatal exceptions into result.errors as
"fatal: …" (the gate _run_*_backfill wrappers check); incremental raises so
the runner's auth-failure handling sees the status code.
"""
import logging
from datetime import datetime, timedelta, timezone

from .client import StripePOSClient
from .mappers import StripePOSMapper
from ..integrations.base.models import SyncProgress, SyncResult

logger = logging.getLogger("meridian.stripe_pos.sync_engine")

# Charges in a non-final or failed state carry no revenue signal.
_INGESTED_STATUSES = {"succeeded"}

_DEFAULT_INCREMENTAL_WINDOW_HOURS = 24 * 7


class StripePOSSyncEngine:
    """
    Usage:
        engine = StripePOSSyncEngine(
            client=StripePOSClient(api_key="…", account_id="acct_…"),
            org_id="…",
            pos_connection_id="…",
        )
        result = await engine.run_initial_backfill()
        result = await engine.run_incremental_sync(since=last_sync_time)
    """

    def __init__(
        self,
        client: StripePOSClient,
        org_id: str,
        pos_connection_id: str,
        on_progress=None,
    ):
        self.client = client
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id
        self.on_progress = on_progress
        self.progress = SyncProgress(pos_connection_id)
        self.mapper = StripePOSMapper(org_id=org_id, pos_connection_id=pos_connection_id)

    def _emit_progress(self):
        if self.on_progress:
            self.on_progress(self.progress)

    async def _collect_charges(self, result: SyncResult, created_gte: int) -> None:
        count = 0
        async for charge in self.client.iter_charges(created_gte=created_gte):
            if charge.get("status") not in _INGESTED_STATUSES:
                continue
            result.transactions.append(self.mapper.map_charge_to_transaction(charge))
            count += 1
            if count % 500 == 0:
                self.progress.update("charges", f"{count} charges fetched", 50.0)
                self._emit_progress()

    async def run_initial_backfill(self, backfill_months: int = 18) -> SyncResult:
        """Full backfill of the charge history. Never raises — fatal errors are
        folded into result.errors as 'fatal: …' for the backfill-wrapper gate."""
        result = SyncResult()
        since = datetime.now(timezone.utc) - timedelta(days=backfill_months * 30)
        self.progress.update("starting", f"Stripe backfill from {since.date()}")
        self._emit_progress()
        try:
            await self._collect_charges(result, created_gte=int(since.timestamp()))
            self.progress.update("done", f"{len(result.transactions)} charges", 100.0)
            self._emit_progress()
        except Exception as e:
            logger.error(f"Stripe backfill failed for org {self.org_id}: {e}", exc_info=True)
            result.errors.append(f"fatal: {e}")
        result.completed_at = datetime.now(timezone.utc)
        return result

    async def run_incremental_sync(self, since: datetime | None = None) -> SyncResult:
        """Charges since the last sync (small default window when unknown).
        Raises on API failure — pos_sync_runner owns error/status handling."""
        result = SyncResult()
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=_DEFAULT_INCREMENTAL_WINDOW_HOURS)
        # Small overlap so a charge landing exactly at the boundary isn't
        # skipped; deterministic ids make the re-ingest an idempotent upsert.
        created_gte = int((since - timedelta(minutes=5)).timestamp())
        await self._collect_charges(result, created_gte=created_gte)
        result.completed_at = datetime.now(timezone.utc)
        return result
