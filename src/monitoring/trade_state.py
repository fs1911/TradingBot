"""
Durable open-trade state + journal hygiene.

Why: on every restart the bot used to rebuild its open trades from the broker
alone ("restored"). That lost the original SL/TP, strategy and opening time, and
it trusted the broker's avg_entry_price — which Alpaca paper occasionally reports
as nonsense for crypto (e.g. BTC at −2,227,542 USD). The fallback TP computed from
such a price fired immediately after the 120 s min-hold, the bot closed a real
position, and the journal booked a fictitious +85,000 USD "tp".
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

MAX_ENTRY_DEVIATION = 0.5   # an entry >50% away from the current price is not credible


def plausible_entry(entry: float | None, current: float | None,
                    max_dev: float = MAX_ENTRY_DEVIATION) -> bool:
    """True if a broker entry price is usable: positive, finite and within
    max_dev of the current price."""
    try:
        e, c = float(entry), float(current)
    except (TypeError, ValueError):
        return False
    if not (e > 0 and c > 0) or e != e or c != c:
        return False
    return abs(e / c - 1) <= max_dev


def save_open_trades(path: Path, trades: dict) -> None:
    """Persist {symbol: trade dict} (side as its value, datetimes as ISO)."""
    out = {}
    for sym, t in trades.items():
        d = {}
        for k, v in t.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            elif hasattr(v, "value"):
                d[k] = v.value
            else:
                d[k] = v
        out[sym] = d
    try:
        path.parent.mkdir(exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(out))
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"Could not save open trades: {e}")


def load_open_trades(path: Path) -> dict:
    """Inverse of save_open_trades; side stays a plain string, opened_at a datetime."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except Exception as e:
        logger.warning(f"Could not read open trades: {e}")
        return {}
    out = {}
    for sym, t in raw.items():
        try:
            t["opened_at"] = datetime.fromisoformat(t["opened_at"])
            out[sym] = t
        except Exception:
            continue
    return out


def sanitize_journal(path: Path) -> int:
    """Void the P&L of journal rows whose entry price was not credible (restore
    artefacts). The row stays (the close happened), but pnl is set to 0 and the
    reason is recorded. Idempotent. Returns the number of rows fixed."""
    if not path.exists():
        return 0
    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.warning(f"sanitize_journal: cannot read journal: {e}")
        return 0
    need = {"entry_price", "exit_price", "pnl_usd", "exit_reason"}
    if not need <= set(df.columns):
        return 0
    ok = [plausible_entry(e, x) for e, x in zip(df["entry_price"], df["exit_price"])]
    bad = ~pd.Series(ok, index=df.index) & (df["exit_reason"] != "invalid_entry")
    n = int(bad.sum())
    if n == 0:
        return 0
    df.loc[bad, "pnl_usd"] = 0.0
    if "pnl_pct" in df.columns:
        df.loc[bad, "pnl_pct"] = 0.0
    df.loc[bad, "exit_reason"] = "invalid_entry"
    if "notes" in df.columns:
        df["notes"] = df["notes"].astype("object")
        df.loc[bad, "notes"] = "pnl voided: broker reported an implausible entry price on restore"
    df.to_csv(path, index=False)
    logger.warning(f"sanitize_journal: voided P&L of {n} rows with implausible entry prices")
    return n
