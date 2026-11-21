"""Abstract base strategy and signal result definition."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd
from app.models.domain import Direction, Trade


@dataclass
class SignalResult:
    has_signal: bool
    direction: Optional[Direction] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_strength: float = 1.0
    details: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None


class BaseStrategy(ABC):
    CODE: str = ""
    NAME: str = ""
    VERSION: str = "1.0.0"
    PRIMARY_ASSETS: List[str] = []
    SUPPORTED_TIMEFRAMES: List[str] = []

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = self.get_default_params()
        if params:
            self.params.update(params)
        self.validate_params(self.params)

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pre-compute all indicators and attach to df before the bar loop."""
        pass

    @abstractmethod
    def check_signal(
        self,
        df: pd.DataFrame,
        bar_index: int,
        current_position: Optional[Trade] = None
    ) -> SignalResult:
        """
        Evaluate entry/exit signals on closed candle at bar_index.
        Zero look-ahead bias: df.iloc[:bar_index + 1] represents all known information.
        """
        pass
