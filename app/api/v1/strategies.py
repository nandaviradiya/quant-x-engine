"""Strategy management API endpoints."""
import logging
from pathlib import Path
import json

from fastapi import APIRouter, HTTPException
from app.config import get_settings

router = APIRouter(prefix="/strategies")
logger = logging.getLogger(__name__)

STRATEGIES_META = [
    {
        "code": "S1_EMA_PULLBACK",
        "name": "EMA Trend Pullback + Breakout",
        "description": "Uses EMA 20/50/200 + VWAP for trend direction with pullback entries confirmed by volume. Enters after bullish/bearish confirmation candle on a retest of the EMA zone.",
        "version": "1.0.0",
        "primary_assets": ["BTCUSD", "ETHUSD"],
        "supported_timeframes": ["M15", "H1", "H4"],
        "default_params": {
            "ema_fast": 20, "ema_slow": 50, "ema_long": 200,
            "atr_period": 14, "volume_period": 20,
            "atr_sl_mult": 2.0, "rr_ratio": 2.0,
            "pullback_ema": "EMA20", "require_volume": True,
            "volume_threshold": 1.2, "min_body_ratio": 0.5
        }
    },
    {
        "code": "S2_MSS",
        "name": "Trend + Market Structure Shift",
        "description": "Identifies BOS and MSS patterns for high-probability trend continuation. Requires structural confirmation before entry.",
        "version": "1.0.0",
        "primary_assets": ["ETHUSD", "BTCUSD"],
        "supported_timeframes": ["M15", "H1"],
        "default_params": {
            "swing_lookback": 5, "confirm_bars": 3,
            "ema_long": 200, "atr_period": 14,
            "rr_ratio": 2.0, "require_bos_before_mss": True,
            "min_structure_quality": 0.6
        }
    },
    {
        "code": "S3_VOL_BREAKOUT",
        "name": "Volatility Breakout + Retest",
        "description": "Detects consolidation ranges and trades confirmed breakouts with volume expansion. Avoids false breakouts using ATR and volume filters.",
        "version": "1.0.0",
        "primary_assets": ["SOLUSD"],
        "supported_timeframes": ["M15", "H1"],
        "default_params": {
            "consolidation_period": 20, "breakout_atr_mult": 1.5,
            "volume_threshold": 1.5, "wait_for_retest": True,
            "retest_tolerance_pct": 0.5, "atr_period": 14, "rr_ratio": 2.0
        }
    },
    {
        "code": "S4_GOLD_EMA_VWAP",
        "name": "Gold EMA + VWAP Trend Pullback",
        "description": "Session-aware gold strategy using EMA 50/200 and VWAP for London/NY session entries. Includes broker-specific server time conversion.",
        "version": "1.0.0",
        "primary_assets": ["XAUUSD"],
        "supported_timeframes": ["M15", "H1"],
        "default_params": {
            "ema_slow": 50, "ema_long": 200,
            "atr_period": 14, "rr_ratio": 2.0,
            "london_session": True, "ny_session": True,
            "london_start_utc": 8, "london_end_utc": 16,
            "ny_start_utc": 13, "ny_end_utc": 22,
            "pullback_zone_pct": 0.3
        }
    },
    {
        "code": "S5_SILVER_RANGE",
        "name": "Silver Range Breakout + Retest",
        "description": "Range breakout strategy for silver with spread and volatility filters. Avoids entries when spread is excessively high.",
        "version": "1.0.0",
        "primary_assets": ["XAGUSD"],
        "supported_timeframes": ["M15", "H1"],
        "default_params": {
            "range_period": 20, "breakout_atr_mult": 1.0,
            "max_spread_pct": 0.3, "wait_for_retest": True,
            "atr_period": 14, "rr_ratio": 2.0
        }
    },
    {
        "code": "S6_LIQUIDITY_SWEEP",
        "name": "Universal Liquidity Sweep",
        "description": "Identifies swept liquidity levels across all instruments. Detects swing highs/lows, equal highs/lows, PDH/PDL with optional MSS/BOS confirmation. Works on all 5 instruments.",
        "version": "1.0.0",
        "primary_assets": ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "XAGUSD"],
        "supported_timeframes": ["M5", "M15", "H1"],
        "default_params": {
            "swing_lookback": 5, "confirm_bars": 3,
            "min_sweep_dist_atr": 0.5, "max_sweep_dist_atr": 3.0,
            "rejection_body_ratio": 0.3,
            "require_mss": False, "require_bos": False,
            "require_volume": False, "volume_threshold": 1.2,
            "use_trend_filter": True, "use_atr_filter": True,
            "min_atr_pct": 0.1, "use_session_filter": False,
            "sl_buffer_atr": 0.5, "rr_ratio": 2.0,
            "equal_level_tolerance_pct": 0.05
        }
    }
]

# In-memory config store (replace with DB persistence in future)
_saved_configs: dict = {}


@router.get("")
async def list_strategies():
    """List all available trading strategies."""
    return STRATEGIES_META


@router.get("/{code}")
async def get_strategy(code: str):
    """Get strategy details by code."""
    strategy = next((s for s in STRATEGIES_META if s["code"] == code), None)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy '{code}' not found")
    return strategy


@router.get("/{code}/config/{symbol}")
async def get_strategy_config(code: str, symbol: str):
    """Get saved strategy configuration for a specific instrument."""
    key = f"{code}:{symbol}"
    if key not in _saved_configs:
        # Return default params
        strategy = next((s for s in STRATEGIES_META if s["code"] == code), None)
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy '{code}' not found")
        return {
            "code": code,
            "symbol": symbol,
            "parameters": strategy["default_params"],
            "risk_config": {
                "risk_per_trade_pct": 0.5,
                "min_risk_reward": 2.0,
                "max_daily_loss_pct": 1.5,
                "max_simultaneous_trades": 3,
                "max_consecutive_losses": 5,
                "use_atr_stop": True,
                "atr_stop_multiplier": 2.0,
                "use_trailing_stop": False
            },
            "is_default": True
        }
    return _saved_configs[key]


@router.put("/{code}/config/{symbol}")
async def save_strategy_config(code: str, symbol: str, config: dict):
    """Save strategy configuration for a specific instrument."""
    key = f"{code}:{symbol}"
    _saved_configs[key] = {
        "code": code,
        "symbol": symbol,
        **config,
        "is_default": False
    }
    return {"success": True, "message": f"Config saved for {code} on {symbol}"}


@router.get("/{code}/params/default")
async def get_default_params(code: str):
    """Get default parameter schema for a strategy."""
    strategy = next((s for s in STRATEGIES_META if s["code"] == code), None)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy '{code}' not found")
    return strategy["default_params"]
