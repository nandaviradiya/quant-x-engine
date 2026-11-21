"""STRATEGY 5: Silver Range Breakout + Retest (XAGUSD)."""
from typing import Dict, Any, Optional
import pandas as pd
from app.models.domain import Direction, Trade
from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.trend import ema, atr
from app.indicators.volatility import detect_consolidation


class Strategy5SilverRange(BaseStrategy):
    CODE = "S5_SILVER_RANGE"
    NAME = "Silver Range Breakout + Retest"
    VERSION = "1.0.0"
    PRIMARY_ASSETS = ["XAGUSD"]
    SUPPORTED_TIMEFRAMES = ["M15", "H1"]

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "range_period": 20,
            "atr_period": 14,
            "ema_long": 200,
            "rr_ratio": 2.0,
            "atr_sl_mult": 1.5,
            "max_spread_pct": 0.003
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        pass

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        d = df.copy()
        d["ema_long"] = ema(d["close"], p["ema_long"])
        d["atr"] = atr(d, p["atr_period"])
        in_cons, r_high, r_low = detect_consolidation(d, period=p["range_period"])
        d["in_range"] = in_cons
        d["range_high"] = r_high
        d["range_low"] = r_low
        return d

    def check_signal(
        self,
        df: pd.DataFrame,
        bar_index: int,
        current_position: Optional[Trade] = None
    ) -> SignalResult:
        if current_position is not None or bar_index < 200:
            return SignalResult(has_signal=False)

        bar = df.iloc[bar_index]
        prev_bar = df.iloc[bar_index - 1]

        if "spread" in bar and pd.notna(bar["spread"]) and bar["spread"] > 0:
            spread_pct = float(bar["spread"]) / float(bar["close"])
            if spread_pct > self.params["max_spread_pct"]:
                return SignalResult(has_signal=False, rejection_reason="Spread too high")

        c = float(bar["close"])
        e_long = float(bar["ema_long"])
        atr_val = float(bar["atr"])
        r_high = float(prev_bar["range_high"])
        r_low = float(prev_bar["range_low"])
        was_in_range = bool(prev_bar["in_range"])

        if was_in_range and c > r_high and c > e_long:
            sl = r_high - (self.params["atr_sl_mult"] * atr_val)
            risk = c - sl
            if risk > 0:
                tp = c + (risk * self.params["rr_ratio"])
                return SignalResult(
                    has_signal=True,
                    direction=Direction.LONG,
                    entry_price=c,
                    stop_loss=sl,
                    take_profit=tp,
                    details={"strategy": self.CODE, "range_high": r_high, "atr": atr_val}
                )

        if was_in_range and c < r_low and c < e_long:
            sl = r_low + (self.params["atr_sl_mult"] * atr_val)
            risk = sl - c
            if risk > 0:
                tp = c - (risk * self.params["rr_ratio"])
                return SignalResult(
                    has_signal=True,
                    direction=Direction.SHORT,
                    entry_price=c,
                    stop_loss=sl,
                    take_profit=tp,
                    details={"strategy": self.CODE, "range_low": r_low, "atr": atr_val}
                )

        return SignalResult(has_signal=False)
