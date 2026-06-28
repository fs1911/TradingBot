"""Shared utility functions."""
from __future__ import annotations
import yaml
import os
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import pytz


def load_yaml(path: str | Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_config(name: str) -> dict:
    """Load a named config file from the config/ directory."""
    root = Path(__file__).parent.parent.parent
    return load_yaml(root / "config" / f"{name}.yaml")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_ch_time(dt: datetime) -> datetime:
    """Convert UTC datetime to Swiss time (CET/CEST)."""
    ch = pytz.timezone("Europe/Zurich")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ch)


def pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return ((new - old) / abs(old)) * 100


def format_currency(value: float, currency: str = "USD") -> str:
    return f"{value:,.2f} {currency}"


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))
