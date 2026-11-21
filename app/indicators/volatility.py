"""Volatility and consolidation indicators."""
import numpy as np
import pandas as pd
from app.indicators.trend import atr


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower)."""
    mid = series.rolling(window=period, min_periods=1).mean()
    std = series.rolling(window=period, min_periods=1).std().fillna(0)
    upper = mid + (std_dev * std)
    lower = mid - (std_dev * std)
    return upper, mid, lower


def volatility_expansion(
    df: pd.DataFrame,
    short_period: int = 5,
    long_period: int = 20
) -> pd.Series:
    """Ratio of short ATR to long ATR. Values > 1.2 indicate volatility expansion."""
    atr_s = atr(df, period=short_period)
    atr_l = atr(df, period=long_period).replace(0, 1e-6)
    return atr_s / atr_l


def detect_consolidation(
    df: pd.DataFrame,
    period: int = 20,
    atr_mult: float = 1.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Detects if price is in a consolidation range.
    Returns (in_consolidation, range_high, range_low).
    """
    rolling_high = df["high"].rolling(window=period, min_periods=period).max()
    rolling_low = df["low"].rolling(window=period, min_periods=period).min()
    current_atr = atr(df, period=period)

    range_size = rolling_high - rolling_low
    in_range = range_size <= (current_atr * atr_mult * np.sqrt(period))
    return in_range.fillna(False), rolling_high, rolling_low
