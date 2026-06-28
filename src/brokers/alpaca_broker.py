"""
Alpaca Markets broker adapter — US Stocks & ETFs.

Supports paper trading and live trading.
Requires ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL in .env
"""
from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import pandas as pd
from loguru import logger

from .base_broker import (
    BaseBroker, Order, OrderSide, OrderType, OrderStatus,
    Position, AccountInfo,
)

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide as AlpacaSide, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    _ALPACA_AVAILABLE = True
except ImportError:
    _ALPACA_AVAILABLE = False
    logger.warning("alpaca-py not installed — AlpacaBroker unavailable")


class AlpacaBroker(BaseBroker):
    """Alpaca Markets adapter (paper + live)."""

    TIMEFRAME_MAP = {
        "1Min": TimeFrame(1, TimeFrameUnit.Minute),
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
        "4Hour": TimeFrame(4, TimeFrameUnit.Hour),
        "1Day": TimeFrame(1, TimeFrameUnit.Day),
    } if _ALPACA_AVAILABLE else {}

    def __init__(self):
        if not _ALPACA_AVAILABLE:
            raise ImportError("Install alpaca-py: pip install alpaca-py")

        api_key = os.environ["ALPACA_API_KEY"]
        secret_key = os.environ["ALPACA_SECRET_KEY"]
        paper = os.environ.get("TRADING_ENV", "paper") != "live"

        self._trading = TradingClient(api_key, secret_key, paper=paper)
        self._data = StockHistoricalDataClient(api_key, secret_key)
        logger.info(f"AlpacaBroker initialised (paper={paper})")

    def get_account(self) -> AccountInfo:
        acct = self._trading.get_account()
        return AccountInfo(
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            currency="USD",
            positions=self.get_positions(),
        )

    def get_positions(self) -> list[Position]:
        positions = []
        for p in self._trading.get_all_positions():
            positions.append(Position(
                symbol=p.symbol,
                qty=float(p.qty),
                entry_price=float(p.avg_entry_price),
                current_price=float(p.current_price),
                unrealized_pnl=float(p.unrealized_pl),
                side=OrderSide.BUY if float(p.qty) > 0 else OrderSide.SELL,
            ))
        return positions

    def get_ohlcv(self, symbol: str, timeframe: str = "1Hour", limit: int = 500) -> pd.DataFrame:
        tf = self.TIMEFRAME_MAP.get(timeframe, TimeFrame(1, TimeFrameUnit.Hour))
        end = datetime.now(timezone.utc)
        # Estimate start based on limit and timeframe (rough)
        minutes_per_bar = {
            "1Min": 1, "5Min": 5, "15Min": 15,
            "1Hour": 60, "4Hour": 240, "1Day": 1440,
        }.get(timeframe, 60)
        start = end - timedelta(minutes=minutes_per_bar * limit * 1.5)

        req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, start=start, end=end, limit=limit)
        bars = self._data.get_stock_bars(req).df

        if bars.empty:
            return pd.DataFrame()

        bars = bars.reset_index()
        bars = bars.rename(columns={
            "timestamp": "datetime", "open": "open", "high": "high",
            "low": "low", "close": "close", "volume": "volume",
        })
        bars = bars[["datetime", "open", "high", "low", "close", "volume"]].copy()
        bars["datetime"] = pd.to_datetime(bars["datetime"])
        bars = bars.set_index("datetime").sort_index()
        return bars

    def place_order(self, order: Order) -> Order:
        side = AlpacaSide.BUY if order.side == OrderSide.BUY else AlpacaSide.SELL

        if order.order_type == OrderType.MARKET:
            req = MarketOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                time_in_force=TimeInForce.DAY,
            )
        elif order.order_type == OrderType.LIMIT:
            req = LimitOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                limit_price=order.limit_price,
                time_in_force=TimeInForce.DAY,
            )
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        resp = self._trading.submit_order(req)
        order.order_id = str(resp.id)
        order.status = OrderStatus.OPEN
        logger.info(f"Order placed: {order.side.value} {order.qty} {order.symbol} → id={order.order_id}")
        return order

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._trading.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            logger.error(f"Cancel order {order_id} failed: {e}")
            return False

    def close_position(self, symbol: str) -> bool:
        try:
            self._trading.close_position(symbol)
            logger.info(f"Closed position: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Close position {symbol} failed: {e}")
            return False

    def get_open_orders(self) -> list[Order]:
        orders = []
        for o in self._trading.get_orders():
            orders.append(Order(
                symbol=o.symbol,
                side=OrderSide.BUY if o.side.value == "buy" else OrderSide.SELL,
                qty=float(o.qty),
                order_id=str(o.id),
                status=OrderStatus.OPEN,
            ))
        return orders

    def is_market_open(self) -> bool:
        clock = self._trading.get_clock()
        return clock.is_open
