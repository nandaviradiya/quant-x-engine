"""STRATEGY 3: Volatility Breakout + Retest (SOLUSD)."""
from typing import Dict, Any, Optional
import pandas as pd
from app.models.domain import Direction, Trade
from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.trend import ema, atr
from app.indicators.volatility import detect_consolidation
from app.indicators.volume import volume_sma, volume_confirms


class Strategy3VolatilityBreakout(BaseStrategy):
    CODE = "S3_VOL_BREAKOUT"
    NAME = "Volatility Breakout + Retest"
    VERSION = "1.0.0"
    PRIMARY_ASSETS = ["SOLUSD"]
    SUPPORTED_TIMEFRAMES = ["M15", "H1"]

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "consolidation_period": 20,
            "atr_period": 14,
            "volume_period": 20,
            "volume_threshold": 1.3,
            "rr_ratio": 2.0,
            "atr_sl_mult": 1.5,
            "ema_long": 200
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        if params.get("consolidation_period", 20) < 5:
            raise ValueError("consolidation_period must be >= 5")

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        d = df.copy()
        d["ema_long"] = ema(d["close"], p["ema_long"])
        d["atr"] = atr(d, p["atr_period"])
        in_cons, r_high, r_low = detect_consolidation(d, period=p["consolidation_period"])
        d["in_consolidation"] = in_cons
        d["range_high"] = r_high
        d["range_low"] = r_low
        d["vol_confirms"] = volume_confirms(d, p["volume_period"], p["volume_threshold"])
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

        c = float(bar["close"])
        e_long = float(bar["ema_long"])
        atr_val = float(bar["atr"])
        r_high = float(prev_bar["range_high"])
        r_low = float(prev_bar["range_low"])
        was_consolidating = bool(prev_bar["in_consolidation"])
        vol_ok = bool(bar["vol_confirms"])

        if was_consolidating and c > r_high and vol_ok and c > e_long:
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

        if was_consolidating and c < r_low and vol_ok and c < e_long:
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
