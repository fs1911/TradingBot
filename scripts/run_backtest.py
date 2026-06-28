#!/usr/bin/env python3
"""
Backtest Runner
────────────────────────────────────────────────────────────────────────────
Downloads historical OHLCV data via yfinance and runs the full backtest.

Usage:
    python scripts/run_backtest.py --symbols SPY QQQ AAPL --period 2y --timeframe 1h
    python scripts/run_backtest.py --symbols BTC-USD --period 1y --timeframe 1h
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from tabulate import tabulate
from loguru import logger

from src.utils.helpers import load_config
from src.indicators.technical import add_all_indicators
from src.strategies.ema_crossover import EMACrossoverStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from src.strategies.macd_momentum import MACDMomentumStrategy
from src.backtest.engine import BacktestEngine, BENCHMARKS


YF_INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "1Hour": "1h", "4h": "4h", "1d": "1d", "1Day": "1d",
}


def fetch_yfinance(symbol: str, period: str, interval: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("Install yfinance: pip install yfinance")

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df.sort_index(inplace=True)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["SPY", "QQQ"])
    parser.add_argument("--period", default="2y", help="yfinance period: 1y | 2y | 5y")
    parser.add_argument("--timeframe", default="1h", help="1h | 1d | 15m")
    parser.add_argument("--capital", type=float, default=10_000)
    parser.add_argument("--risk-pct", type=float, default=1.0)
    args = parser.parse_args()

    strategy_cfg = load_config("strategy_config")
    all_params = {}
    for strat_name in ("ema_crossover", "rsi_mean_reversion", "macd_momentum"):
        all_params.update(strategy_cfg.get(strat_name, {}))

    strategies = [
        EMACrossoverStrategy(strategy_cfg.get("ema_crossover", {})),
        RSIMeanReversionStrategy(strategy_cfg.get("rsi_mean_reversion", {})),
        MACDMomentumStrategy(strategy_cfg.get("macd_momentum", {})),
    ]

    engine = BacktestEngine(
        strategies=strategies,
        initial_capital=args.capital,
        risk_per_trade_pct=args.risk_pct,
    )

    yf_interval = YF_INTERVAL_MAP.get(args.timeframe, "1h")
    summary_rows = []

    for symbol in args.symbols:
        logger.info(f"Backtesting {symbol} ({args.period}, {args.timeframe})...")
        try:
            df = fetch_yfinance(symbol, args.period, yf_interval)
            result = engine.run(df, symbol, all_params)
            row = result.summary_dict()
            row["PASS"] = "✓" if engine.passes_benchmarks(result) else "✗"
            summary_rows.append(row)
        except Exception as e:
            logger.error(f"Backtest failed for {symbol}: {e}")

    if summary_rows:
        print("\n" + "="*80)
        print("BACKTEST SUMMARY")
        print("="*80)
        print(tabulate(summary_rows, headers="keys", tablefmt="rounded_outline"))
        print(f"\nBenchmarks: Sharpe≥{BENCHMARKS['min_sharpe']} | "
              f"PF≥{BENCHMARKS['min_profit_factor']} | "
              f"MaxDD≤{BENCHMARKS['max_drawdown_pct']}% | "
              f"WR≥{BENCHMARKS['min_win_rate']}% | "
              f"Trades≥{BENCHMARKS['min_trades']}")


if __name__ == "__main__":
    main()
