"""Trend and moving average indicators for QUANT-X."""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=1).mean()


def vwap(df: pd.DataFrame, session_reset: bool = True) -> pd.Series:
    """
    Volume Weighted Average Price.
    If session_reset is True and intraday, resets at 00:00 UTC each day.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"].replace(0, 1e-6)

    if session_reset and "timestamp" in df.columns:
        dates = pd.to_datetime(df["timestamp"]).dt.date
        cum_vol = vol.groupby(dates).cumsum()
        cum_tp_vol = (typical_price * vol).groupby(dates).cumsum()
        return cum_tp_vol / cum_vol
    else:
        cum_vol = vol.cumsum()
        cum_tp_vol = (typical_price * vol).cumsum()
        return cum_tp_vol / cum_vol


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range with Wilder's smoothing."""
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1).fillna(df["open"])

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def ema_alignment(
    df: pd.DataFrame,
    fast: int = 20,
    mid: int = 50,
    slow: int = 200
) -> pd.Series:
    """
    Returns:
       1 if Close > EMA(slow) and EMA(fast) > EMA(mid) (Bullish)
      -1 if Close < EMA(slow) and EMA(fast) < EMA(mid) (Bearish)
       0 otherwise
    """
    e_fast = ema(df["close"], fast)
    e_mid = ema(df["close"], mid)
    e_slow = ema(df["close"], slow)

    bull = (df["close"] > e_slow) & (e_fast > e_mid)
    bear = (df["close"] < e_slow) & (e_fast < e_mid)

    res = pd.Series(0, index=df.index, dtype=int)
    res[bull] = 1
    res[bear] = -1
    return res
