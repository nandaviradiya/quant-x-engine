"""Volume confirmation indicators."""
import pandas as pd


def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["volume"].rolling(window=period, min_periods=1).mean()


def volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Current bar volume divided by SMA volume. > 1.0 means above average."""
    sma_vol = volume_sma(df, period).replace(0, 1e-6)
    return df["volume"] / sma_vol


def volume_confirms(df: pd.DataFrame, period: int = 20, threshold: float = 1.2) -> pd.Series:
    return volume_ratio(df, period) >= threshold
