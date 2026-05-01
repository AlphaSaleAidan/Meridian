"""
Market Data Service — Economic indicators via OpenBB.

Pulls CPI, consumer spending, unemployment, and sector performance.
Cached daily to avoid redundant API calls.
Feeds into benchmark and forecaster agents.
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

logger = logging.getLogger("meridian.economics")

_cache: dict[str, Any] = {}
_cache_expiry: dict[str, datetime] = {}
CACHE_TTL = timedelta(hours=24)


def _is_cached(key: str) -> bool:
    expiry = _cache_expiry.get(key)
    if expiry and datetime.now(timezone.utc) < expiry:
        return True
    return False


def _set_cache(key: str, value: Any):
    _cache[key] = value
    _cache_expiry[key] = datetime.now(timezone.utc) + CACHE_TTL


def get_cpi(start_date: Optional[str] = None) -> list[dict]:
    """Get Consumer Price Index data."""
    if _is_cached("cpi"):
        return _cache["cpi"]

    try:
        from openbb import obb
        result = obb.economy.cpi(
            country="united_states",
            frequency="monthly",
        )
        data = [
            {"date": str(row.date), "value": row.value}
            for row in result.results
        ]
        _set_cache("cpi", data)
        return data
    except Exception as e:
        logger.error(f"Failed to fetch CPI data: {e}")
        return []


def get_consumer_spending() -> list[dict]:
    """Get personal consumption expenditure data."""
    if _is_cached("consumer_spending"):
        return _cache["consumer_spending"]

    try:
        from openbb import obb
        result = obb.economy.fred_series(
            symbol="PCE",
            start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        )
        data = [
            {"date": str(row.date), "value": row.value}
            for row in result.results
        ]
        _set_cache("consumer_spending", data)
        return data
    except Exception as e:
        logger.error(f"Failed to fetch consumer spending: {e}")
        return []


def get_unemployment() -> list[dict]:
    """Get unemployment rate."""
    if _is_cached("unemployment"):
        return _cache["unemployment"]

    try:
        from openbb import obb
        result = obb.economy.fred_series(
            symbol="UNRATE",
            start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        )
        data = [
            {"date": str(row.date), "value": row.value}
            for row in result.results
        ]
        _set_cache("unemployment", data)
        return data
    except Exception as e:
        logger.error(f"Failed to fetch unemployment data: {e}")
        return []


def get_sector_performance(sector: str = "consumer_discretionary") -> list[dict]:
    """Get sector ETF performance data."""
    if _is_cached(f"sector_{sector}"):
        return _cache[f"sector_{sector}"]

    sector_etfs = {
        "consumer_discretionary": "XLY",
        "consumer_staples": "XLP",
        "restaurants": "EATZ",
        "retail": "XRT",
    }

    symbol = sector_etfs.get(sector, "XLY")

    try:
        from openbb import obb
        result = obb.equity.price.historical(
            symbol=symbol,
            start_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            provider="yfinance",
        )
        data = [
            {
                "date": str(row.date),
                "close": row.close,
                "volume": row.volume,
            }
            for row in result.results
        ]
        _set_cache(f"sector_{sector}", data)
        return data
    except Exception as e:
        logger.error(f"Failed to fetch sector performance for {sector}: {e}")
        return []


def get_economic_context(business_vertical: str = "restaurant") -> dict[str, Any]:
    """Get all economic indicators relevant to a business vertical.

    Returns a dict suitable for injection into benchmark/forecaster agents.
    """
    sector_map = {
        "restaurant": "restaurants",
        "cafe": "restaurants",
        "smoke_shop": "consumer_discretionary",
        "retail": "retail",
    }
    sector = sector_map.get(business_vertical, "consumer_discretionary")

    return {
        "cpi": get_cpi(),
        "consumer_spending": get_consumer_spending(),
        "unemployment": get_unemployment(),
        "sector_performance": get_sector_performance(sector),
        "vertical": business_vertical,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
