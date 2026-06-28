"""
CCXT broker adapter — Crypto exchanges (Binance, Kraken, Bybit …).

Configure via environment variables per exchange. The adapter
wraps ccxt's unified API so strategies are exchange-agnostic.
"""
from __future__ import annotations
import os
import time
from typing import Optional
import pandas as pd
from loguru import logger

from .base_broker import (
    BaseBroker, Order, OrderSide, OrderType, OrderStatus,
    Position, AccountInfo,
)

try:
    import ccxt
    _CCXT_AVAILABLE = True
except ImportError:
    _CCXT_AVAILABLE = False
    logger.warning("ccxt not installed — CCXTBroker unavailable")


# Maps our generic timeframe strings to ccxt format
TIMEFRAME_MAP = {
    "1Min": "1m", "3Min": "3m", "5Min": "5m", "15Min": "15m",
    "30Min": "30m", "1Hour": "1h", "2Hour": "2h", "4Hour": "4h",
    "6Hour": "6h", "12Hour": "12h", "1Day": "1d", "1Week": "1w",
}

EXCHANGE_ENV_KEYS = {
    "binance": ("BINANCE_API_KEY", "BINANCE_SECRET_KEY"),
    "kraken": ("KRAKEN_API_KEY", "KRAKEN_SECRET_KEY"),
    "bybit": ("BYBIT_API_KEY", "BYBIT_SECRET_KEY"),
    "kucoin": ("KUCOIN_API_KEY", "KUCOIN_SECRET_KEY"),
    "okx": ("OKX_API_KEY", "OKX_SECRET_KEY"),
}


class CCXTBroker(BaseBroker):
    """Generic crypto exchange adapter via CCXT."""

    def __init__(self, exchange_id: str = "binance"):
        if not _CCXT_AVAILABLE:
            raise ImportError("Install ccxt: pip install ccxt")

        self.exchange_id = exchange_id.lower()
        api_key_env, secret_env = EXCHANGE_ENV_KEYS.get(
            self.exchange_id, ("API_KEY", "SECRET_KEY")
        )

        api_key = os.environ.get(api_key_env, "")
        secret = os.environ.get(secret_env, "")
        testnet = os.environ.get(f"{exchange_id.upper()}_TESTNET", "true").lower() == "true"

        exchange_class = getattr(ccxt, self.exchange_id)
        self._exchange: ccxt.Exchange = exchange_class({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "future" if "futures" in exchange_id else "spot"},
        })

        if testnet and hasattr(self._exchange, "set_sandbox_mode"):
            self._exchange.set_sandbox_mode(True)
            logger.info(f"CCXTBroker [{exchange_id}] — TESTNET mode")
        else:
            logger.info(f"CCXTBroker [{exchange_id}] — {'sandbox' if testnet else 'LIVE'} mode")

        self._exchange.load_markets()

    def get_account(self) -> AccountInfo:
        balance = self._exchange.fetch_balance()
        total = balance.get("USDT", {}).get("total", 0.0) or 0.0
        free = balance.get("USDT", {}).get("free", 0.0) or 0.0
        return AccountInfo(
            equity=float(total),
            cash=float(free),
            buying_power=float(free),
            currency="USDT",
            positions=self.get_positions(),
        )

    def get_positions(self) -> list[Position]:
        positions = []
        try:
            raw = self._exchange.fetch_positions()
            for p in raw:
                if p.get("contracts", 0) == 0:
                    continue
                qty = float(p.get("contracts", 0))
                side = OrderSide.BUY if p.get("side") == "long" else OrderSide.SELL
                positions.append(Position(
                    symbol=p["symbol"],
                    qty=qty if side == OrderSide.BUY else -qty,
                    entry_price=float(p.get("entryPrice", 0)),
                    current_price=float(p.get("markPrice", 0)),
                    unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                    side=side,
                ))
        except ccxt.NotSupported:
            pass
        return positions

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        tf = TIMEFRAME_MAP.get(timeframe, timeframe)
        raw = self._exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(raw, columns=["datetime", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True)
        df = df.set_index("datetime").sort_index()
        return df

    def place_order(self, order: Order) -> Order:
        side = "buy" if order.side == OrderSide.BUY else "sell"
        try:
            if order.order_type == OrderType.MARKET:
                resp = self._exchange.create_market_order(order.symbol, side, order.qty)
            elif order.order_type == OrderType.LIMIT:
                resp = self._exchange.create_limit_order(order.symbol, side, order.qty, order.limit_price)
            else:
                raise ValueError(f"Unsupported order type: {order.order_type}")

            order.order_id = resp.get("id")
            order.status = OrderStatus.OPEN
            order.filled_price = resp.get("price") or resp.get("average")
            logger.info(f"Order placed: {side} {order.qty} {order.symbol} @ {order.filled_price}")
        except Exception as e:
            order.status = OrderStatus.REJECTED
            logger.error(f"Order failed for {order.symbol}: {e}")
        return order

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._exchange.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"Cancel {order_id} failed: {e}")
            return False

    def close_position(self, symbol: str) -> bool:
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                side = "sell" if pos.qty > 0 else "buy"
                try:
                    self._exchange.create_market_order(symbol, side, abs(pos.qty))
                    return True
                except Exception as e:
                    logger.error(f"Close {symbol} failed: {e}")
                    return False
        return False

    def get_open_orders(self) -> list[Order]:
        orders = []
        try:
            for o in self._exchange.fetch_open_orders():
                orders.append(Order(
                    symbol=o["symbol"],
                    side=OrderSide.BUY if o["side"] == "buy" else OrderSide.SELL,
                    qty=float(o["amount"]),
                    order_id=str(o["id"]),
                    status=OrderStatus.OPEN,
                    limit_price=o.get("price"),
                ))
        except Exception as e:
            logger.error(f"get_open_orders failed: {e}")
        return orders
