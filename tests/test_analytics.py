"""
test_analytics.py — pytest suite for api/analytics.py.

Uses hand-constructed synthetic pandas DataFrames only. NO network calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import analytics  # noqa: E402


def make_history(closes, start="2024-01-01"):
    dates = pd.date_range(start=start, periods=len(closes), freq="B")
    df = pd.DataFrame({
        "Open": closes,
        "High": [c * 1.01 for c in closes],
        "Low": [c * 0.99 for c in closes],
        "Close": closes,
        "Volume": [1_000_000] * len(closes),
    }, index=dates)
    return df


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

def test_sma_basic():
    closes = [10, 20, 30, 40, 50]
    history = make_history(closes)
    sma3 = analytics.compute_sma(history, 3)
    assert sma3 == pytest.approx((30 + 40 + 50) / 3)


def test_sma_insufficient_data_returns_none():
    history = make_history([10, 20])
    assert analytics.compute_sma(history, 5) is None


def test_sma_empty_history_returns_none():
    empty = pd.DataFrame(columns=["Close"])
    assert analytics.compute_sma(empty, 5) is None


# ---------------------------------------------------------------------------
# Golden cross
# ---------------------------------------------------------------------------

def test_golden_cross_true_when_sma50_above_sma200():
    assert analytics.compute_golden_cross(105.0, 100.0) is True


def test_golden_cross_false_when_sma50_below_sma200():
    assert analytics.compute_golden_cross(95.0, 100.0) is False


def test_golden_cross_none_when_missing_input():
    assert analytics.compute_golden_cross(None, 100.0) is None
    assert analytics.compute_golden_cross(100.0, None) is None


# ---------------------------------------------------------------------------
# Max drawdown
# ---------------------------------------------------------------------------

def test_max_drawdown_hand_verified():
    # Prices: 100 -> 120 (peak) -> 60 (trough) -> 90
    closes = [100, 120, 60, 90]
    history = make_history(closes)
    dd = analytics.compute_max_drawdown(history)
    # trough 60 vs running max 120 -> 60/120 - 1 = -0.5
    assert dd == pytest.approx(-0.5)


def test_max_drawdown_monotonic_increase_is_zero():
    closes = [10, 20, 30, 40]
    history = make_history(closes)
    dd = analytics.compute_max_drawdown(history)
    assert dd == pytest.approx(0.0)


def test_max_drawdown_empty_returns_none():
    empty = pd.DataFrame(columns=["Close"])
    assert analytics.compute_max_drawdown(empty) is None


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

def test_returns_1m_hand_verified():
    # 22 trading days: base at index 0 = 100, last = 110 -> return = 10%
    closes = [100] + [100] * 20 + [110]  # length 22
    history = make_history(closes)
    result = analytics.compute_returns(history)
    assert result["return_1m"] == pytest.approx(0.10)


def test_returns_insufficient_data_is_none():
    closes = [100, 105]
    history = make_history(closes)
    result = analytics.compute_returns(history)
    assert result["return_1m"] is None
    assert result["return_6m"] is None
    assert result["return_1y"] is None


# ---------------------------------------------------------------------------
# RSI — hand-computed small example (simple rolling-average method)
# ---------------------------------------------------------------------------

def test_rsi_hand_computed_example():
    # Construct 15 closes: 14 diffs.
    # Use a simple alternating-but-net-up series so we can hand-verify.
    # Closes: 44,44.25,44.5,43.75,44.65,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28,46.00
    closes = [44, 44.25, 44.5, 43.75, 44.65, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
    history = make_history(closes)
    rsi = analytics.compute_rsi(history, period=14)

    # Hand-compute using the SAME simple rolling average method.
    delta = np.diff(closes)
    gains = np.clip(delta, 0, None)
    losses = -np.clip(delta, None, 0)
    avg_gain = gains.mean()  # 14 deltas total -> simple average over all 14
    avg_loss = losses.mean()
    expected_rs = avg_gain / avg_loss
    expected_rsi = 100 - (100 / (1 + expected_rs))

    assert rsi == pytest.approx(expected_rsi, rel=1e-6)


def test_rsi_all_gains_is_100():
    closes = [10 + i for i in range(20)]  # strictly increasing
    history = make_history(closes)
    rsi = analytics.compute_rsi(history, period=14)
    assert rsi == pytest.approx(100.0)


def test_rsi_insufficient_data_returns_none():
    history = make_history([10, 11, 12])
    assert analytics.compute_rsi(history, period=14) is None


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------

def test_volatility_zero_for_constant_prices():
    closes = [100] * 30
    history = make_history(closes)
    vol = analytics.compute_volatility(history)
    assert vol == pytest.approx(0.0)


def test_volatility_none_for_insufficient_data():
    history = make_history([100])
    assert analytics.compute_volatility(history) is None


# ---------------------------------------------------------------------------
# Health score — boundary / clamping behavior
# ---------------------------------------------------------------------------

def test_health_score_clamped_between_0_and_100():
    result = analytics.compute_health_score(
        target_pe=5.0,
        peer_pes=[100.0, 100.0],  # target much cheaper -> high valuation score
        last_close=150.0,
        sma_50=100.0,
        sma_200=90.0,  # bullish trend -> momentum high
        rsi_14=50.0,   # neutral-good RSI band
        profit_margin=0.5,  # very high margin
        roe=0.5,  # very high ROE
    )
    assert 0.0 <= result["final_score"] <= 100.0
    assert result["final_score"] > 80  # should score very well


def test_health_score_worst_case_clamped_at_or_above_0():
    result = analytics.compute_health_score(
        target_pe=1000.0,
        peer_pes=[10.0, 10.0],  # wildly expensive vs peers
        last_close=50.0,
        sma_50=100.0,
        sma_200=110.0,  # bearish trend
        rsi_14=90.0,   # overbought
        profit_margin=-0.5,  # losses
        roe=-0.5,
    )
    assert 0.0 <= result["final_score"] <= 100.0
    assert result["final_score"] < 30  # should score poorly


def test_health_score_missing_pe_is_neutral():
    valuation = analytics.score_valuation(None, [10.0, 20.0])
    assert valuation["score"] == 50.0


def test_health_score_weights_sum_to_one():
    assert analytics.VALUATION_WEIGHT + analytics.MOMENTUM_WEIGHT + analytics.PROFITABILITY_WEIGHT == pytest.approx(1.0)
