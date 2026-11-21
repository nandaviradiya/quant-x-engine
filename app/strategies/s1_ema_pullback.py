"""STRATEGY 1: EMA Trend Pullback + Breakout."""
from typing import Dict, Any, Optional
import pandas as pd
from app.models.domain import Direction, Trade
from app.strategies.base import BaseStrategy, SignalResult
from app.indicators.trend import ema, vwap, atr
from app.indicators.volume import volume_sma, volume_confirms


class Strategy1EmaPullback(BaseStrategy):
    CODE = "S1_EMA_PULLBACK"
    NAME = "EMA Trend Pullback + Breakout"
    VERSION = "1.0.0"
    PRIMARY_ASSETS = ["BTCUSD", "ETHUSD"]
    SUPPORTED_TIMEFRAMES = ["M15", "H1", "H4"]

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "ema_fast": 20,
            "ema_slow": 50,
            "ema_long": 200,
            "atr_period": 14,
            "volume_period": 20,
            "atr_sl_mult": 2.0,
            "rr_ratio": 2.0,
            "pullback_ema": "EMA20",
            "require_volume": True,
            "volume_threshold": 1.1,
            "min_body_ratio": 0.4
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        if params.get("ema_fast", 20) >= params.get("ema_slow", 50):
            raise ValueError("ema_fast must be less than ema_slow")
        if params.get("rr_ratio", 2.0) < 1.0:
            raise ValueError("rr_ratio must be at least 1.0")

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        d = df.copy()
        d["ema_fast"] = ema(d["close"], p["ema_fast"])
        d["ema_slow"] = ema(d["close"], p["ema_slow"])
        d["ema_long"] = ema(d["close"], p["ema_long"])
        d["vwap"] = vwap(d)
        d["atr"] = atr(d, p["atr_period"])
        d["vol_sma"] = volume_sma(d, p["volume_period"])
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
        o = float(bar["open"])
        h = float(bar["high"])
        l = float(bar["low"])
        e_fast = float(bar["ema_fast"])
        e_mid = float(bar["ema_slow"])
        e_long = float(bar["ema_long"])
        vwap_val = float(bar["vwap"])
        atr_val = float(bar["atr"])
        vol_ok = bool(bar["vol_confirms"]) if self.params["require_volume"] else True

        candle_range = max(h - l, 1e-8)
        body = abs(c - o)
        body_ratio = body / candle_range

        # 1. Bullish conditions
        if c > e_long and e_fast > e_mid and c > vwap_val:
            pulled_back = (l <= e_fast * 1.002 or prev_bar["low"] <= prev_bar["ema_fast"] * 1.002)
            is_bullish_candle = c > o and body_ratio >= self.params["min_body_ratio"]

            if pulled_back and is_bullish_candle and vol_ok:
                sl = min(l, float(prev_bar["low"])) - (self.params["atr_sl_mult"] * atr_val)
                risk = c - sl
                if risk > 0:
                    tp = c + (risk * self.params["rr_ratio"])
                    return SignalResult(
                        has_signal=True,
                        direction=Direction.LONG,
                        entry_price=c,
                        stop_loss=sl,
                        take_profit=tp,
                        details={
                            "strategy": self.CODE,
                            "ema_fast": e_fast,
                            "ema_slow": e_mid,
                            "ema_long": e_long,
                            "vwap": vwap_val,
                            "atr": atr_val
                        }
                    )

        # 2. Bearish conditions
        if c < e_long and e_fast < e_mid and c < vwap_val:
            pulled_back = (h >= e_fast * 0.998 or prev_bar["high"] >= prev_bar["ema_fast"] * 0.998)
            is_bearish_candle = c < o and body_ratio >= self.params["min_body_ratio"]

            if pulled_back and is_bearish_candle and vol_ok:
                sl = max(h, float(prev_bar["high"])) + (self.params["atr_sl_mult"] * atr_val)
                risk = sl - c
                if risk > 0:
                    tp = c - (risk * self.params["rr_ratio"])
                    return SignalResult(
                        has_signal=True,
                        direction=Direction.SHORT,
                        entry_price=c,
                        stop_loss=sl,
                        take_profit=tp,
                        details={
                            "strategy": self.CODE,
                            "ema_fast": e_fast,
                            "ema_slow": e_mid,
                            "ema_long": e_long,
                            "vwap": vwap_val,
                            "atr": atr_val
                        }
                    )

        return SignalResult(has_signal=False)
