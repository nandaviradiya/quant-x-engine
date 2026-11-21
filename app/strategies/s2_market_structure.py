"""STRATEGY 2: Trend + Market Structure Shift (MSS)."""
from typing import Dict, Any, Optional
import pandas as pd
from app.models.domain import Direction, Trade
from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.trend import ema, atr
from app.indicators.structure import swing_highs, swing_lows, market_structure_shifts


class Strategy2MarketStructure(BaseStrategy):
    CODE = "S2_MSS"
    NAME = "Trend + Market Structure Shift"
    VERSION = "1.0.0"
    PRIMARY_ASSETS = ["ETHUSD", "BTCUSD"]
    SUPPORTED_TIMEFRAMES = ["M15", "H1"]

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "swing_lookback": 5,
            "confirm_bars": 3,
            "ema_long": 200,
            "atr_period": 14,
            "rr_ratio": 2.0,
            "atr_sl_mult": 1.5
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        if params.get("swing_lookback", 5) < 2:
            raise ValueError("swing_lookback must be at least 2")

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        d = df.copy()
        d["ema_long"] = ema(d["close"], p["ema_long"])
        d["atr"] = atr(d, p["atr_period"])
        sh = swing_highs(d, lookback=p["swing_lookback"], confirm_bars=p["confirm_bars"])
        sl = swing_lows(d, lookback=p["swing_lookback"], confirm_bars=p["confirm_bars"])
        bull_mss, bear_mss = market_structure_shifts(d, sh, sl, confirm_bars=p["confirm_bars"])
        d["bull_mss"] = bull_mss
        d["bear_mss"] = bear_mss
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
        c = float(bar["close"])
        e_long = float(bar["ema_long"])
        atr_val = float(bar["atr"])

        if bool(bar["bull_mss"]) and c > e_long:
            sl = float(bar["low"]) - (self.params["atr_sl_mult"] * atr_val)
            risk = c - sl
            if risk > 0:
                tp = c + (risk * self.params["rr_ratio"])
                return SignalResult(
                    has_signal=True,
                    direction=Direction.LONG,
                    entry_price=c,
                    stop_loss=sl,
                    take_profit=tp,
                    details={"strategy": self.CODE, "type": "Bullish MSS", "atr": atr_val}
                )

        if bool(bar["bear_mss"]) and c < e_long:
            sl = float(bar["high"]) + (self.params["atr_sl_mult"] * atr_val)
            risk = sl - c
            if risk > 0:
                tp = c - (risk * self.params["rr_ratio"])
                return SignalResult(
                    has_signal=True,
                    direction=Direction.SHORT,
                    entry_price=c,
                    stop_loss=sl,
                    take_profit=tp,
                    details={"strategy": self.CODE, "type": "Bearish MSS", "atr": atr_val}
                )

        return SignalResult(has_signal=False)
