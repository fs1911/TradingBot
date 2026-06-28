"""Abstract base class for all broker adapters."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import pandas as pd


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_qty: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    client_order_id: Optional[str] = None


@dataclass
class Position:
    symbol: str
    qty: float           # positive = long, negative = short
    entry_price: float
    current_price: float
    unrealized_pnl: float
    side: OrderSide


@dataclass
class AccountInfo:
    equity: float
    cash: float
    buying_power: float
    currency: str = "USD"
    positions: list[Position] = field(default_factory=list)


class BaseBroker(ABC):
    """Common interface every broker adapter must implement."""

    @abstractmethod
    def get_account(self) -> AccountInfo: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame: ...

    @abstractmethod
    def place_order(self, order: Order) -> Order: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def close_position(self, symbol: str) -> bool: ...

    @abstractmethod
    def get_open_orders(self) -> list[Order]: ...

    def is_market_open(self) -> bool:
        return True

    def get_current_price(self, symbol: str) -> float:
        df = self.get_ohlcv(symbol, "1Min", limit=1)
        if df.empty:
            raise ValueError(f"No price data for {symbol}")
        return float(df["close"].iloc[-1])
