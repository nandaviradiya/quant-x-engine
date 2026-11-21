"""
Event-Driven Backtesting Engine for QUANT-X.
Accurately models:
- Zero look-ahead bias
- Forward chronological simulation
- Spread, commission, and slippage
- Conservative intrabar SL/TP evaluation
- Position sizing based on instrument contract & tick specifications
"""
import logging
from datetime import datetime
from typing import Optional, Callable, List
import pandas as pd
from app.models.domain import (
    Trade, BacktestConfig, PerformanceMetrics, Direction, ExitReason, Instrument, MarketType
)
from app.strategies.base import BaseStrategy, SignalResult
from app.risk.manager import RiskManager
from app.risk.sizing import calculate_position_size
from app.analytics.metrics import compute_performance_metrics
from app.analytics.charts import (
    generate_equity_curve, generate_drawdown_curve,
    generate_monthly_returns, generate_r_distribution
)

logger = logging.getLogger(__name__)

INSTRUMENTS_SPEC: dict[str, Instrument] = {
    "BTCUSD": Instrument("BTCUSD", "Bitcoin / USD", MarketType.CRYPTO, "BTC", "USD", 1.0, 0.01, 0.01, 0.001, 10.0, 0.001, True),
    "ETHUSD": Instrument("ETHUSD", "Ethereum / USD", MarketType.CRYPTO, "ETH", "USD", 1.0, 0.01, 0.01, 0.001, 100.0, 0.001, True),
    "SOLUSD": Instrument("SOLUSD", "Solana / USD", MarketType.CRYPTO, "SOL", "USD", 1.0, 0.001, 0.001, 0.01, 1000.0, 0.01, True),
    "XAUUSD": Instrument("XAUUSD", "Gold / USD", MarketType.METAL, "XAU", "USD", 100.0, 0.01, 1.0, 0.01, 50.0, 0.01, False),
    "XAGUSD": Instrument("XAGUSD", "Silver / USD", MarketType.METAL, "XAG", "USD", 5000.0, 0.001, 5.0, 0.01, 50.0, 0.01, False),
}


class BacktestExecutionResult:
    def __init__(self):
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []
        self.drawdown_curve: List[dict] = []
        self.monthly_returns: List[dict] = []
        self.r_distribution: List[dict] = []
        self.metrics: Optional[PerformanceMetrics] = None


