"""Data orchestration service."""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from app.config import get_settings
from app.data.storage import (
    save_ohlcv, load_ohlcv, list_available_timeframes,
    get_bar_count, get_file_hash, delete_ohlcv
)
from app.data.validator import validate_ohlcv_dataframe, parse_csv_to_ohlcv, ValidationResult
from app.models.schemas import DataAvailabilityItem, DataQualityReport, DataImportResponse


class DataService:
    def __init__(self):
        self.settings = get_settings()

    def import_csv_file(
        self,
        filepath_or_content: Any,
        symbol: str,
        timeframe: str
    ) -> DataImportResponse:
        try:
            df = parse_csv_to_ohlcv(filepath_or_content, symbol)
            val_res = validate_ohlcv_dataframe(df, symbol, timeframe, is_24_7=(symbol not in ("XAUUSD", "XAGUSD")))

            if not val_res.is_valid and val_res.errors:
                return DataImportResponse(
                    success=False,
                    symbol=symbol,
                    timeframe=timeframe,
                    bars_imported=0,
                    quality_score=val_res.quality_score,
                    warnings=val_res.warnings,
                    errors=val_res.errors
                )

            saved_path = save_ohlcv(self.settings.PARQUET_DATA_DIR, symbol, timeframe, df)
            return DataImportResponse(
                success=True,
                symbol=symbol,
                timeframe=timeframe,
                bars_imported=len(df),
                quality_score=val_res.quality_score,
                warnings=val_res.warnings,
                errors=val_res.errors,
                file_path=saved_path
            )
        except Exception as e:
            return DataImportResponse(
                success=False,
                symbol=symbol,
                timeframe=timeframe,
                bars_imported=0,
                quality_score=0.0,
                errors=[str(e)]
            )

    def get_data_availability(self) -> List[DataAvailabilityItem]:
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "XAGUSD"]
        timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        items = []

        for s in symbols:
            avail = list_available_timeframes(self.settings.PARQUET_DATA_DIR, s)
            for tf in timeframes:
                if tf in avail:
                    cnt = get_bar_count(self.settings.PARQUET_DATA_DIR, s, tf)
                    h = get_file_hash(self.settings.PARQUET_DATA_DIR, s, tf)
                    items.append(DataAvailabilityItem(
                        symbol=s,
                        timeframe=tf,
                        bar_count=cnt,
                        file_hash=h
                    ))
                else:
                    items.append(DataAvailabilityItem(
                        symbol=s,
                        timeframe=tf,
                        bar_count=0
                    ))
        return items

    def get_quality_report(self, symbol: str, timeframe: str) -> DataQualityReport:
        df = load_ohlcv(self.settings.PARQUET_DATA_DIR, symbol, timeframe)
        if df.empty:
            return DataQualityReport(
                symbol=symbol, timeframe=timeframe, total_bars=0,
                missing_bars=0, duplicate_bars=0, gap_count=0,
                quality_score=0.0, has_volume=False, has_bid_ask=False,
                errors=["No historical data found"]
            )

        res = validate_ohlcv_dataframe(df, symbol, timeframe, is_24_7=(symbol not in ("XAUUSD", "XAGUSD")))
        return DataQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            total_bars=res.total_bars,
            missing_bars=res.missing_bars,
            duplicate_bars=res.duplicate_bars,
            gap_count=res.gap_count,
            quality_score=res.quality_score,
            has_volume=res.has_volume,
            has_bid_ask=res.has_bid_ask,
            min_price=res.min_price,
            max_price=res.max_price,
            warnings=res.warnings,
            errors=res.errors,
            gaps_detail=res.gaps_detail
        )

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> List[Dict[str, Any]]:
        df = load_ohlcv(self.settings.PARQUET_DATA_DIR, symbol, timeframe)
        if df.empty:
            return []
        if limit and len(df) > limit:
            df = df.tail(limit)
        bars = []
        for _, row in df.iterrows():
            ts_val = row["timestamp"]
            ts = int(ts_val.timestamp()) if hasattr(ts_val, "timestamp") else int(pd.to_datetime(ts_val).timestamp())
            bars.append({
                "time": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
        return bars


data_service = DataService()
