"""
analytics.py — Rule-based analytics engine for Equity Research Copilot.

All functions are pure / deterministic given a pandas OHLCV DataFrame
(as returned by yfinance's `Ticker.history()`) and/or a fundamentals
dict (as returned by yfinance's `Ticker.info`). No network calls happen
in this module — that keeps it fully unit-testable offline.

RSI METHOD NOTE (documented per spec, mirrored in docs/ARCHITECTURE.md):
We use the SIMPLE ROLLING AVERAGE method (not Wilder smoothing) for RSI(14):
    RSI = 100 - (100 / (1 + RS))
    RS  = simple rolling mean of gains over N periods / simple rolling
          mean of losses over N periods (both means computed with a plain
          rolling window, not an exponential/Wilder smoothed average).
We chose the simple rolling-average method over Wilder smoothing because
it is easier to hand-verify in unit tests (no recursive/exponential state)
and the difference in practice is small for a portfolio-grade tool that is
explicitly not for high-frequency trading decisions.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
import math

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Sector -> peer ticker map (hardcoded, zero-cost, no dynamic sector lookup)
# ---------------------------------------------------------------------------
SECTOR_PEER_MAP: Dict[str, List[str]] = {
    "tech": ["AAPL", "MSFT", "GOOGL"],
    "banking": ["JPM", "BAC"],
    "auto": ["TSLA", "F"],
    "fmcg": ["PG", "KO"],
}


# ---------------------------------------------------------------------------
# Price-history based metrics
# ---------------------------------------------------------------------------

def compute_returns(history: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Compute trailing 1-month, 6-month, and 1-year total returns.

    Returns are computed as (last_close / close_N_periods_ago) - 1, using
    trading-day approximations: 1M ~= 21 trading days, 6M ~= 126, 1Y ~= 252.
    If the history DataFrame does not contain enough rows for a given
    window, that key's value is None (never raises).
    """
    result: Dict[str, Optional[float]] = {"return_1m": None, "return_6m": None, "return_1y": None}
    if history is None or history.empty or "Close" not in history.columns:
        return result

    close = history["Close"].dropna()
    if len(close) < 2:
        return result

    last = close.iloc[-1]
    windows = {"return_1m": 21, "return_6m": 126, "return_1y": 252}
    for key, window in windows.items():
        if len(close) > window:
            base = close.iloc[-(window + 1)]
            if base and base != 0:
                result[key] = float(last / base - 1.0)
    return result


def compute_volatility(history: pd.DataFrame, window: int = 21) -> Optional[float]:
    """Rolling annualized volatility.

    Computed as the standard deviation of daily pct-change returns over the
    most recent `window` trading days, annualized by multiplying by
    sqrt(252) (the standard trading-days-per-year approximation).
    Returns None if there isn't enough data (<2 return observations).
    """
    if history is None or history.empty or "Close" not in history.columns:
        return None
    close = history["Close"].dropna()
    returns = close.pct_change().dropna()
    if len(returns) < 2:
        return None
    recent = returns.tail(window)
    if len(recent) < 2:
        return None
    daily_std = recent.std(ddof=1)
    if daily_std is None or (isinstance(daily_std, float) and math.isnan(daily_std)):
        return None
    return float(daily_std * math.sqrt(252))


def compute_sma(history: pd.DataFrame, window: int) -> Optional[float]:
    """Simple moving average of Close over the last `window` sessions.

    Returns None if there are fewer than `window` closing prices available.
    """
    if history is None or history.empty or "Close" not in history.columns:
        return None
    close = history["Close"].dropna()
    if len(close) < window:
        return None
    return float(close.tail(window).mean())


def compute_golden_cross(sma_50: Optional[float], sma_200: Optional[float]) -> Optional[bool]:
    """True if SMA(50) > SMA(200) ("golden cross" regime), False if it is a
    "death cross" regime (SMA50 <= SMA200). None if either input is missing.
    """
    if sma_50 is None or sma_200 is None:
        return None
    return bool(sma_50 > sma_200)


