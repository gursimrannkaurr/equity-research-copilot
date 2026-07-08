"""
market_data.py — yfinance wrapper with an in-process TTL cache.

yfinance is an UNOFFICIAL, free, no-API-key wrapper around Yahoo Finance's
public endpoints. It can rate-limit or throttle requests (especially from
datacenter/cloud IPs, which is relevant on serverless deploys — see
docs/DEPLOYMENT.md). This module wraps all yfinance calls so failures are
converted into a typed error rather than an unhandled exception / 500.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

CACHE_TTL_SECONDS = 300  # ~5 minutes

# cache key -> (value, inserted_at_epoch_seconds)
_cache: Dict[Tuple[str, str], Tuple[Any, float]] = {}


class MarketDataError(Exception):
    """Raised when a ticker cannot be resolved or yfinance fails.

    `status_code` lets the FastAPI layer map this to a clean 4xx JSON
    response instead of a 500 stack trace.
    """

    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _cache_get(key: Tuple[str, str]) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, inserted_at = entry
    if time.time() - inserted_at > CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return value


def _cache_set(key: Tuple[str, str], value: Any) -> None:
    _cache[key] = (value, time.time())


def get_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch OHLCV history for `symbol` over `period` (yfinance period
    string, e.g. "1mo", "6mo", "1y", "2y"). Cached for CACHE_TTL_SECONDS.

    Raises MarketDataError (never a raw exception) on failure or an empty
    / invalid ticker result.
    """
    if not symbol or not symbol.strip():
        raise MarketDataError("Ticker symbol is required.", status_code=400)

    symbol = symbol.strip().upper()
    key = (symbol, f"history:{period}")
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period)
    except Exception as exc:  # noqa: BLE001 - intentionally broad, yfinance raises many types
        raise MarketDataError(f"Failed to fetch price history for '{symbol}': {exc}", status_code=502) from exc

    if history is None or history.empty:
        raise MarketDataError(f"No price data found for ticker '{symbol}'. It may be invalid or delisted.", status_code=404)

    _cache_set(key, history)
    return history


def get_info(symbol: str) -> Dict[str, Any]:
    """Fetch the yfinance `.info` fundamentals dict for `symbol`. Cached.

    Raises MarketDataError on failure. Does NOT raise merely because some
    fundamental fields are missing (that's normal and handled downstream
    in analytics.extract_fundamentals via .get()).
    """
    if not symbol or not symbol.strip():
        raise MarketDataError("Ticker symbol is required.", status_code=400)

    symbol = symbol.strip().upper()
    key = (symbol, "info")
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
    except Exception as exc:  # noqa: BLE001
        raise MarketDataError(f"Failed to fetch fundamentals for '{symbol}': {exc}", status_code=502) from exc

    if not info or (isinstance(info, dict) and len(info) <= 1):
        raise MarketDataError(f"No fundamentals data found for ticker '{symbol}'.", status_code=404)

    _cache_set(key, info)
    return info


def clear_cache() -> None:
    """Utility for tests: clear the in-process cache."""
    _cache.clear()
