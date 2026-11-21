"""STRATEGY 4: Gold EMA + VWAP Trend Pullback (XAUUSD)."""
from typing import Dict, Any, Optional
import pandas as pd
from app.models.domain import Direction, Trade
from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.trend import ema, vwap, atr


class Strategy4GoldEmaVwap(BaseStrategy):
    CODE = "S4_GOLD_EMA_VWAP"
    NAME = "Gold EMA + VWAP Trend Pullback"
    VERSION = "1.0.0"
    PRIMARY_ASSETS = ["XAUUSD"]
    SUPPORTED_TIMEFRAMES = ["M15", "H1"]

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "ema_slow": 50,
            "ema_long": 200,
            "atr_period": 14,
            "rr_ratio": 2.0,
            "atr_sl_mult": 1.8,
            "london_session": True,
            "ny_session": True,
            "london_start_utc": 8,
            "london_end_utc": 16,
            "ny_start_utc": 13,
            "ny_end_utc": 21
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        pass

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        d = df.copy()
        d["ema_slow"] = ema(d["close"], p["ema_slow"])
        d["ema_long"] = ema(d["close"], p["ema_long"])
        d["vwap"] = vwap(d)
        d["atr"] = atr(d, p["atr_period"])
        return d

    def _in_session(self, ts: pd.Timestamp) -> bool:
        p = self.params
        h = ts.hour
        london = p["london_session"] and (p["london_start_utc"] <= h <= p["london_end_utc"])
        ny = p["ny_session"] and (p["ny_start_utc"] <= h <= p["ny_end_utc"])
        return london or ny

    def check_signal(
        self,
        df: pd.DataFrame,
        bar_index: int,
        current_position: Optional[Trade] = None
    ) -> SignalResult:
        if current_position is not None or bar_index < 200:
            return SignalResult(has_signal=False)

        bar = df.iloc[bar_index]
        ts = pd.to_datetime(bar["timestamp"])
        if not self._in_session(ts):
            return SignalResult(has_signal=False, rejection_reason="Outside active trading session")

        c = float(bar["close"])
        o = float(bar["open"])
        l = float(bar["low"])
        h = float(bar["high"])
        e_slow = float(bar["ema_slow"])
        e_long = float(bar["ema_long"])
        vwap_val = float(bar["vwap"])
        atr_val = float(bar["atr"])

        if c > e_long and e_slow > e_long and c > vwap_val:
            touched_support = (l <= e_slow * 1.001 or l <= vwap_val * 1.001)
            bullish_candle = c > o
            if touched_support and bullish_candle:
                sl = l - (self.params["atr_sl_mult"] * atr_val)
                risk = c - sl
                if risk > 0:
                    tp = c + (risk * self.params["rr_ratio"])
                    return SignalResult(
                        has_signal=True,
                        direction=Direction.LONG,
                        entry_price=c,
                        stop_loss=sl,
                        take_profit=tp,
                        details={"strategy": self.CODE, "session_time": ts.isoformat(), "atr": atr_val}
                    )

        if c < e_long and e_slow < e_long and c < vwap_val:
            touched_res = (h >= e_slow * 0.999 or h >= vwap_val * 0.999)
            bearish_candle = c < o
            if touched_res and bearish_candle:
                sl = h + (self.params["atr_sl_mult"] * atr_val)
                risk = sl - c
                if risk > 0:
                    tp = c - (risk * self.params["rr_ratio"])
                    return SignalResult(
                        has_signal=True,
                        direction=Direction.SHORT,
                        entry_price=c,
                        stop_loss=sl,
                        take_profit=tp,
                        details={"strategy": self.CODE, "session_time": ts.isoformat(), "atr": atr_val}
                    )

        return SignalResult(has_signal=False)
