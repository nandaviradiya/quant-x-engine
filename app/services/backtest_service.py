"""Backtest job execution and management service."""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
from app.config import get_settings
from app.models.domain import BacktestConfig, Direction, Timeframe, RiskConfig, ExecutionConfig
from app.models.schemas import BacktestRunRequest, BacktestJobResponse, BacktestResultsResponse, TradeRecord
from app.data.storage import load_ohlcv
from app.backtesting.engine import BacktestEngine
from app.strategies.s1_ema_pullback import Strategy1EmaPullback
from app.strategies.s2_market_structure import Strategy2MarketStructure
from app.strategies.s3_volatility_breakout import Strategy3VolatilityBreakout
from app.strategies.s4_gold_ema_vwap import Strategy4GoldEmaVwap
from app.strategies.s5_silver_range import Strategy5SilverRange
from app.strategies.s6_liquidity_sweep import Strategy6LiquiditySweep

logger = logging.getLogger(__name__)

STRATEGY_MAP = {
    "S1_EMA_PULLBACK": Strategy1EmaPullback,
    "S2_MSS": Strategy2MarketStructure,
    "S3_VOL_BREAKOUT": Strategy3VolatilityBreakout,
    "S4_GOLD_EMA_VWAP": Strategy4GoldEmaVwap,
    "S5_SILVER_RANGE": Strategy5SilverRange,
    "S6_LIQUIDITY_SWEEP": Strategy6LiquiditySweep,
}


class BacktestService:
    def __init__(self):
        self.settings = get_settings()
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, Any] = {}

    def submit_job(self, req: BacktestRunRequest) -> BacktestJobResponse:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "RUNNING",
            "progress": 0,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "name": req.name or f"{req.strategy_code}_{req.symbol}",
            "request": req,
            "error_message": None
        }

        asyncio.create_task(self._execute_job(job_id, req))

        return BacktestJobResponse(
            job_id=job_id,
            status="RUNNING",
            progress=0,
            started_at=self.jobs[job_id]["started_at"],
            name=self.jobs[job_id]["name"]
        )

    async def _execute_job(self, job_id: str, req: BacktestRunRequest):
        try:
            strat_cls = STRATEGY_MAP.get(req.strategy_code)
            if not strat_cls:
                raise ValueError(f"Unknown strategy code '{req.strategy_code}'")

            df = load_ohlcv(
                self.settings.PARQUET_DATA_DIR,
                req.symbol,
                req.timeframe,
                req.start_date,
                req.end_date
            )
            if df.empty:
                raise ValueError(f"No historical data found for {req.symbol} {req.timeframe}. Please import data first.")

            cfg = BacktestConfig(
                strategy_code=req.strategy_code,
                symbol=req.symbol,
                timeframe=Timeframe[req.timeframe],
                start_date=req.start_date,
                end_date=req.end_date,
                initial_capital=req.initial_capital,
                direction=Direction[req.direction],
                strategy_params=req.strategy_params,
                risk_config=RiskConfig(risk_per_trade_pct=req.risk_pct),
                execution_config=ExecutionConfig()
            )

            strat_inst = strat_cls(req.strategy_params)

            def progress_cb(curr: int, tot: int, trades_n: int):
                pct = int((curr / max(tot, 1)) * 100)
                if job_id in self.jobs:
                    self.jobs[job_id]["progress"] = pct

            engine = BacktestEngine(cfg, df, strat_inst, progress_callback=progress_cb)
            res = await asyncio.to_thread(engine.run)

            self.results[job_id] = res
            self.jobs[job_id]["status"] = "COMPLETED"
            self.jobs[job_id]["progress"] = 100
            self.jobs[job_id]["completed_at"] = datetime.now(timezone.utc)

            report_file = Path(self.settings.REPORTS_DIR) / f"{job_id}.json"
            report_data = {
                "job_id": job_id,
                "strategy": req.strategy_code,
                "symbol": req.symbol,
                "net_profit": res.metrics.net_profit if res.metrics else 0.0,
                "win_rate": res.metrics.win_rate if res.metrics else 0.0,
                "trades_count": len(res.trades)
            }
            report_file.write_text(json.dumps(report_data))

        except Exception as e:
            logger.error(f"Backtest job {job_id} failed: {e}")
            self.jobs[job_id]["status"] = "FAILED"
            self.jobs[job_id]["error_message"] = str(e)
            self.jobs[job_id]["completed_at"] = datetime.now(timezone.utc)

    def get_job_status(self, job_id: str) -> Optional[BacktestJobResponse]:
        j = self.jobs.get(job_id)
        if not j:
            return None
        return BacktestJobResponse(
            job_id=j["job_id"],
            status=j["status"],
            progress=j["progress"],
            name=j["name"],
            started_at=j["started_at"],
            completed_at=j["completed_at"],
            error_message=j["error_message"]
        )

    def get_results(self, job_id: str) -> Optional[BacktestResultsResponse]:
        j = self.jobs.get(job_id)
        res = self.results.get(job_id)
        if not j or not res:
            return None

        from app.models.schemas import PerformanceMetricsResponse
        m = res.metrics
        metrics_resp = PerformanceMetricsResponse(
            total_trades=m.total_trades,
            winning_trades=m.winning_trades,
            losing_trades=m.losing_trades,
            break_even_trades=m.break_even_trades,
            win_rate=m.win_rate,
            net_profit=m.net_profit,
            net_return_pct=m.net_return_pct,
            gross_profit=m.gross_profit,
            gross_loss=m.gross_loss,
            profit_factor=m.profit_factor,
            expected_value=m.expected_value,
            avg_win=m.avg_win,
            avg_loss=m.avg_loss,
            max_drawdown=m.max_drawdown,
            max_drawdown_pct=m.max_drawdown_pct,
            sharpe_ratio=m.sharpe_ratio,
            sortino_ratio=m.sortino_ratio,
            recovery_factor=m.recovery_factor,
            max_consecutive_wins=m.max_consecutive_wins,
            max_consecutive_losses=m.max_consecutive_losses,
            total_commission=m.total_commission,
            total_slippage=m.total_slippage,
            total_spread_cost=m.total_spread_cost,
            long_trades=m.long_trades,
            short_trades=m.short_trades,
            long_win_rate=m.long_win_rate,
            short_win_rate=m.short_win_rate
        )

        return BacktestResultsResponse(
            job_id=job_id,
            status=j["status"],
            metrics=metrics_resp,
            equity_curve=res.equity_curve,
            drawdown_curve=res.drawdown_curve,
            monthly_returns=res.monthly_returns,
            r_distribution=res.r_distribution
        )

    def get_trades(self, job_id: str) -> List[TradeRecord]:
        res = self.results.get(job_id)
        if not res:
            return []
        trades = []
        for t in res.trades:
            trades.append(TradeRecord(
                trade_number=t.trade_number,
                asset=t.asset,
                strategy_code=t.strategy_code,
                direction=t.direction.value,
                entry_time=t.entry_time,
                entry_price=t.entry_price,
                position_size=t.position_size,
                stop_loss=t.stop_loss,
                take_profit=t.take_profit,
                exit_time=t.exit_time,
                exit_price=t.exit_price,
                gross_pnl=t.gross_pnl,
                commission=t.commission,
                slippage=t.slippage,
                spread_cost=t.spread_cost,
                net_pnl=t.net_pnl,
                r_multiple=t.r_multiple,
                exit_reason=t.exit_reason.value if t.exit_reason else None,
                signal_details=t.signal_details
            ))
        return trades


backtest_service = BacktestService()
