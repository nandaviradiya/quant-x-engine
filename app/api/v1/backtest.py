"""Backtest execution and results API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.backtest_service import backtest_service
from app.models.schemas import (
    BacktestRunRequest, BacktestJobResponse,
    BacktestResultsResponse, TradeListResponse, TradeRecord
)

router = APIRouter(prefix="/backtest")


@router.post("/run", response_model=BacktestJobResponse)
async def run_backtest(req: BacktestRunRequest):
    return backtest_service.submit_job(req)


@router.get("/{job_id}/status", response_model=BacktestJobResponse)
async def get_status(job_id: str):
    status = backtest_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Backtest job not found")
    return status


@router.get("/{job_id}/results", response_model=BacktestResultsResponse)
async def get_results(job_id: str):
    res = backtest_service.get_results(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="Results not found or backtest still running")
    return res


@router.get("/{job_id}/trades", response_model=TradeListResponse)
async def get_trades(
    job_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000)
):
    all_trades = backtest_service.get_trades(job_id)
    start = (page - 1) * page_size
    end = start + page_size
    return TradeListResponse(
        trades=all_trades[start:end],
        total=len(all_trades),
        page=page,
        page_size=page_size
    )


@router.get("/history", response_model=List[BacktestJobResponse])
async def get_history():
    jobs = []
    for j_id, j in backtest_service.jobs.items():
        jobs.append(BacktestJobResponse(
            job_id=j["job_id"],
            status=j["status"],
            progress=j["progress"],
            name=j["name"],
            started_at=j["started_at"],
            completed_at=j["completed_at"],
            error_message=j["error_message"]
        ))
    return jobs
