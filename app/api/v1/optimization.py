"""Optimization API router."""
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.models.schemas import OptimizationRunRequest, OptimizationResultsResponse
from app.models.domain import BacktestConfig, Direction, Timeframe, RiskConfig, ExecutionConfig
from app.data.storage import load_ohlcv
from app.config import get_settings
from app.optimization.grid_search import run_grid_search
from app.services.backtest_service import STRATEGY_MAP

router = APIRouter(prefix="/optimization")
opt_results: Dict[str, OptimizationResultsResponse] = {}


@router.post("/run", response_model=OptimizationResultsResponse)
async def run_optimization(req: OptimizationRunRequest):
    settings = get_settings()
    strat_cls = STRATEGY_MAP.get(req.strategy_code)
    if not strat_cls:
        raise HTTPException(status_code=400, detail=f"Unknown strategy code {req.strategy_code}")

    df = load_ohlcv(settings.PARQUET_DATA_DIR, req.symbol, req.timeframe, req.start_date, req.end_date)
    if df.empty:
        raise HTTPException(status_code=400, detail="No historical data found for optimization")

    base_cfg = BacktestConfig(
        strategy_code=req.strategy_code,
        symbol=req.symbol,
        timeframe=Timeframe[req.timeframe],
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        direction=Direction.BOTH,
        strategy_params={},
        risk_config=RiskConfig(),
        execution_config=ExecutionConfig()
    )

    trials = run_grid_search(
        base_cfg,
        df,
        strat_cls,
        req.param_space,
        objective_metric=req.objective_metric,
        max_trials=req.max_trials
    )

    best = trials[0] if trials else None
    job_id = str(uuid.uuid4())

    response = OptimizationResultsResponse(
        job_id=job_id,
        status="COMPLETED",
        best_params=best.parameters if best else {},
        best_score=best.score if best else 0.0,
        objective_metric=req.objective_metric,
        trials=trials
    )
    opt_results[job_id] = response
    return response


@router.get("/{job_id}/results", response_model=OptimizationResultsResponse)
async def get_optimization_results(job_id: str):
    res = opt_results.get(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="Optimization results not found")
    return res