def compute_max_drawdown(history: pd.DataFrame) -> Optional[float]:
    """Maximum peak-to-trough drawdown over the full supplied history,
    expressed as a negative fraction (e.g. -0.35 == -35%).

    Computed as min over t of (price_t / running_max_price_t - 1).
    Returns None if there's no price data.
    """
    if history is None or history.empty or "Close" not in history.columns:
        return None
    close = history["Close"].dropna()
    if close.empty:
        return None
    running_max = close.cummax()
    drawdown = close / running_max - 1.0
    dd_min = drawdown.min()
    if dd_min is None or (isinstance(dd_min, float) and math.isnan(dd_min)):
        return None
    return float(dd_min)


def compute_rsi(history: pd.DataFrame, period: int = 14) -> Optional[float]:
    """RSI(14) using the SIMPLE ROLLING AVERAGE method (see module docstring
    for rationale vs. Wilder smoothing).

    Steps:
      1. delta = Close.diff()
      2. gains = delta.clip(lower=0); losses = -delta.clip(upper=0)
      3. avg_gain = simple rolling mean of gains over `period`
         avg_loss = simple rolling mean of losses over `period`
      4. RS = avg_gain / avg_loss
      5. RSI = 100 - 100 / (1 + RS)
         Special cases: if avg_loss == 0 and avg_gain > 0 -> RSI = 100
                        if avg_loss == 0 and avg_gain == 0 -> RSI = 50 (flat/no movement)

    Returns the most recent RSI value, or None if there isn't enough data.
    """
    if history is None or history.empty or "Close" not in history.columns:
        return None
    close = history["Close"].dropna()
    if len(close) < period + 1:
        return None

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()

    last_avg_gain = avg_gain.iloc[-1]
    last_avg_loss = avg_loss.iloc[-1]

    if pd.isna(last_avg_gain) or pd.isna(last_avg_loss):
        return None

    if last_avg_loss == 0:
        return 100.0 if last_avg_gain > 0 else 50.0

    rs = last_avg_gain / last_avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi)


def compute_price_metrics(history: pd.DataFrame) -> Dict[str, Any]:
    """Bundle of all price-history-derived metrics used across the app."""
    returns = compute_returns(history)
    sma_50 = compute_sma(history, 50)
    sma_200 = compute_sma(history, 200)
    last_close = None
    if history is not None and not history.empty and "Close" in history.columns:
        closes = history["Close"].dropna()
        if not closes.empty:
            last_close = float(closes.iloc[-1])

    metrics: Dict[str, Any] = {
        "last_close": last_close,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "golden_cross": compute_golden_cross(sma_50, sma_200),
        "volatility_annualized": compute_volatility(history),
        "max_drawdown": compute_max_drawdown(history),
        "rsi_14": compute_rsi(history),
    }
    metrics.update(returns)
    return metrics


# ---------------------------------------------------------------------------
# Fundamentals extraction (from yfinance .info dict)
# ---------------------------------------------------------------------------

FUNDAMENTAL_FIELDS = {
    "trailing_pe": "trailingPE",
    "forward_pe": "forwardPE",
    "price_to_book": "priceToBook",
    "trailing_eps": "trailingEps",
    "market_cap": "marketCap",
    "profit_margin": "profitMargins",
    "roe": "returnOnEquity",
    "debt_to_equity": "debtToEquity",
    "revenue_growth": "revenueGrowth",
    "earnings_growth": "earningsGrowth",
}


