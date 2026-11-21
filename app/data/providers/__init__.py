"""Market data provider adapters for QUANT-X."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import pandas as pd
from app.data.storage import load_ohlcv, list_available_timeframes


class BaseDataProvider(ABC):
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        pass

    @abstractmethod
    def get_supported_timeframes(self) -> List[str]:
        pass

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        pass


class ParquetStoreProvider(BaseDataProvider):
    """Primary local Parquet storage provider."""
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def get_name(self) -> str:
        return "Local Parquet Store"

    def get_supported_symbols(self) -> List[str]:
        return ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "XAGUSD"]

    def get_supported_timeframes(self) -> List[str]:
        return ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        return load_ohlcv(self.data_dir, symbol, timeframe, start, end)


class CSVImportProvider(BaseDataProvider):
    """Direct CSV importer adapter."""
    def __init__(self, filepath: str):
        self.filepath = filepath

    def get_name(self) -> str:
        return "CSV File Adapter"

    def get_supported_symbols(self) -> List[str]:
        return ["BTCUSD", "ETHUSD", "SOLUSD", "XAUUSD", "XAGUSD"]

    def get_supported_timeframes(self) -> List[str]:
        return ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        from app.data.validator import parse_csv_to_ohlcv
        df = parse_csv_to_ohlcv(self.filepath, symbol)
        if start:
            start_ts = pd.to_datetime(start, utc=True)
            df = df[df["timestamp"] >= start_ts]
        if end:
            end_ts = pd.to_datetime(end, utc=True)
            df = df[df["timestamp"] <= end_ts]
        return df.reset_index(drop=True)
