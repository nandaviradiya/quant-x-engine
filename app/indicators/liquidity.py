"""
Liquidity Level Detection & Sweep Identification for Strategy 6 and filters.
CRITICAL: All levels require lookback & confirmation bars before becoming eligible for sweep.
No future candles are ever used.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from app.indicators.structure import swing_highs, swing_lows


@dataclass
class LiquidityZone:
    id: int
    bar_index: int           # The bar where the swing occurred
    confirmed_at_bar: int    # The bar when this swing was confirmed
    price: float
    zone_type: str           # "SWING_HIGH", "SWING_LOW", "EQ_HIGH", "EQ_LOW", "PDH", "PDL"
    swept: bool = False
    swept_at_bar: Optional[int] = None
    sweep_candle_low: Optional[float] = None
    sweep_candle_high: Optional[float] = None


def detect_liquidity_zones(
    df: pd.DataFrame,
    swing_lookback: int = 5,
    confirm_bars: int = 3,
    eq_tolerance_pct: float = 0.05
) -> List[LiquidityZone]:
    """Detects confirmed swing highs/lows and equal highs/lows."""
    sh = swing_highs(df, lookback=swing_lookback, confirm_bars=confirm_bars)
    sl = swing_lows(df, lookback=swing_lookback, confirm_bars=confirm_bars)

    zones: List[LiquidityZone] = []
    zone_id = 0

    for i in range(len(df)):
        if sh.iloc[i]:
            zones.append(LiquidityZone(
                id=zone_id,
                bar_index=i,
                confirmed_at_bar=i + confirm_bars,
                price=float(df["high"].iloc[i]),
                zone_type="SWING_HIGH"
            ))
            zone_id += 1
        if sl.iloc[i]:
            zones.append(LiquidityZone(
                id=zone_id,
                bar_index=i,
                confirmed_at_bar=i + confirm_bars,
                price=float(df["low"].iloc[i]),
                zone_type="SWING_LOW"
            ))
            zone_id += 1

    # Check for equal highs / equal lows
    high_zones = [z for z in zones if z.zone_type == "SWING_HIGH"]
    for i in range(len(high_zones)):
        for j in range(i + 1, len(high_zones)):
            z1, z2 = high_zones[i], high_zones[j]
            diff_pct = abs(z1.price - z2.price) / z1.price * 100.0
            if diff_pct <= eq_tolerance_pct:
                z1.zone_type = "EQ_HIGH"
                z2.zone_type = "EQ_HIGH"

    low_zones = [z for z in zones if z.zone_type == "SWING_LOW"]
    for i in range(len(low_zones)):
        for j in range(i + 1, len(low_zones)):
            z1, z2 = low_zones[i], low_zones[j]
            diff_pct = abs(z1.price - z2.price) / z1.price * 100.0
            if diff_pct <= eq_tolerance_pct:
                z1.zone_type = "EQ_LOW"
                z2.zone_type = "EQ_LOW"

    return zones


def check_sweep_at_bar(
    bar: pd.Series,
    bar_index: int,
    active_zones: List[LiquidityZone],
    atr_val: float,
    min_sweep_atr: float = 0.5,
    max_sweep_atr: float = 3.0,
    rejection_ratio: float = 0.35
) -> Tuple[Optional[LiquidityZone], Optional[str]]:
    """
    Checks if current bar creates a valid liquidity sweep on any confirmed, unswept zone.
    Returns (swept_zone, "BULLISH" | "BEARISH") or (None, None).
    """
    o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
    candle_range = max(h - l, 1e-8)
    candle_body = abs(c - o)

    # 1. Bullish sweep: price dipped below a SWING_LOW / EQ_LOW but closed back above it
    for zone in active_zones:
        if zone.swept or zone.confirmed_at_bar >= bar_index:
            continue

        if zone.zone_type in ("SWING_LOW", "EQ_LOW", "PDL"):
            if l < zone.price and c > zone.price:
                sweep_dist = zone.price - l
                if min_sweep_atr * atr_val <= sweep_dist <= max_sweep_atr * atr_val:
                    # Rejection wick check: lower wick must be prominent
                    lower_wick = min(o, c) - l
                    if lower_wick / candle_range >= (1.0 - rejection_ratio):
                        zone.swept = True
                        zone.swept_at_bar = bar_index
                        zone.sweep_candle_low = l
                        return zone, "BULLISH"

        elif zone.zone_type in ("SWING_HIGH", "EQ_HIGH", "PDH"):
            if h > zone.price and c < zone.price:
                sweep_dist = h - zone.price
                if min_sweep_atr * atr_val <= sweep_dist <= max_sweep_atr * atr_val:
                    upper_wick = h - max(o, c)
                    if upper_wick / candle_range >= (1.0 - rejection_ratio):
                        zone.swept = True
                        zone.swept_at_bar = bar_index
                        zone.sweep_candle_high = h
                        return zone, "BEARISH"

    return None, None
