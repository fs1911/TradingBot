"""Base class for all trading strategies."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import pandas as pd


class SignalType(str, Enum):
    LONG = "long"
    SHORT = "short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    NEUTRAL = "neutral"


@dataclass
class Signal:
    symbol: str
    signal: SignalType
    strategy: str
    score: float = 0.0              # Conviction score 0–1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def is_entry(self) -> bool:
        return self.signal in (SignalType.LONG, SignalType.SHORT)

    def is_exit(self) -> bool:
        return self.signal in (SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT)


class BaseStrategy(ABC):
    """All strategies implement generate_signals()."""

    name: str = "base"

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """
        Accept a fully-computed OHLCV+indicator DataFrame.
        Return a list of Signal objects (may be empty).
        """
        ...

    def _last(self, df: pd.DataFrame, col: str, n: int = 0):
        """Safely access the nth-to-last row of a column."""
        return df[col].iloc[-(n + 1)]
