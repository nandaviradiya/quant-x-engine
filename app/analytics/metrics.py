"""Comprehensive performance metrics calculation."""
import numpy as np
from typing import List
from app.models.domain import Trade, PerformanceMetrics, Direction


def compute_performance_metrics(
    trades: List[Trade],
    initial_capital: float,
    equity_curve_values: List[float]
) -> PerformanceMetrics:
    if not trades:
        return PerformanceMetrics()

    m = PerformanceMetrics()
    m.total_trades = len(trades)

    pnls = [t.net_pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    breakevens = [p for p in pnls if p == 0]

    m.winning_trades = len(wins)
    m.losing_trades = len(losses)
    m.break_even_trades = len(breakevens)
    m.win_rate = round(len(wins) / len(trades), 4)

    m.gross_profit = round(float(sum(wins)), 2)
    m.gross_loss = round(float(abs(sum(losses))), 2)
    m.net_profit = round(float(sum(pnls)), 2)
    m.net_return_pct = round((m.net_profit / initial_capital) * 100.0, 4)

    m.profit_factor = round(m.gross_profit / max(m.gross_loss, 1e-6), 4)
    m.expected_value = round(float(np.mean(pnls)), 2)
    m.avg_win = round(float(np.mean(wins)), 2) if wins else 0.0
    m.avg_loss = round(float(abs(np.mean(losses))), 2) if losses else 0.0

    # Max Drawdown
    if equity_curve_values:
        arr = np.array(equity_curve_values)
        peak = np.maximum.accumulate(arr)
        dd = peak - arr
        dd_pct = (dd / np.maximum(peak, 1e-6)) * 100.0
        m.max_drawdown = round(float(np.max(dd)), 2)
        m.max_drawdown_pct = round(float(np.max(dd_pct)), 4)

    # Sharpe and Sortino (annualized based on trade returns)
    if len(pnls) >= 2:
        returns = np.array(pnls) / initial_capital
        mean_r = np.mean(returns)
        std_r = np.std(returns)
        if std_r > 1e-8:
            m.sharpe_ratio = round(float((mean_r / std_r) * np.sqrt(252)), 4)

        downside = returns[returns < 0]
        if len(downside) > 0:
            downside_std = np.std(downside)
            if downside_std > 1e-8:
                m.sortino_ratio = round(float((mean_r / downside_std) * np.sqrt(252)), 4)

    # Recovery Factor
    if m.max_drawdown > 0:
        m.recovery_factor = round(m.net_profit / m.max_drawdown, 4)

    # Consecutive Streaks
    max_w = 0
    max_l = 0
    cur_w = 0
    cur_l = 0
    for p in pnls:
        if p > 0:
            cur_w += 1
            cur_l = 0
            max_w = max(max_w, cur_w)
        elif p < 0:
            cur_l += 1
            cur_w = 0
            max_l = max(max_l, cur_l)
        else:
            cur_w = 0
            cur_l = 0
    m.max_consecutive_wins = max_w
    m.max_consecutive_losses = max_l

    # Long vs Short
    longs = [t for t in trades if t.direction == Direction.LONG]
    shorts = [t for t in trades if t.direction == Direction.SHORT]
    m.long_trades = len(longs)
    m.short_trades = len(shorts)
    m.long_win_rate = round(len([t for t in longs if t.net_pnl > 0]) / max(len(longs), 1), 4)
    m.short_win_rate = round(len([t for t in shorts if t.net_pnl > 0]) / max(len(shorts), 1), 4)

    # Costs
    m.total_commission = round(float(sum(t.commission for t in trades)), 2)
    m.total_slippage = round(float(sum(t.slippage for t in trades)), 2)
    m.total_spread_cost = round(float(sum(t.spread_cost for t in trades)), 2)

    return m
