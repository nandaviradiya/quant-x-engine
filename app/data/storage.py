"""OHLCV Parquet storage engine for QUANT-X."""
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
OPTIONAL_COLUMNS = ["bid", "ask", "spread"]

MARKET_TYPE_MAP = {
    "BTCUSD": "crypto",
    "ETHUSD": "crypto",
    "SOLUSD": "crypto",
    "XAUUSD": "metals",
    "XAGUSD": "metals"
}


def get_market_type(symbol: str) -> str:
    return MARKET_TYPE_MAP.get(symbol.upper(), "misc")


def get_parquet_path(data_dir: str, symbol: str, timeframe: str) -> Path:
    market = get_market_type(symbol)
    base = Path(data_dir) / market / symbol.upper()
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{timeframe.upper()}.parquet"


def save_ohlcv(data_dir: str, symbol: str, timeframe: str, df: pd.DataFrame) -> str:
    """Validate, clean, normalize, and save OHLCV DataFrame as Parquet."""
    if df.empty:
        raise ValueError("Cannot save empty DataFrame")

    clean_df = df.copy()

    # Column name lowercasing
    clean_df.columns = [str(c).strip().lower() for c in clean_df.columns]

    for req in REQUIRED_COLUMNS:
        if req not in clean_df.columns:
            raise ValueError(f"Missing required column: '{req}'")

    # Timestamp conversion to UTC
    if not pd.api.types.is_datetime64_any_dtype(clean_df["timestamp"]):
        clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"], utc=True)
    elif clean_df["timestamp"].dt.tz is None:
        clean_df["timestamp"] = clean_df["timestamp"].dt.tz_localize("UTC")
    else:
        clean_df["timestamp"] = clean_df["timestamp"].dt.tz_convert("UTC")

    # Numeric conversion
    for col in ["open", "high", "low", "close", "volume"]:
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

    for opt in OPTIONAL_COLUMNS:
        if opt in clean_df.columns:
            clean_df[opt] = pd.to_numeric(clean_df[opt], errors="coerce")

    # Drop NaNs in OHLC
    clean_df = clean_df.dropna(subset=["timestamp", "open", "high", "low", "close"]).copy()

    # Drop duplicates by timestamp
    clean_df = clean_df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    target_path = get_parquet_path(data_dir, symbol, timeframe)
    try:
        clean_df.to_parquet(target_path, engine="pyarrow", compression="snappy", index=False)
        logger.info(f"Saved {len(clean_df)} bars to {target_path}")
    except Exception as e:
        logger.error(f"Failed to save parquet via pyarrow, attempting fallback: {e}")
        clean_df.to_parquet(target_path, index=False)

    return str(target_path)


def load_ohlcv(
    data_dir: str,
    symbol: str,
    timeframe: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> pd.DataFrame:
    """Load OHLCV DataFrame from Parquet with optional date filtering."""
    file_path = get_parquet_path(data_dir, symbol, timeframe)
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df = pd.read_parquet(file_path)
    if df.empty:
        return df

    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    elif df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    if start:
        start_ts = pd.to_datetime(start, utc=True)
        df = df[df["timestamp"] >= start_ts]

    if end:
        end_ts = pd.to_datetime(end, utc=True)
        df = df[df["timestamp"] <= end_ts]

    return df.sort_values("timestamp").reset_index(drop=True)


def list_available_timeframes(data_dir: str, symbol: str) -> List[str]:
    market = get_market_type(symbol)
    symbol_dir = Path(data_dir) / market / symbol.upper()
    if not symbol_dir.exists():
        return []
    return [p.stem for p in symbol_dir.glob("*.parquet")]


def get_file_hash(data_dir: str, symbol: str, timeframe: str) -> Optional[str]:
    file_path = get_parquet_path(data_dir, symbol, timeframe)
    if not file_path.exists():
        return None
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_bar_count(data_dir: str, symbol: str, timeframe: str) -> int:
    file_path = get_parquet_path(data_dir, symbol, timeframe)
    if not file_path.exists():
        return 0
    try:
        import pyarrow.parquet as pq
        return pq.read_metadata(file_path).num_rows
    except Exception:
        df = pd.read_parquet(file_path, columns=["timestamp"])
        return len(df)


def delete_ohlcv(data_dir: str, symbol: str, timeframe: str) -> bool:
    file_path = get_parquet_path(data_dir, symbol, timeframe)
    if file_path.exists():
        file_path.unlink()
        return True
    return False