def extract_fundamentals(info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract a stable, minimal set of fundamentals from yfinance's `.info`
    dict. Uses `.get(key)` throughout with default None so missing fields
    (which are common and vary by ticker/exchange) never raise.
    """
    info = info or {}
    out: Dict[str, Any] = {}
    for out_key, info_key in FUNDAMENTAL_FIELDS.items():
        out[out_key] = info.get(info_key)
    out["short_name"] = info.get("shortName")
    out["sector"] = info.get("sector")
    out["industry"] = info.get("industry")
    out["currency"] = info.get("currency")
    return out


# ---------------------------------------------------------------------------
# Peer comparison
# ---------------------------------------------------------------------------

def resolve_peers(sector: Optional[str], explicit_peers: Optional[List[str]] = None) -> List[str]:
    """Resolve the peer ticker list. Explicit peers (if provided) always
    override the hardcoded sector map. Sector matching is case-insensitive
    substring match against SECTOR_PEER_MAP keys; unknown sector -> [].
    """
    if explicit_peers:
        return [p.strip().upper() for p in explicit_peers if p.strip()]
    if not sector:
        return []
    sector_lower = sector.lower()
    for key, peers in SECTOR_PEER_MAP.items():
        if key in sector_lower or sector_lower in key:
            return list(peers)
    return []


def build_ratio_table(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a peer comparison ratio table.

    `rows` is a list of dicts, each with at least:
        {"symbol": str, "fundamentals": {...extract_fundamentals output...}}

    Returns a list of flat dict rows suitable for direct JSON/table
    rendering: symbol, pe, forward_pe, pb, roe, margin, market_cap.
    """
    table: List[Dict[str, Any]] = []
    for row in rows:
        symbol = row.get("symbol")
        f = row.get("fundamentals") or {}
        table.append({
            "symbol": symbol,
            "trailing_pe": f.get("trailing_pe"),
            "forward_pe": f.get("forward_pe"),
            "price_to_book": f.get("price_to_book"),
            "roe": f.get("roe"),
            "profit_margin": f.get("profit_margin"),
            "market_cap": f.get("market_cap"),
            "debt_to_equity": f.get("debt_to_equity"),
        })
    return table


# ---------------------------------------------------------------------------
# Composite health score (0-100)
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def score_valuation(target_pe: Optional[float], peer_pes: List[Optional[float]]) -> Dict[str, Any]:
    """Valuation sub-score (0-100), weight 30% of total.

    Method:
      - Gather valid (non-None, > 0) peer P/E values into `peer_valid`.
      - If target_pe is None or <= 0, OR there are no valid peer P/E values:
            score = 50 (neutral), reason recorded.
      - Else:
            peer_avg_pe = mean(peer_valid)
            ratio = target_pe / peer_avg_pe
            score = 100 - (ratio - 1) * 100, i.e. trading exactly at peer
            average -> 50... wait, see below for exact curve actually used.

    EXACT SCORING CURVE (documented, matches docs/ARCHITECTURE.md verbatim):
      score = clamp(100 - (ratio * 50), 0, 100)
      where ratio = target_pe / peer_avg_pe.
      - ratio = 1.0 (trading at peer average)      -> score = 50
      - ratio = 0.5 (trading at half peer average)  -> score = 75  (cheaper -> higher score)
      - ratio = 2.0 (trading at 2x peer average)     -> score = 0   (expensive -> lower score)
      - ratio = 0.0 (near-zero P/E)                  -> score = 100 (clamped)
    Lower relative P/E scores higher (cheaper valuation vs peers = better score).
    """
    peer_valid = [p for p in peer_pes if p is not None and p > 0]
    if target_pe is None or target_pe <= 0 or not peer_valid:
        return {"score": 50.0, "reason": "P/E missing or negative for target or no valid peer P/E data; neutral score applied."}

    peer_avg_pe = sum(peer_valid) / len(peer_valid)
    if peer_avg_pe <= 0:
        return {"score": 50.0, "reason": "Peer average P/E is non-positive; neutral score applied."}

    ratio = target_pe / peer_avg_pe
    score = _clamp(100.0 - (ratio * 50.0))
    return {"score": score, "reason": f"Target P/E {target_pe:.2f} vs peer average {peer_avg_pe:.2f} (ratio {ratio:.2f})."}


def score_momentum(last_close: Optional[float], sma_50: Optional[float], sma_200: Optional[float],
                    rsi_14: Optional[float]) -> Dict[str, Any]:
    """Momentum sub-score (0-100), weight 35% of total.

    Composed of two equally-weighted components (each 0-100, averaged):

    (a) Trend component (price vs SMAs):
        - price > sma_50 AND price > sma_200  -> 100
        - price > sma_50 XOR price > sma_200   -> 60
        - price < sma_50 AND price < sma_200   -> 20
        - any required input missing            -> 50 (neutral)

    (b) RSI banding component:
        - RSI in [40, 60]              -> 100 (healthy neutral momentum)
        - RSI in [30, 40) or (60, 70]  -> 70  (mildly oversold/overbought)
        - RSI < 30                     -> 40  (oversold - risk of further weakness
                                                 despite potential bounce)
        - RSI > 70                     -> 40  (overbought - risk of pullback)
        - RSI missing                  -> 50 (neutral)

    Final momentum score = average(trend_component, rsi_component), clamped [0,100].
    """
    if last_close is None or sma_50 is None or sma_200 is None:
        trend_component = 50.0
    else:
        above_50 = last_close > sma_50
        above_200 = last_close > sma_200
        if above_50 and above_200:
            trend_component = 100.0
        elif above_50 or above_200:
            trend_component = 60.0
        else:
            trend_component = 20.0

    if rsi_14 is None:
        rsi_component = 50.0
    elif 40 <= rsi_14 <= 60:
        rsi_component = 100.0
    elif 30 <= rsi_14 < 40 or 60 < rsi_14 <= 70:
        rsi_component = 70.0
    else:
        rsi_component = 40.0

    score = _clamp((trend_component + rsi_component) / 2.0)
    return {
        "score": score,
        "trend_component": trend_component,
        "rsi_component": rsi_component,
        "reason": f"Trend component {trend_component}, RSI component {rsi_component} (RSI={rsi_14}).",
    }


def score_profitability(profit_margin: Optional[float], roe: Optional[float]) -> Dict[str, Any]:
    """Profitability sub-score (0-100), weight 35% of total.

    Composed of two equally-weighted components (each 0-100, averaged):

    (a) Profit margin component (yfinance `profitMargins`, a fraction e.g. 0.25 = 25%):
        - margin >= 0.20        -> 100
        - 0.10 <= margin < 0.20 -> 75
        - 0.00 <= margin < 0.10 -> 50
        - margin < 0.00 (loss)  -> 20
        - missing               -> 50 (neutral)

    (b) ROE component (yfinance `returnOnEquity`, a fraction e.g. 0.15 = 15%):
        - roe >= 0.20        -> 100
        - 0.10 <= roe < 0.20 -> 75
        - 0.00 <= roe < 0.10 -> 50
        - roe < 0.00         -> 20
        - missing            -> 50 (neutral)

    Final profitability score = average(margin_component, roe_component), clamped [0,100].
    """
    def bucket(value: Optional[float]) -> float:
        if value is None:
            return 50.0
        if value >= 0.20:
            return 100.0
        if value >= 0.10:
            return 75.0
        if value >= 0.00:
            return 50.0
        return 20.0

    margin_component = bucket(profit_margin)
    roe_component = bucket(roe)
    score = _clamp((margin_component + roe_component) / 2.0)
    return {
        "score": score,
        "margin_component": margin_component,
        "roe_component": roe_component,
        "reason": f"Margin component {margin_component} (margin={profit_margin}), ROE component {roe_component} (roe={roe}).",
    }


VALUATION_WEIGHT = 0.30
MOMENTUM_WEIGHT = 0.35
PROFITABILITY_WEIGHT = 0.35


def compute_health_score(
    target_pe: Optional[float],
    peer_pes: List[Optional[float]],
    last_close: Optional[float],
    sma_50: Optional[float],
    sma_200: Optional[float],
    rsi_14: Optional[float],
    profit_margin: Optional[float],
    roe: Optional[float],
) -> Dict[str, Any]:
    """Composite health score (0-100).

    Final = clamp(
        0.30 * valuation_score +
        0.35 * momentum_score +
        0.35 * profitability_score,
        0, 100
    )

    See score_valuation, score_momentum, score_profitability docstrings for
    each sub-score's exact formula. This EXACT weighting (30/35/35) and each
    sub-formula is mirrored verbatim in docs/ARCHITECTURE.md — if you change
    a formula here, update that doc too.
    """
    valuation = score_valuation(target_pe, peer_pes)
    momentum = score_momentum(last_close, sma_50, sma_200, rsi_14)
    profitability = score_profitability(profit_margin, roe)

    final = _clamp(
        VALUATION_WEIGHT * valuation["score"]
        + MOMENTUM_WEIGHT * momentum["score"]
        + PROFITABILITY_WEIGHT * profitability["score"]
    )

    return {
        "final_score": round(final, 1),
        "valuation": valuation,
        "momentum": momentum,
        "profitability": profitability,
        "weights": {
            "valuation": VALUATION_WEIGHT,
            "momentum": MOMENTUM_WEIGHT,
            "profitability": PROFITABILITY_WEIGHT,
        },
    }
