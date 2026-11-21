"""Analytics and Strategy Comparison matrix API."""
from typing import List
from fastapi import APIRouter
from app.models.schemas import StrategyComparisonRow
from app.services.backtest_service import backtest_service

router = APIRouter(prefix="/analytics")


@router.get("/comparison", response_model=List[StrategyComparisonRow])
async def strategy_comparison_matrix():
    rows = []
    for job_id, res in backtest_service.results.items():
        job_info = backtest_service.jobs.get(job_id, {})
        req = job_info.get("request")
        if req and res and res.metrics:
            m = res.metrics
            rows.append(StrategyComparisonRow(
                strategy_code=req.strategy_code,
                strategy_name=job_info.get("name", req.strategy_code),
                symbol=req.symbol,
                total_trades=m.total_trades,
                win_rate=m.win_rate,
                profit_factor=m.profit_factor,
                net_return_pct=m.net_return_pct,
                max_drawdown_pct=m.max_drawdown_pct,
                sharpe_ratio=m.sharpe_ratio,
                avg_r=round(float(m.net_profit / max(m.gross_loss, 1.0)), 2)
            ))
    return rows
