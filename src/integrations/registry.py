"""POS integration registry — factory for sync engines."""
import logging
from typing import Any

from .base import BaseSyncEngine

logger = logging.getLogger("meridian.integrations.registry")

_REGISTRY: dict[str, type] = {}


def register(pos_type: str, engine_cls: type):
    _REGISTRY[pos_type.lower()] = engine_cls


def get_sync_engine(pos_type: str, **kwargs) -> BaseSyncEngine:
    """Instantiate the correct sync engine for a POS provider.

    >>> engine = get_sync_engine("square", client=sq_client, org_id="abc")
    """
    key = pos_type.lower()
    if key not in _REGISTRY:
        _register_defaults()
    cls = _REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"Unknown POS type: {pos_type}. Available: {list(_REGISTRY)}")
    return cls(**kwargs)


def _register_defaults():
    """Lazy-register built-in engines to avoid circular imports."""
    if _REGISTRY:
        return
    try:
        from ..square.sync_engine import SyncEngine
        register("square", SyncEngine)
    except ImportError:
        logger.debug("Square sync engine not available")
    try:
        from ..clover.sync_engine import CloverSyncEngine
        register("clover", CloverSyncEngine)
    except ImportError:
        logger.debug("Clover sync engine not available")
