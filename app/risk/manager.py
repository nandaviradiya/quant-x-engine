"""Centralized risk management rules engine."""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict
from app.models.domain import Trade, RiskConfig


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: Optional[str] = None


class RiskManager:
    def __init__(self, config: RiskConfig, initial_capital: float):
        self.config = config
        self.initial_capital = initial_capital
        self.peak_equity = initial_capital
        self.daily_pnl: Dict[date, float] = {}
        self.open_trades: List[Trade] = []
        self.consecutive_losses: int = 0
        self.consecutive_wins: int = 0

    def can_open_trade(
        self,
        current_equity: float,
        current_time: datetime,
        symbol: str
    ) -> RiskCheckResult:
        if len(self.open_trades) >= self.config.max_simultaneous_trades:
            return RiskCheckResult(False, f"Max simultaneous trades reached ({self.config.max_simultaneous_trades})")

        d = current_time.date()
        daily_loss = self.daily_pnl.get(d, 0.0)
        max_daily = self.initial_capital * (self.config.max_daily_loss_pct / 100.0)
        if daily_loss < -max_daily:
            return RiskCheckResult(False, f"Daily loss limit reached (-{abs(daily_loss):.2f})")

        if self.consecutive_losses >= self.config.max_consecutive_losses:
            return RiskCheckResult(False, f"Max consecutive losses ({self.consecutive_losses}) reached")

        crypto_set = {"BTCUSD", "ETHUSD", "SOLUSD"}
        if symbol in crypto_set:
            crypto_open = sum(1 for t in self.open_trades if t.asset in crypto_set)
            if crypto_open >= 2:
                return RiskCheckResult(False, "Max correlated crypto positions reached (2)")

        return RiskCheckResult(True)

    def register_trade_open(self, trade: Trade) -> None:
        self.open_trades.append(trade)

    def register_trade_close(self, trade: Trade, close_time: datetime) -> None:
        if trade in self.open_trades:
            self.open_trades.remove(trade)

        d = close_time.date()
        self.daily_pnl[d] = self.daily_pnl.get(d, 0.0) + trade.net_pnl

        if trade.net_pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        elif trade.net_pnl < 0:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

    def update_peak_equity(self, current_equity: float) -> None:
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
