"""QUANT-X domain models - dataclasses and enums."""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


class MarketType(str, Enum):
    CRYPTO = "CRYPTO"
    METAL = "METAL"
    FOREX = "FOREX"
    EQUITY = "EQUITY"


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

    @property
    def seconds(self) -> int:
        mapping = {
            "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
            "H1": 3600, "H4": 14400, "D1": 86400,
        }
        return mapping[self.value]


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExitReason(str, Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP = "TRAILING_STOP"
    BREAK_EVEN = "BREAK_EVEN"
    SIGNAL_REVERSE = "SIGNAL_REVERSE"
    END_OF_DATA = "END_OF_DATA"
    MAX_BARS = "MAX_BARS"
    MANUAL = "MANUAL"


@dataclass
class Instrument:
    symbol: str
    display_name: str
    market_type: MarketType
    base_currency: str
    quote_currency: str
    contract_size: float
    tick_size: float
    tick_value: float
    min_lot: float
    max_lot: float
    lot_step: float
    is_24_7: bool
    trading_sessions: Optional[Dict] = None
    metadata: Optional[Dict] = None


@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 0.5
    min_risk_reward: float = 2.0
    max_daily_loss_pct: float = 1.5
    max_simultaneous_trades: int = 3
    max_portfolio_exposure_pct: float = 10.0
    max_consecutive_losses: int = 5
    use_atr_stop: bool = True
    atr_stop_multiplier: float = 2.0
    use_trailing_stop: bool = False
    trailing_stop_atr_mult: float = 1.5
    break_even_at_rr: Optional[float] = 1.0


@dataclass
class ExecutionConfig:
    spread_pct: float = 0.0
    commission_per_lot: float = 0.0
    slippage_pips: float = 0.0
    use_tick_data: bool = False
    fill_at_open: bool = False  # True = fill at next bar open; False = fill at candle close


@dataclass
class BacktestConfig:
    strategy_code: str
    symbol: str
    timeframe: Timeframe
    start_date: datetime
    end_date: datetime
    initial_capital: float
    direction: Direction
    strategy_params: Dict[str, Any]
    risk_config: RiskConfig
    execution_config: ExecutionConfig
    higher_tf: Optional[Timeframe] = None
    entry_tf: Optional[Timeframe] = None
    name: Optional[str] = None


@dataclass
class Trade:
    trade_number: int
    asset: str
    strategy_code: str
    direction: Direction
    entry_time: datetime
    entry_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    gross_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    spread_cost: float = 0.0
    net_pnl: float = 0.0
    r_multiple: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    signal_details: Optional[Dict] = None
    is_open: bool = True


@dataclass
class PerformanceMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    win_rate: float = 0.0
    net_profit: float = 0.0
    net_return_pct: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    expected_value: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    recovery_factor: float = 0.0
    avg_holding_bars: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    total_spread_cost: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
