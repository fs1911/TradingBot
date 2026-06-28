#!/usr/bin/env python3
"""
Generate a performance report from the trading journal.

Usage:
    python scripts/generate_report.py --period daily
    python scripts/generate_report.py --period weekly
    python scripts/generate_report.py --hints
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.monitoring.reporter import PerformanceReporter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--hints", action="store_true", help="Print optimisation hints")
    args = parser.parse_args()

    reporter = PerformanceReporter()

    if args.period == "daily":
        report = reporter.daily_report()
    else:
        report = reporter.weekly_report()

    print("\n")
    for k, v in report.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for sk, sv in v.items():
                print(f"    {sk}: {sv}")
        else:
            print(f"  {k}: {v}")

    if args.hints:
        print("\n=== OPTIMISATION HINTS ===")
        for hint in reporter.generate_optimization_hints():
            print(f"  • {hint}")


if __name__ == "__main__":
    main()