class BacktestEngine:
    def __init__(
        self,
        config: BacktestConfig,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        progress_callback: Optional[Callable[[int, int, int], None]] = None
    ):
        self.config = config
        self.df = df.copy().reset_index(drop=True)
        self.strategy = strategy
        self.progress_callback = progress_callback
        self.capital = float(config.initial_capital)
        self.equity = float(config.initial_capital)
        self.risk_manager = RiskManager(config.risk_config, self.capital)
        self.instrument = INSTRUMENTS_SPEC.get(config.symbol.upper(), INSTRUMENTS_SPEC["BTCUSD"])

    def _apply_costs(self, trade: Trade, is_entry: bool) -> None:
        exec_cfg = self.config.execution_config
        # Spread cost
        if exec_cfg.spread_pct > 0:
            sp_cost = (trade.entry_price * exec_cfg.spread_pct / 2.0) * trade.position_size
            trade.spread_cost += sp_cost

        # Commission
        if exec_cfg.commission_per_lot > 0:
            lots = trade.position_size / self.instrument.contract_size
            trade.commission += (exec_cfg.commission_per_lot / 2.0) * lots

        # Slippage
        if exec_cfg.slippage_pips > 0:
            lots = trade.position_size / self.instrument.contract_size
            slip = (exec_cfg.slippage_pips * self.instrument.tick_value / 2.0) * lots
            trade.slippage += slip

    def _check_exit(self, trade: Trade, bar: pd.Series) -> Optional[ExitReason]:
        h, l = float(bar["high"]), float(bar["low"])

        if trade.direction == Direction.LONG:
            sl_hit = l <= trade.stop_loss
            tp_hit = h >= trade.take_profit
            # Conservative rule: if both hit in the same bar, assume Stop Loss hit first
            if sl_hit and tp_hit:
                return ExitReason.STOP_LOSS
            if sl_hit:
                return ExitReason.STOP_LOSS
            if tp_hit:
                return ExitReason.TAKE_PROFIT
        else:
            sl_hit = h >= trade.stop_loss
            tp_hit = l <= trade.take_profit
            if sl_hit and tp_hit:
                return ExitReason.STOP_LOSS
            if sl_hit:
                return ExitReason.STOP_LOSS
            if tp_hit:
                return ExitReason.TAKE_PROFIT

        return None

    def _close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, reason: ExitReason) -> None:
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = reason
        trade.is_open = False

        self._apply_costs(trade, is_entry=False)

        if trade.direction == Direction.LONG:
            trade.gross_pnl = (exit_price - trade.entry_price) * trade.position_size
        else:
            trade.gross_pnl = (trade.entry_price - exit_price) * trade.position_size

        total_costs = trade.commission + trade.slippage + trade.spread_cost
        trade.net_pnl = round(trade.gross_pnl - total_costs, 2)

        risk_val = abs(trade.entry_price - trade.stop_loss) * trade.position_size
        if risk_val > 1e-6:
            trade.r_multiple = round(trade.net_pnl / risk_val, 2)
        else:
            trade.r_multiple = 0.0

        self.equity += trade.net_pnl
        self.risk_manager.update_peak_equity(self.equity)
        self.risk_manager.register_trade_close(trade, exit_time)

    def run(self) -> BacktestExecutionResult:
        res = BacktestExecutionResult()

        # Pre-compute indicators
        self.df = self.strategy.compute_indicators(self.df)

        # Date filtering
        if "timestamp" in self.df.columns:
            start_ts = pd.to_datetime(self.config.start_date, utc=True)
            end_ts = pd.to_datetime(self.config.end_date, utc=True)
            self.df = self.df[(self.df["timestamp"] >= start_ts) & (self.df["timestamp"] <= end_ts)].reset_index(drop=True)

        n = len(self.df)
        if n < 50:
            logger.warning("Insufficient data bars for backtest")
            res.metrics = PerformanceMetrics()
            return res

        open_trades: List[Trade] = []
        closed_trades: List[Trade] = []
        trade_id = 1
        equity_values = [self.equity]

        # Chronological forward loop
        for i in range(n):
            bar = self.df.iloc[i]
            bar_time = pd.to_datetime(bar["timestamp"])

            # 1. Evaluate open trades for exit on this bar
            to_close = []
            for t in open_trades:
                exit_r = self._check_exit(t, bar)
                if exit_r:
                    px = t.stop_loss if exit_r == ExitReason.STOP_LOSS else (t.take_profit if exit_r == ExitReason.TAKE_PROFIT else float(bar["close"]))
                    self._close_trade(t, px, bar_time, exit_r)
                    to_close.append(t)
                    closed_trades.append(t)
                    equity_values.append(self.equity)

            for t in to_close:
                open_trades.remove(t)

            # 2. Check for entry signal on closed bar i
            # Fill executed at close of bar i (or next bar open)
            if len(open_trades) < self.config.risk_config.max_simultaneous_trades:
                risk_chk = self.risk_manager.can_open_trade(self.equity, bar_time, self.config.symbol)
                if risk_chk.allowed:
                    sig = self.strategy.check_signal(self.df, i, open_trades[0] if open_trades else None)
                    if sig.has_signal and sig.direction is not None:
                        # Direction filter
                        dir_allowed = (self.config.direction == Direction.BOTH) or (self.config.direction == sig.direction)
                        if dir_allowed:
                            try:
                                size_res = calculate_position_size(
                                    account_balance=self.equity,
                                    risk_pct=self.config.risk_config.risk_per_trade_pct,
                                    entry_price=sig.entry_price,
                                    stop_loss=sig.stop_loss,
                                    instrument=self.instrument
                                )

                                new_trade = Trade(
                                    trade_number=trade_id,
                                    asset=self.config.symbol,
                                    strategy_code=self.config.strategy_code,
                                    direction=sig.direction,
                                    entry_time=bar_time,
                                    entry_price=sig.entry_price,
                                    stop_loss=sig.stop_loss,
                                    take_profit=sig.take_profit,
                                    position_size=size_res.position_size,
                                    signal_details=sig.details
                                )
                                self._apply_costs(new_trade, is_entry=True)
                                open_trades.append(new_trade)
                                self.risk_manager.register_trade_open(new_trade)
                                trade_id += 1
                            except Exception as e:
                                logger.debug(f"Position sizing error: {e}")

            if self.progress_callback and (i % 50 == 0 or i == n - 1):
                self.progress_callback(i, n, len(closed_trades))

        # Close remaining open trades at final bar
        last_bar = self.df.iloc[-1]
        last_time = pd.to_datetime(last_bar["timestamp"])
        for t in open_trades:
            self._close_trade(t, float(last_bar["close"]), last_time, ExitReason.END_OF_DATA)
            closed_trades.append(t)
            equity_values.append(self.equity)

        # Assemble results
        res.trades = closed_trades
        res.metrics = compute_performance_metrics(closed_trades, self.capital, equity_values)
        res.equity_curve = generate_equity_curve(closed_trades, self.capital)
        res.drawdown_curve = generate_drawdown_curve(res.equity_curve)
        res.monthly_returns = generate_monthly_returns(closed_trades, self.capital)
        res.r_distribution = generate_r_distribution(closed_trades)

        return res
