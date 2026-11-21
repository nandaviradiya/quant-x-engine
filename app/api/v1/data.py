"""Data management REST endpoints."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.services.data_service import data_service
from app.models.schemas import (
    InstrumentResponse, TimeframeResponse, DataImportResponse,
    DataQualityReport, DataAvailabilityItem
)

router = APIRouter(prefix="/data")

INSTRUMENTS_META = [
    {"symbol": "BTCUSD", "display_name": "Bitcoin / US Dollar", "market_type": "CRYPTO", "base_currency": "BTC", "quote_currency": "USD", "contract_size": 1.0, "tick_size": 0.01, "tick_value": 0.01, "min_lot": 0.001, "max_lot": 10.0, "lot_step": 0.001, "is_24_7": True},
    {"symbol": "ETHUSD", "display_name": "Ethereum / US Dollar", "market_type": "CRYPTO", "base_currency": "ETH", "quote_currency": "USD", "contract_size": 1.0, "tick_size": 0.01, "tick_value": 0.01, "min_lot": 0.001, "max_lot": 100.0, "lot_step": 0.001, "is_24_7": True},
    {"symbol": "SOLUSD", "display_name": "Solana / US Dollar", "market_type": "CRYPTO", "base_currency": "SOL", "quote_currency": "USD", "contract_size": 1.0, "tick_size": 0.001, "tick_value": 0.001, "min_lot": 0.01, "max_lot": 1000.0, "lot_step": 0.01, "is_24_7": True},
    {"symbol": "XAUUSD", "display_name": "Gold / US Dollar", "market_type": "METAL", "base_currency": "XAU", "quote_currency": "USD", "contract_size": 100.0, "tick_size": 0.01, "tick_value": 1.0, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "is_24_7": False},
    {"symbol": "XAGUSD", "display_name": "Silver / US Dollar", "market_type": "METAL", "base_currency": "XAG", "quote_currency": "USD", "contract_size": 5000.0, "tick_size": 0.001, "tick_value": 5.0, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "is_24_7": False},
]

TIMEFRAMES_META = [
    {"code": "M1", "display_name": "1 Minute", "seconds": 60, "sort_order": 1},
    {"code": "M5", "display_name": "5 Minutes", "seconds": 300, "sort_order": 2},
    {"code": "M15", "display_name": "15 Minutes", "seconds": 900, "sort_order": 3},
    {"code": "M30", "display_name": "30 Minutes", "seconds": 1800, "sort_order": 4},
    {"code": "H1", "display_name": "1 Hour", "seconds": 3600, "sort_order": 5},
    {"code": "H4", "display_name": "4 Hours", "seconds": 14400, "sort_order": 6},
    {"code": "D1", "display_name": "1 Day", "seconds": 86400, "sort_order": 7},
]


@router.get("/instruments", response_model=List[InstrumentResponse])
async def list_instruments():
    avail_map = {item.symbol: item.bar_count for item in data_service.get_data_availability() if item.bar_count > 0}
    res = []
    for ins in INSTRUMENTS_META:
        bars = avail_map.get(ins["symbol"], 0)
        res.append(InstrumentResponse(**ins, data_available=(bars > 0), bar_count=bars))
    return res


@router.get("/timeframes", response_model=List[TimeframeResponse])
async def list_timeframes():
    return [TimeframeResponse(**tf) for tf in TIMEFRAMES_META]


@router.post("/import", response_model=DataImportResponse)
async def import_data(
    file: UploadFile = File(...),
    symbol: str = Form(...),
    timeframe: str = Form(...)
):
    content = await file.read()
    result = data_service.import_csv_file(content, symbol.upper(), timeframe.upper())
    return result


@router.get("/availability", response_model=List[DataAvailabilityItem])
async def data_availability():
    return data_service.get_data_availability()


@router.get("/quality/{symbol}/{timeframe}", response_model=DataQualityReport)
async def quality_report(symbol: str, timeframe: str):
    return data_service.get_quality_report(symbol.upper(), timeframe.upper())
