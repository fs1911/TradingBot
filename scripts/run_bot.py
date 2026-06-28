#!/usr/bin/env python3
"""
Entry point — start the live / paper trading bot.

Usage:
    python scripts/run_bot.py
    python scripts/run_bot.py --once      # single tick (for cron)
    python scripts/run_bot.py --broker binance
"""
import argparse
import sys
import os

# Allow running from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.bot import TradingBot


def main():
    parser = argparse.ArgumentParser(description="TradingBot Runner")
    parser.add_argument("--once", action="store_true", help="Run a single tick and exit")
    parser.add_argument("--broker", type=str, help="Override broker (alpaca|binance|kraken)")
    args = parser.parse_args()

    override = {}
    if args.broker:
        override["broker"] = args.broker

    bot = TradingBot(config_override=override if override else None)

    if args.once:
        bot.run_once()
    else:
        bot.run()


if __name__ == "__main__":
    main()
