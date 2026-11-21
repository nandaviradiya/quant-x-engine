"""
Market structure indicators for QUANT-X.
CRITICAL: Designed with zero look-ahead bias.
A swing high/low is ONLY identified after 'confirm_bars' have closed below/above it.
"""
import numpy as np
import pandas as pd
from typing import Tuple


def swing_highs(
    df: pd.DataFrame,
    lookback: int = 5,
    confirm_bars: int = 3
) -> pd.Series:
    """
    Identify confirmed swing highs.
    Bar i is a confirmed swing high at bar (i + confirm_bars) if:
    high[i] is greater than all bars from (i - lookback) to (i - 1),
    AND high[i] is greater than all bars from (i + 1) to (i + confirm_bars).
    Returns boolean series aligned with df index (True at bar i when confirmed).
    """
    highs = df["high"].values
    n = len(df)
    is_sh = np.zeros(n, dtype=bool)

    for i in range(lookback, n - confirm_bars):
        cand = highs[i]
        # Left check
        left = highs[i - lookback:i]
        if np.all(cand > left):
            # Right check
            right = highs[i + 1:i + confirm_bars + 1]
            if np.all(cand > right):
                is_sh[i] = True

    return pd.Series(is_sh, index=df.index)


def swing_lows(
    df: pd.DataFrame,
    lookback: int = 5,
    confirm_bars: int = 3
) -> pd.Series:
    """
    Identify confirmed swing lows.
    Returns boolean series aligned with df index.
    """
    lows = df["low"].values
    n = len(df)
    is_sl = np.zeros(n, dtype=bool)

    for i in range(lookback, n - confirm_bars):
        cand = lows[i]
        left = lows[i - lookback:i]
        if np.all(cand < left):
            right = lows[i + 1:i + confirm_bars + 1]
            if np.all(cand < right):
                is_sl[i] = True

    return pd.Series(is_sl, index=df.index)


def market_structure_shifts(
    df: pd.DataFrame,
    sh_series: pd.Series,
    sl_series: pd.Series,
    confirm_bars: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Detect Market Structure Shifts (MSS) bar by bar with zero lookahead bias.
    Only confirmed swing levels known at bar k are considered.
    Returns (bullish_mss, bearish_mss) boolean Series.
    """
    n = len(df)
    bull_mss = np.zeros(n, dtype=bool)
    bear_mss = np.zeros(n, dtype=bool)

    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values

    last_active_sh = None
    last_active_sl = None

    for k in range(n):
        # Has a swing high just completed its confirmation at bar k?
        check_idx = k - confirm_bars
        if check_idx >= 0:
            if sh_series.iloc[check_idx]:
                last_active_sh = highs[check_idx]
            if sl_series.iloc[check_idx]:
                last_active_sl = lows[check_idx]

        # Check for MSS at bar k
        c = closes[k]
        if last_active_sh is not None and c > last_active_sh:
            bull_mss[k] = True
            last_active_sh = None  # Level consumed

        if last_active_sl is not None and c < last_active_sl:
            bear_mss[k] = True
            last_active_sl = None  # Level consumed

    return pd.Series(bull_mss, index=df.index), pd.Series(bear_mss, index=df.index)


def previous_day_high_low(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Returns (pdh, pdl) available at the start of each day with zero look-ahead."""
    dates = pd.to_datetime(df["timestamp"]).dt.date
    daily_h = df["high"].groupby(dates).transform("max")
    daily_l = df["low"].groupby(dates).transform("min")

    pdh = daily_h.groupby(dates).shift(1).ffill()
    pdl = daily_l.groupby(dates).shift(1).ffill()
    return pdh, pdl
