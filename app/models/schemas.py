"""Pydantic v2 schemas for QUANT-X API."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


class InstrumentResponse(BaseModel):
    symbol: str
    display_name: str
    market_type: str
    base_currency: str
    quote_currency: str
    contract_size: float
    tick_size: float
    tick_value: float
    min_lot: float
    max_lot: float
    lot_step: float
    is_24_7: bool
    data_available: bool = False
    bar_count: int = 0
    trading_sessions: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class TimeframeResponse(BaseModel):
    code: str
    display_name: str
    seconds: int
    sort_order: int


class DataImportResponse(BaseModel):
    success: bool
    symbol: str
    timeframe: str
    bars_imported: int
    quality_score: float
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    file_path: Optional[str] = None


class DataQualityReport(BaseModel):
    symbol: str
    timeframe: str
    total_bars: int
    missing_bars: int
    duplicate_bars: int
    gap_count: int
    quality_score: float
    has_volume: bool
    has_bid_ask: bool
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    gaps_detail: List[Dict[str, Any]] = Field(default_factory=list)


class DataAvailabilityItem(BaseModel):
    symbol: str
    timeframe: str
    bar_count: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    quality_score: Optional[float] = None
    file_hash: Optional[str] = None


class StrategyInfo(BaseModel):
    code: str
    name: str
    description: str
    version: str = "1.0.0"
    primary_assets: List[str]
    supported_timeframes: List[str]
    default_params: Dict[str, Any]


class StrategyConfigRequest(BaseModel):
    parameters: Dict[str, Any]
    risk_config: Dict[str, Any]


class StrategyConfigResponse(BaseModel):
    code: str
    symbol: str
    parameters: Dict[str, Any]
    risk_config: Dict[str, Any]
    is_default: bool = False


class RiskConfigSchema(BaseModel):
    risk_per_trade_pct: float = Field(default=0.5, ge=0.01, le=10.0)
    min_risk_reward: float = Field(default=2.0, ge=0.5)
    max_daily_loss_pct: float = Field(default=1.5, ge=0.1, le=50.0)
    max_simultaneous_trades: int = Field(default=3, ge=1, le=50)
    max_portfolio_exposure_pct: float = Field(default=10.0, ge=1.0)
    max_consecutive_losses: int = Field(default=5, ge=1)
    use_atr_stop: bool = True
    atr_stop_multiplier: float = 2.0
    use_trailing_stop: bool = False
    trailing_stop_atr_mult: float = 1.5
    break_even_at_rr: Optional[float] = 1.0


class ExecutionConfigSchema(BaseModel):
    spread_pct: float = 0.0002
    commission_per_lot: float = 0.0
    slippage_pips: float = 0.5
    use_tick_data: bool = False
    fill_at_open: bool = True


class BacktestRunRequest(BaseModel):
    symbol: str
    strategy_code: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000.0, gt=0)
    direction: Literal["LONG", "SHORT", "BOTH"] = "BOTH"
    risk_pct: float = Field(default=0.5, ge=0.01, le=10.0)
    strategy_params: Dict[str, Any] = Field(default_factory=dict)
    risk_config: Optional[RiskConfigSchema] = None
    execution_config: Optional[ExecutionConfigSchema] = None
    higher_tf: Optional[str] = None
    entry_tf: Optional[str] = None
    name: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str):
        allowed = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "XAGUSD"]
        if v.upper() not in allowed:
            raise ValueError(f"Symbol must be one of {allowed}")
        return v.upper()

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: datetime, info):
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be strictly after start_date")
        return v


class BacktestJobResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TradeRecord(BaseModel):
    trade_number: int
    asset: str
    strategy_code: str
    direction: str
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
    exit_reason: Optional[str] = None
    signal_details: Optional[Dict[str, Any]] = None


class TradeListResponse(BaseModel):
    trades: List[TradeRecord]
    total: int
    page: int = 1
    page_size: int = 100


class PerformanceMetricsResponse(BaseModel):
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


class BacktestResultsResponse(BaseModel):
    job_id: str
    status: str
    metrics: PerformanceMetricsResponse
    equity_curve: List[Dict[str, Any]]
    drawdown_curve: List[Dict[str, Any]]
    monthly_returns: List[Dict[str, Any]]
    r_distribution: List[Dict[str, Any]] = Field(default_factory=list)


class StrategyComparisonRow(BaseModel):
    strategy_code: str
    strategy_name: str
    symbol: str
    total_trades: int
    win_rate: float
    profit_factor: float
    net_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_r: float


class PositionSizeRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    account_balance: float
    risk_pct: float = 0.5


class PositionSizeResponse(BaseModel):
    position_size: float
    lot_size: float
    risk_amount: float
    stop_distance: float
    r_value: float


class OptimizationRunRequest(BaseModel):
    strategy_code: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    optimization_type: Literal["GRID", "RANDOM", "WALK_FORWARD"] = "GRID"
    param_space: Dict[str, Any]
    objective_metric: str = "profit_factor"
    max_trials: int = 50
    initial_capital: float = 10000.0


class OptimizationTrialResult(BaseModel):
    trial_number: int
    parameters: Dict[str, Any]
    metrics: PerformanceMetricsResponse
    score: float


class OptimizationResultsResponse(BaseModel):
    job_id: str
    status: str
    best_params: Dict[str, Any]
    best_score: float
    objective_metric: str
    trials: List[OptimizationTrialResult]


class HealthResponse(BaseModel):
    status: str
    version: str
    engine_uptime_seconds: float
    data_dir: str
    database_connected: bool = True
