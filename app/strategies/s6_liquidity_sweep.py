"""
STRATEGY 6: Universal Liquidity Sweep Strategy (Mandatory for ALL 5 Instruments).
Works independently and can act as a confirmation filter for all other strategies.
"""
from typing import Dict, Any, Optional, List
import pandas as pd
from app.models.domain import Direction, Trade
from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.trend import ema, atr
from app.indicators.liquidity import detect_liquidity_zones, check_sweep_at_bar, LiquidityZone


class Strategy6LiquiditySweep(BaseStrategy):
    CODE = "S6_LIQUIDITY_SWEEP"
    NAME = "Universal Liquidity Sweep"
    VERSION = "1.0.0"
    PRIMARY_ASSETS = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "XAGUSD"]
    SUPPORTED_TIMEFRAMES = ["M5", "M15", "H1"]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.zones: List[LiquidityZone] = []

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "swing_lookback": 5,
            "confirm_bars": 3,
            "min_sweep_dist_atr": 0.3,
            "max_sweep_dist_atr": 3.0,
            "rejection_ratio": 0.35,
            "use_trend_filter": True,
            "ema_long": 200,
            "atr_period": 14,
            "rr_ratio": 2.0,
            "sl_buffer_atr": 0.5,
            "eq_tolerance_pct": 0.05
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        pass

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        d = df.copy()
        d["ema_long"] = ema(d["close"], p["ema_long"])
        d["atr"] = atr(d, p["atr_period"])

        self.zones = detect_liquidity_zones(
            d,
            swing_lookback=p["swing_lookback"],
            confirm_bars=p["confirm_bars"],
            eq_tolerance_pct=p["eq_tolerance_pct"]
        )
        return d

    def check_signal(
        self,
        df: pd.DataFrame,
        bar_index: int,
        current_position: Optional[Trade] = None
    ) -> SignalResult:
        if current_position is not None or bar_index < 50:
            return SignalResult(has_signal=False)

        bar = df.iloc[bar_index]
        c = float(bar["close"])
        e_long = float(bar["ema_long"])
        atr_val = float(bar["atr"])
        p = self.params

        zone, sweep_dir = check_sweep_at_bar(
            bar,
            bar_index,
            self.zones,
            atr_val=atr_val,
            min_sweep_atr=p["min_sweep_dist_atr"],
            max_sweep_atr=p["max_sweep_dist_atr"],
            rejection_ratio=p["rejection_ratio"]
        )

        if not zone or not sweep_dir:
            return SignalResult(has_signal=False)

        if sweep_dir == "BULLISH":
            if p["use_trend_filter"] and c < e_long:
                return SignalResult(has_signal=False, rejection_reason="Trend filter blocked bullish sweep")

            sl = float(zone.sweep_candle_low) - (p["sl_buffer_atr"] * atr_val)
            risk = c - sl
            if risk > 0:
                tp = c + (risk * p["rr_ratio"])
                return SignalResult(
                    has_signal=True,
                    direction=Direction.LONG,
                    entry_price=c,
                    stop_loss=sl,
                    take_profit=tp,
                    details={
                        "strategy": self.CODE,
                        "swept_zone_type": zone.zone_type,
                        "swept_price": zone.price,
                        "sweep_candle_low": zone.sweep_candle_low,
                        "atr": atr_val
                    }
                )

        elif sweep_dir == "BEARISH":
            if p["use_trend_filter"] and c > e_long:
                return SignalResult(has_signal=False, rejection_reason="Trend filter blocked bearish sweep")

            sl = float(zone.sweep_candle_high) + (p["sl_buffer_atr"] * atr_val)
            risk = sl - c
            if risk > 0:
                tp = c - (risk * p["rr_ratio"])
                return SignalResult(
                    has_signal=True,
                    direction=Direction.SHORT,
                    entry_price=c,
                    stop_loss=sl,
                    take_profit=tp,
                    details={
                        "strategy": self.CODE,
                        "swept_zone_type": zone.zone_type,
                        "swept_price": zone.price,
                        "sweep_candle_high": zone.sweep_candle_high,
                        "atr": atr_val
                    }
                )

        return SignalResult(has_signal=False)
