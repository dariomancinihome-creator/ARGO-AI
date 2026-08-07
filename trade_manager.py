from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

STORE_PATH = Path(__file__).with_name("trades.json")


@dataclass
class TrackedTrade:
    id: str
    asset: str
    ticker: str
    direction: str
    entry: float
    stop_loss: float | None
    tp1: float | None
    tp2: float | None
    setup: str
    opened_at: str
    status: str = "OPEN"
    closed_at: str | None = None
    exit_price: float | None = None


def _safe_float(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def load_trades(path: Path = STORE_PATH) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_trades(trades: list[dict], path: Path = STORE_PATH) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(trades, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def add_trade(*, asset: str, ticker: str, entry: float, stop_loss: float | None,
              tp1: float | None, tp2: float | None, setup: str,
              path: Path = STORE_PATH) -> dict:
    trades = load_trades(path)
    trade = TrackedTrade(
        id=datetime.now().strftime("%Y%m%d%H%M%S%f"), asset=asset, ticker=ticker,
        direction="LONG", entry=float(entry), stop_loss=_safe_float(stop_loss),
        tp1=_safe_float(tp1), tp2=_safe_float(tp2), setup=setup,
        opened_at=datetime.now().isoformat(timespec="seconds"),
    )
    trades.append(asdict(trade))
    save_trades(trades, path)
    return asdict(trade)


def close_trade(trade_id: str, exit_price: float, path: Path = STORE_PATH) -> None:
    trades = load_trades(path)
    for trade in trades:
        if trade.get("id") == trade_id and trade.get("status") == "OPEN":
            trade["status"] = "CLOSED"
            trade["exit_price"] = float(exit_price)
            trade["closed_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_trades(trades, path)


def trade_snapshot(trade: dict, current_price: float) -> dict:
    entry = float(trade["entry"])
    current = float(current_price)
    pnl_pct = ((current / entry) - 1.0) * 100.0 if entry else 0.0
    sl, tp1, tp2 = (_safe_float(trade.get(k)) for k in ("stop_loss", "tp1", "tp2"))
    if sl is not None and current <= sl:
        state, action = "🔴 Stop raggiunto", "Piano invalidato"
    elif tp2 is not None and current >= tp2:
        state, action = "🏁 TP2 raggiunto", "Target finale raggiunto"
    elif tp1 is not None and current >= tp1:
        state, action = "🎯 TP1 raggiunto", "Valuta protezione del profitto"
    elif current >= entry:
        state, action = "🟢 Trade in profitto", "Piano ancora attivo"
    else:
        state, action = "🟡 Sotto entry", "Controlla il setup e lo stop"
    def distance(level):
        return None if level is None else ((level / current) - 1.0) * 100.0
    return {"pnl_pct": pnl_pct, "state": state, "action": action,
            "distance_sl": distance(sl), "distance_tp1": distance(tp1),
            "distance_tp2": distance(tp2)}
