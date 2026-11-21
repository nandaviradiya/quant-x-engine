"""Historical data validation, cleaning, and quality scoring."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class ValidationResult:
    is_valid: bool
    total_bars: int
    missing_bars: int
    duplicate_bars: int
    anomalies: int
    gap_count: int
    quality_score: float
    has_volume: bool
    has_bid_ask: bool
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    gaps_detail: List[Dict[str, Any]] = field(default_factory=list)


TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400
}


def parse_csv_to_ohlcv(content_or_path: Any, symbol: str) -> pd.DataFrame:
    """Robust parser for various CSV formats including MT5, TradingView, Yahoo Finance."""
    if isinstance(content_or_path, (str, bytes, io.BytesIO, io.StringIO)):
        if isinstance(content_or_path, bytes):
            content_or_path = io.BytesIO(content_or_path)
        elif isinstance(content_or_path, str) and ("\n" in content_or_path or "\r" in content_or_path):
            content_or_path = io.StringIO(content_or_path)
    
    # Try reading first with flexible delimiter detection
    try:
        df = pd.read_csv(content_or_path, sep=None, engine="python")
    except Exception:
        if hasattr(content_or_path, "seek"):
            content_or_path.seek(0)
        df = pd.read_csv(content_or_path, sep=",")

    cols = {str(c).strip(): c for c in df.columns}
    normalized_cols = {str(c).strip().lower(): c for c in df.columns}

    # MT5 format detection (<DATE> and <TIME> or Date and Time as separate columns)
    date_col = None
    time_col = None
    for k, orig in normalized_cols.items():
        if k in ("<date>", "date"):
            date_col = orig
        elif k in ("<time>", "time"):
            time_col = orig

    if date_col and time_col:
        # Merge date and time
        df["timestamp"] = pd.to_datetime(
            df[date_col].astype(str) + " " + df[time_col].astype(str),
            errors="coerce"
        )
    elif date_col and not time_col:
        df["timestamp"] = pd.to_datetime(df[date_col], errors="coerce")
    else:
        # Check for timestamp or datetime column
        ts_candidates = ["timestamp", "datetime", "time", "date", "<date_time>", "gmt time"]
        found_ts = None
        for c in ts_candidates:
            if c in normalized_cols:
                found_ts = normalized_cols[c]
                break
        if found_ts:
            df["timestamp"] = pd.to_datetime(df[found_ts], errors="coerce")
        else:
            # Assume first column is timestamp
            df["timestamp"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # Map OHLCV
    ohlcv_map = {
        "open": ["open", "<open>", "o", "price_open"],
        "high": ["high", "<high>", "h", "price_high"],
        "low": ["low", "<low>", "l", "price_low"],
        "close": ["close", "<close>", "c", "price_close"],
        "volume": ["volume", "<vol>", "<tickvol>", "vol", "v", "tick_volume", "volume_usd"]
    }

    result = pd.DataFrame()
    result["timestamp"] = df["timestamp"]

    for target, candidates in ohlcv_map.items():
        matched = False
        for cand in candidates:
            if cand in normalized_cols:
                result[target] = pd.to_numeric(df[normalized_cols[cand]], errors="coerce")
                matched = True
                break
        if not matched:
            if target == "volume":
                result["volume"] = 1.0  # default for tick data without volume
            else:
                raise ValueError(f"Could not identify '{target}' price column in CSV. Found: {list(df.columns)}")

    # Check for optional bid/ask/spread
    if "bid" in normalized_cols:
        result["bid"] = pd.to_numeric(df[normalized_cols["bid"]], errors="coerce")
    if "ask" in normalized_cols:
        result["ask"] = pd.to_numeric(df[normalized_cols["ask"]], errors="coerce")
    if "spread" in normalized_cols:
        result["spread"] = pd.to_numeric(df[normalized_cols["spread"]], errors="coerce")
    elif "bid" in result.columns and "ask" in result.columns:
        result["spread"] = result["ask"] - result["bid"]

    # Normalize timezone to UTC
    if result["timestamp"].dt.tz is None:
        result["timestamp"] = result["timestamp"].dt.tz_localize("UTC")
    else:
        result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")

    return result.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp").reset_index(drop=True)


def validate_ohlcv_dataframe(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    is_24_7: bool = True
) -> ValidationResult:
    """Comprehensive validation of historical OHLCV data."""
    warnings: List[str] = []
    errors: List[str] = []

    if df.empty:
        return ValidationResult(
            is_valid=False, total_bars=0, missing_bars=0, duplicate_bars=0,
            anomalies=0, gap_count=0, quality_score=0.0, has_volume=False,
            has_bid_ask=False, errors=["Dataset is empty"]
        )

    total_bars = len(df)

    # 1. Check required columns
    for col in ["timestamp", "open", "high", "low", "close"]:
        if col not in df.columns:
            errors.append(f"Required column '{col}' is missing")

    if errors:
        return ValidationResult(
            is_valid=False, total_bars=total_bars, missing_bars=0, duplicate_bars=0,
            anomalies=0, gap_count=0, quality_score=0.0, has_volume=False,
            has_bid_ask=False, errors=errors
        )

    # 2. Check price sanity: high >= low, high >= open, high >= close, low <= open, low <= close
    invalid_high_low = (df["high"] < df["low"]).sum()
    invalid_high_open = (df["high"] < df["open"]).sum()
    invalid_high_close = (df["high"] < df["close"]).sum()
    invalid_low_open = (df["low"] > df["open"]).sum()
    invalid_low_close = (df["low"] > df["close"]).sum()

    anomalies = int(invalid_high_low + invalid_high_open + invalid_high_close + invalid_low_open + invalid_low_close)
    if anomalies > 0:
        warnings.append(f"Detected {anomalies} price consistency anomalies (e.g. High < Low)")

    # 3. Check for zero or negative prices
    zero_prices = ((df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0) | (df["close"] <= 0)).sum()
    if zero_prices > 0:
        errors.append(f"Found {zero_prices} zero or negative price candles")

    # 4. Check duplicates
    duplicate_bars = int(df["timestamp"].duplicated().sum())
    if duplicate_bars > 0:
        warnings.append(f"Found {duplicate_bars} duplicate timestamp candles")

    # 5. Check gaps
    tf_seconds = TIMEFRAME_SECONDS.get(timeframe.upper(), 3600)
    gaps, missing_bars = detect_gaps(df, tf_seconds, is_24_7)
    if missing_bars > 0:
        warnings.append(f"Detected {len(gaps)} data gaps with approx {missing_bars} missing bars")

    # 6. Check volume and bid/ask presence
    has_volume = "volume" in df.columns and (df["volume"] > 0).any()
    if not has_volume:
        warnings.append("Volume information is absent or all zeros")

    has_bid_ask = "bid" in df.columns and "ask" in df.columns

    # 7. Compute Quality Score (0 to 100)
    missing_pct = min(1.0, missing_bars / max(total_bars, 1))
    dup_pct = min(1.0, duplicate_bars / max(total_bars, 1))
    anomaly_pct = min(1.0, anomalies / max(total_bars, 1))

    deduction = (missing_pct * 40.0) + (dup_pct * 30.0) + (anomaly_pct * 30.0)
    quality_score = max(0.0, round(100.0 - deduction, 2))

    min_p = float(df["low"].min()) if not df.empty else None
    max_p = float(df["high"].max()) if not df.empty else None

    is_valid = len(errors) == 0 and quality_score >= 50.0

    return ValidationResult(
        is_valid=is_valid,
        total_bars=total_bars,
        missing_bars=missing_bars,
        duplicate_bars=duplicate_bars,
        anomalies=anomalies,
        gap_count=len(gaps),
        quality_score=quality_score,
        has_volume=has_volume,
        has_bid_ask=has_bid_ask,
        min_price=min_p,
        max_price=max_p,
        warnings=warnings,
        errors=errors,
        gaps_detail=gaps[:20]  # first 20 gaps
    )


def detect_gaps(df: pd.DataFrame, timeframe_seconds: int, is_24_7: bool) -> Tuple[List[Dict[str, Any]], int]:
    """Detect unexpected time gaps between consecutive candles."""
    if len(df) < 2:
        return [], 0

    diffs = df["timestamp"].diff().dt.total_seconds().dropna()
    expected_diff = float(timeframe_seconds)

    gap_threshold = expected_diff * 1.5
    gaps: List[Dict[str, Any]] = []
    total_missing = 0

    gap_indices = diffs[diffs > gap_threshold].index

    for idx in gap_indices:
        t_prev = df.loc[idx - 1, "timestamp"]
        t_curr = df.loc[idx, "timestamp"]
        gap_sec = (t_curr - t_prev).total_seconds()

        # For metals (non-24/7), weekend gaps (Friday close to Sunday open) are normal
        if not is_24_7:
            if t_prev.weekday() in (4, 5) and t_curr.weekday() in (6, 0):
                continue

        missing_estimate = int(max(0, round((gap_sec - expected_diff) / expected_diff)))
        if missing_estimate > 0:
            total_missing += missing_estimate
            gaps.append({
                "from": t_prev.isoformat(),
                "to": t_curr.isoformat(),
                "gap_hours": round(gap_sec / 3600.0, 2),
                "estimated_missing_bars": missing_estimate
            })

    return gaps, total_missing
